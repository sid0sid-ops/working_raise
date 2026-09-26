"""
RAISE NIAH Benchmark — Main CLI Execution Runner
Orchestrates scientific Needle-in-a-Haystack evaluation:
  - Multi-depth and multi-corpus parametric sweeps
  - Chunk size and overlap sensitivity testing
  - Isolated component diagnostic probes
  - 2D retrieval heatmap generation and reporting
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root (RAG) is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Enforce UTF-8 encoding for console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from evaluation.benchmarks.niah.chunking_simulator import ChunkingSimulator
from evaluation.benchmarks.niah.component_probes import (
    ChromaDBProbe,
    EmbeddingProbe,
    GraphTraversalProbe,
    LLMGenerationProbe,
    RerankerProbe,
)
from evaluation.benchmarks.niah.corpus_builder import CorpusBuilder
from evaluation.benchmarks.niah.failure_attributor import FailureAttributor
from evaluation.benchmarks.niah.haystack_generator import HaystackGenerator
from evaluation.benchmarks.niah.isolation_harness import NIAHIsolationHarness
from evaluation.benchmarks.niah.needle_catalog import (
    STANDARD_NEEDLES,
    NeedleCase,
    get_needle,
    list_available_needles,
)
from evaluation.benchmarks.niah.visualizer import NIAHVisualizer


class NIAHBenchmarkRunner:
    """
    Master test harness coordinating NIAH evaluation workflows.
    """

    def __init__(self, seed: int = 42, model_name: Optional[str] = None):
        self.seed = seed
        self.model_name = model_name
        self.generator = HaystackGenerator(seed=seed)
        self.builder = CorpusBuilder(generator=self.generator)

    def run_single_experiment(
        self,
        needle: NeedleCase | str,
        target_words: int = 3000,
        depth: float = 0.50,
        chunk_size: int = 450,
        chunk_overlap: float = 0.0,
        top_k: int = 4,
        test_llm: bool = True,
        use_live_neo4j: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes an isolated end-to-end NIAH test for a single (needle, size, depth, chunking) configuration.
        """
        needle_case = get_needle(needle) if isinstance(needle, str) else needle

        t_start = time.perf_counter()

        # 1. Assemble isolated corpus
        t_corpus_start = time.perf_counter()
        corpus = self.builder.build_corpus(
            needle=needle_case,
            target_words=target_words,
            depth=depth,
        )
        t_corpus_ms = (time.perf_counter() - t_corpus_start) * 1000

        # 2. Chunk corpus with specified parameters
        t_chunk_start = time.perf_counter()
        chunked = ChunkingSimulator.chunk_corpus(
            corpus=corpus,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        t_chunk_ms = (time.perf_counter() - t_chunk_start) * 1000

        # 3. Execute isolated sandbox harness
        with NIAHIsolationHarness(model_name=self.model_name, use_live_neo4j=use_live_neo4j) as harness:
            # Probe A: Embedding representation
            t_embed_start = time.perf_counter()
            distractors = [p for i, p in enumerate(corpus.paragraphs) if i != corpus.needle_paragraph_idx][:50]
            embed_res = EmbeddingProbe.evaluate(
                vector_harness=harness.vector_harness,
                needle_case=needle_case,
                distractor_paragraphs=distractors,
            )
            t_embed_ms = (time.perf_counter() - t_embed_start) * 1000

            # Probe B: ChromaDB retrieval
            t_chroma_start = time.perf_counter()
            chroma_res = ChromaDBProbe.evaluate(
                vector_harness=harness.vector_harness,
                chunked_corpus=chunked,
                needle_case=needle_case,
                top_k=top_k,
            )
            t_chroma_ms = (time.perf_counter() - t_chroma_start) * 1000

            # Probe C: Cross-Encoder Reranker
            t_rerank_start = time.perf_counter()
            rerank_res = RerankerProbe.evaluate(
                candidates=chroma_res.retrieved_chunks,
                needle_case=needle_case,
                gold_chunk_ids=chunked.gold_chunk_ids,
                top_n=5,
            )
            t_rerank_ms = (time.perf_counter() - t_rerank_start) * 1000

            # Probe D: Graph Traversal (for relational graph needles)
            t_graph_ms = 0.0
            graph_res = None
            if needle_case.graph_entities and needle_case.graph_relations:
                t_graph_start = time.perf_counter()
                graph_res = GraphTraversalProbe.evaluate(
                    graph_harness=harness.graph_harness,
                    needle_case=needle_case,
                    max_hops=2,
                )
                t_graph_ms = (time.perf_counter() - t_graph_start) * 1000

            # Probe E: LLM In-Context Extraction (if enabled)
            t_gen_ms = 0.0
            gen_res = None
            if test_llm:
                t_gen_start = time.perf_counter()
                top_context_chunks = (
                    rerank_res.reranked_chunks[:6]
                    if rerank_res and rerank_res.reranked_chunks
                    else chroma_res.retrieved_chunks[:6]
                )
                subg = harness.graph_harness.in_memory_graph.extract_subgraph(
                    seed_node_ids=[needle_case.graph_entities[0]["id"]], hops=2
                ) if needle_case.graph_entities else None

                gen_res = LLMGenerationProbe.evaluate(
                    retrieved_chunks=top_context_chunks,
                    needle_case=needle_case,
                    subgraph=subg,
                )
                t_gen_ms = (time.perf_counter() - t_gen_start) * 1000

            # Diagnostic failure attribution
            diagnosis = FailureAttributor.diagnose(
                embedding_res=embed_res,
                retrieval_res=chroma_res,
                reranker_res=rerank_res,
                graph_res=graph_res,
                generation_res=gen_res,
                needle_case=needle_case,
            )

            is_success = diagnosis.stage.value == "SUCCESS"
            t_total_ms = (time.perf_counter() - t_start) * 1000

            gold_rank = chroma_res.gold_rank
            top_1_hit = bool(gold_rank == 1)
            reciprocal_rank = (1.0 / gold_rank) if gold_rank else 0.0

            return {
                "needle_id": needle_case.needle_id,
                "needle_type": needle_case.needle_type.value,
                "target_words": target_words,
                "actual_words": corpus.actual_words,
                "depth_requested": depth,
                "depth_actual": corpus.depth_actual,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "total_chunks": chunked.total_chunks,
                "needle_fragmented": chunked.needle_fragmented,
                "query": needle_case.query,
                "expected_answer": needle_case.expected_answer,
                "top_k_recall": chroma_res.top_k_recall,
                "top_1_hit": top_1_hit,
                "reciprocal_rank": reciprocal_rank,
                "gold_rank": gold_rank,
                "gold_similarity": chroma_res.gold_similarity,
                "embedding_margin": embed_res.similarity_margin,
                "reranker_retained": rerank_res.reranker_retained,
                "reranker_rank": rerank_res.post_rerank_rank,
                "graph_success": graph_res.traversal_success if graph_res else True,
                "generation_success": gen_res.generation_success if gen_res else None,
                "success": is_success,
                "failure_stage": diagnosis.stage.value,
                "root_cause": diagnosis.root_cause,
                "recommended_fix": diagnosis.recommended_fix,
                "latency_breakdown": {
                    "corpus_build_ms": round(t_corpus_ms, 2),
                    "chunking_ms": round(t_chunk_ms, 2),
                    "embedding_probe_ms": round(t_embed_ms, 2),
                    "chromadb_retrieval_ms": round(t_chroma_ms, 2),
                    "reranker_ms": round(t_rerank_ms, 2),
                    "graph_ms": round(t_graph_ms, 2),
                    "generation_ms": round(t_gen_ms, 2),
                    "total_ms": round(t_total_ms, 2),
                }
            }

    def run_sweep(
        self,
        needle_id: str = "fact_quantum_crypt",
        depths: Optional[List[float]] = None,
        context_sizes: Optional[List[int]] = None,
        chunk_size: int = 450,
        chunk_overlap: float = 0.0,
        top_k: int = 4,
        test_llm: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Runs full 2D grid sweep over (depth x context_size).
        """
        test_depths = depths or [0.0, 0.25, 0.50, 0.75, 1.00]
        test_sizes = context_sizes or [1000, 3000, 6000, 10000]

        print(f"\n" + "=" * 78)
        print(f" 🚀 [NIAH BENCHMARK SWEEP] Needle: '{needle_id}'")
        print(f"   Depths: {[f'{int(d*100)}%' for d in test_depths]}")
        print(f"   Context Sizes: {[f'{s}w' for s in test_sizes]}")
        print(f"   Chunk Size: {chunk_size}w | Overlap: {int(chunk_overlap*100)}% | Top-K: {top_k}")
        print("=" * 78)

        results = []
        total_tests = len(test_depths) * len(test_sizes)
        count = 0

        for d in test_depths:
            for s in test_sizes:
                count += 1
                t0 = time.time()
                res = self.run_single_experiment(
                    needle=needle_id,
                    target_words=s,
                    depth=d,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    top_k=top_k,
                    test_llm=test_llm,
                )
                elapsed = time.time() - t0
                status = "PASS" if res["success"] else res["failure_stage"]
                rank_str = f"rank={res['gold_rank']}" if res["gold_rank"] else "not retrieved"
                print(f"  [{count}/{total_tests}] Depth: {int(d*100):>3}% | Size: {s:>5}w | Status: {status:<15} ({rank_str}) [{elapsed:.2f}s]")
                results.append(res)

        return results

    def run_isolated_component_evaluation(self, needle_id: str = "fact_quantum_crypt") -> Dict[str, Any]:
        """
        Evaluates and isolates each component independently to answer diagnostic questions.
        """
        needle_case = get_needle(needle_id)
        print(f"\n======================================================================")
        print(f" 🔬 ISOLATED COMPONENT DIAGNOSTICS: Needle '{needle_case.needle_id}'")
        print(f"======================================================================")

        distractors = self.generator.generate_haystack(target_words=2000)
        corpus = self.builder.build_corpus(needle=needle_case, target_words=3000, depth=0.50)
        chunked = ChunkingSimulator.chunk_corpus(corpus=corpus, chunk_size=450, chunk_overlap=0.0)

        with NIAHIsolationHarness(model_name=self.model_name, use_live_neo4j=False) as harness:
            # 1. Embedding Probe
            print("\n[Probe 1/5] Testing Dense Embedding Representation...")
            emb_res = EmbeddingProbe.evaluate(harness.vector_harness, needle_case, distractors)
            print(f"  • Query-Needle Cosine Similarity: {emb_res.query_needle_sim:.4f}")
            print(f"  • Max Distractor Similarity    : {emb_res.max_distractor_sim:.4f}")
            print(f"  • Similarity Margin Delta     : {emb_res.similarity_margin:+.4f}")
            print(f"  • Needle Representation Rank  : #{emb_res.needle_rank} of {emb_res.total_candidates}")
            print(f"  • Result: {'✅ PASSED (Separable representation)' if emb_res.representation_success else '❌ FAILED'}")

            # 2. ChromaDB Retrieval Probe
            print("\n[Probe 2/5] Testing ChromaDB Cosine Index Top-K Recall...")
            chroma_res = ChromaDBProbe.evaluate(harness.vector_harness, chunked, needle_case, top_k=5)
            print(f"  • Total Chunks Indexed: {chroma_res.total_indexed_chunks}")
            print(f"  • Gold Chunk Rank    : #{chroma_res.gold_rank or 'Unretrieved'}")
            print(f"  • Gold Similarity    : {chroma_res.gold_similarity}")
            print(f"  • Top-5 Recall       : {'✅ PASSED (Retrieved in top-5)' if chroma_res.top_k_recall else '❌ FAILED'}")

            # 3. CrossEncoder Reranker Probe
            print("\n[Probe 3/5] Testing Cross-Encoder Contextual Reranker...")
            rerank_res = RerankerProbe.evaluate(chroma_res.retrieved_chunks, needle_case, chunked.gold_chunk_ids, top_n=5)
            print(f"  • Pre-Rerank Rank : #{rerank_res.pre_rerank_rank}")
            print(f"  • Post-Rerank Rank: #{rerank_res.post_rerank_rank}")
            print(f"  • Rank Delta      : {rerank_res.rank_delta:+d} (Promotion/Demotion)")
            print(f"  • Result          : {'✅ PASSED (Retained in top-5)' if rerank_res.reranker_retained else '❌ FAILED'}")

            # 4. Graph Traversal Probe (using multi-hop needle if available)
            print("\n[Probe 4/5] Testing Knowledge Graph Multi-Hop Traversal...")
            graph_needle = get_needle("graph_multihop_carbon")
            graph_res = GraphTraversalProbe.evaluate(harness.graph_harness, graph_needle, max_hops=2)
            print(f"  • Seed Entity Found  : {graph_res.seed_found}")
            print(f"  • Target Entity Found: {graph_res.target_found}")
            print(f"  • Traversed Path Hops: {graph_res.path_length}")
            print(f"  • Result             : {'✅ PASSED (Multi-hop path resolved)' if graph_res.traversal_success else '❌ FAILED'}")

            # 5. LLM Extraction Probe
            print("\n[Probe 5/5] Testing Grounded LLM Context Extraction...")
            gen_res = LLMGenerationProbe.evaluate(chroma_res.retrieved_chunks, needle_case)
            print(f"  • Gold in Context Prompt: {gen_res.gold_in_context}")
            print(f"  • LLM Backend Online   : {gen_res.llm_available}")
            print(f"  • Generated Answer     : \"{gen_res.generated_answer[:100]}...\"")
            print(f"  • Answer Verified      : {'✅ PASSED' if gen_res.generation_success else '❌ FAILED'}")

        print(f"\n======================================================================")
        print(f" ✅ ALL 5 COMPONENT PROBES EXECUTED CLEANLY")
        print(f"======================================================================\n")

        return {
            "embedding": emb_res.to_dict(),
            "chromadb": chroma_res.to_dict(),
            "reranker": rerank_res.to_dict(),
            "graph": graph_res.to_dict(),
            "generation": gen_res.to_dict(),
        }


def main():
    parser = argparse.ArgumentParser(description="RAISE NIAH Retrieval Robustness Benchmark")
    parser.add_argument("--quick", action="store_true", help="Run fast 6-cell sanity check")
    parser.add_argument("--sweep", action="store_true", help="Run full 2D parametric sweep")
    parser.add_argument("--isolate-components", action="store_true", help="Run isolated component-level probes")
    parser.add_argument("--needle", type=str, default="fact_quantum_crypt", choices=list_available_needles(), help="Target needle ID")
    parser.add_argument("--chunk-size", type=int, default=450, help="Chunk size in words")
    parser.add_argument("--chunk-overlap", type=float, default=0.0, help="Chunk overlap ratio (0.0 to 0.3)")
    parser.add_argument("--top-k", type=int, default=4, help="Top-k retrieval budget (default: 4 for Fast Mode)")
    parser.add_argument("--test-llm", action="store_true", help="Test LLM synthesis stage")
    args = parser.parse_args()

    runner = NIAHBenchmarkRunner()

    if args.isolate_components:
        runner.run_isolated_component_evaluation(needle_id=args.needle)
        return

    if args.quick:
        depths = [0.0, 0.50, 1.00]
        sizes = [1000, 5000]
        results = runner.run_sweep(
            needle_id=args.needle,
            depths=depths,
            context_sizes=sizes,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            top_k=args.top_k,
            test_llm=args.test_llm,
        )
    elif args.sweep:
        depths = [0.0, 0.10, 0.25, 0.50, 0.75, 0.90, 1.00]
        sizes = [1000, 3000, 6000, 10000, 20000]
        results = runner.run_sweep(
            needle_id=args.needle,
            depths=depths,
            context_sizes=sizes,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            top_k=args.top_k,
            test_llm=args.test_llm,
        )
    else:
        # Default: quick run
        depths = [0.0, 0.50, 1.00]
        sizes = [1000, 4000]
        results = runner.run_sweep(
            needle_id=args.needle,
            depths=depths,
            context_sizes=sizes,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            top_k=args.top_k,
            test_llm=args.test_llm,
        )

    # Render Visual ASCII Matrix & Export Markdown Report
    print("\n" + "=" * 78)
    print(" 📊 2D RETRIEVAL MATRIX (DEPTH VS CONTEXT SIZE)")
    print("=" * 78)
    ascii_table = NIAHVisualizer.render_ascii_matrix(
        results=results,
        depths=sorted(list({r["depth_requested"] for r in results})),
        context_sizes=sorted(list({r["target_words"] for r in results})),
    )
    print(ascii_table)

    paths = NIAHVisualizer.export_report(
        results=results,
        experiment_name=f"niah_{args.needle}",
    )
    print(f"\n📄 Saved Benchmark Report: {paths['markdown']}")
    print(f"📊 Saved Benchmark JSON  : {paths['json']}\n")


if __name__ == "__main__":
    main()
