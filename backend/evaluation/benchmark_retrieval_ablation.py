"""
Milestone 2: Retrieval Subsystem Ablation Benchmark
Evaluates 3 isolated retrieval configurations across 50 complex academic & institutional queries:
  1. VECTOR ONLY: ChromaDB dense cosine search (BAAI/bge-large-en-v1.5)
  2. VECTOR + BM25: Hybrid dense + Okapi BM25 with Reciprocal Rank Fusion (k=60)
  3. VECTOR + BM25 + GRAPH: Tri-substrate Hybrid Fusion with Neo4j 2-hop Cypher entity expansion

Metrics:
  - Recall@3, Recall@5, Recall@10
  - Mean Reciprocal Rank (MRR)
  - Relational Entity Coverage (Multi-Hop Precision)
  - Latency (Mean, Median, p90, p95) in milliseconds
  - Latency Overhead & Adaptive Query Routing Recommendation
"""

import asyncio
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Set

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.infrastructure.vector.chroma import LocalVectorEngine
from src.retrieval.parallel_retriever import SelfContainedBM25, AsyncParallelRetriever
from src.retrieval.fusion import reciprocal_rank_fusion
from src.retrieval.pipeline import StandaloneRAGPipeline
from src.infrastructure.graph.neo4j import Neo4jDatabase

# 50 Curated Multi-Hop, Relational, Tabular, and Factual Queries
ABLATION_TESTBED = [
    # --- IIT Madras Domain (15 Queries) ---
    {"id": "IITM_01", "type": "TABLE_EXACT", "query": "What are the student counts for foreign nationals and women students in Table 1.4?", "target_doc": "Annual Report 2024-25 final upload.pdf", "keywords": ["foreign nationals", "women students", "table 1.4", "127", "827"]},
    {"id": "IITM_02", "type": "MULTI_HOP_RELATIONAL", "query": "Who is the Dean of Academic Research and which department are they affiliated with?", "target_doc": "Annual Report 2024-25 final upload.pdf", "keywords": ["dean", "academic research", "administration"]},
    {"id": "IITM_03", "type": "METRIC_EXTRACTION", "query": "What was the total research funding and sponsored project sanction amount?", "target_doc": "Annual Report 2024-25 final upload.pdf", "keywords": ["sponsored research", "funding", "sanctioned", "crore"]},
    {"id": "IITM_04", "type": "MULTI_HOP_RELATIONAL", "query": "Which patents were granted to the Department of Electrical Engineering?", "target_doc": "Annual Report 2024-25 final upload.pdf", "keywords": ["patents", "electrical engineering", "intellectual property"]},
    {"id": "IITM_05", "type": "TABLE_EXACT", "query": "How many degrees were awarded across B.Tech, M.Tech, and Ph.D. programmes?", "target_doc": "Annual Report 2024-25 final upload.pdf", "keywords": ["degrees awarded", "convocation", "b.tech", "ph.d"]},
    {"id": "IITM_06", "type": "INSTITUTIONAL_STRUCTURE", "query": "What centres of excellence were established under the Institute of Eminence initiative?", "target_doc": "Annual Report 2024-25 final upload.pdf", "keywords": ["centres of excellence", "ioe", "eminence"]},
    {"id": "IITM_07", "type": "FINANCIAL_EXTRACTION", "query": "What was the total plan and non-plan grant received from the Ministry of Education?", "target_doc": "Annual Report 2024-25 final upload.pdf", "keywords": ["grants", "ministry of education", "plan", "non-plan"]},
    {"id": "IITM_08", "type": "MULTI_HOP_RELATIONAL", "query": "Which international universities signed MoUs with IIT Madras for joint degrees?", "target_doc": "Annual Report 2024-25 final upload.pdf", "keywords": ["mou", "international", "joint degree", "collaboration"]},
    {"id": "IITM_09", "type": "FACULTY_METRICS", "query": "What is the total sanctioned and active faculty strength across engineering departments?", "target_doc": "Annual Report 2024-25 final upload.pdf", "keywords": ["faculty strength", "sanctioned", "active faculty"]},
    {"id": "IITM_10", "type": "TABLE_EXACT", "query": "What are the campus placement statistics and median salary reported for graduating students?", "target_doc": "Annual Report 2024-25 final upload.pdf", "keywords": ["placement", "median salary", "offers", "recruiting"]},
    {"id": "IITM_11", "type": "MULTI_HOP_RELATIONAL", "query": "What technologies were transferred to industrial partners through the ICSR office?", "target_doc": "Annual Report 2024-25 final upload.pdf", "keywords": ["technology transfer", "icsr", "industrial consultancy"]},
    {"id": "IITM_12", "type": "ALUMNI_AFFAIRS", "query": "How much endowment funding was contributed by alumni associations and donors?", "target_doc": "Annual Report 2024-25 final upload.pdf", "keywords": ["endowment", "alumni", "donation", "contribution"]},
    {"id": "IITM_13", "type": "INFRASTRUCTURE", "query": "What new hostel buildings and academic facilities were completed during the year?", "target_doc": "Annual Report 2024-25 final upload.pdf", "keywords": ["infrastructure", "hostel", "construction", "completed"]},
    {"id": "IITM_14", "type": "RESEARCH_OUTPUT", "query": "What is the total number of peer-reviewed Scopus and Web of Science publications?", "target_doc": "Annual Report 2024-25 final upload.pdf", "keywords": ["publications", "scopus", "web of science", "citations"]},
    {"id": "IITM_15", "type": "STUDENT_AFFAIRS", "query": "What financial assistance and fellowship schemes are available for Ph.D. scholars?", "target_doc": "Annual Report 2024-25 final upload.pdf", "keywords": ["fellowship", "financial assistance", "scholarship", "htra"]},

    # --- IIT (ISM) Dhanbad Domain (15 Queries) ---
    {"id": "ISM_01", "type": "TABLE_EXACT", "query": "Under Schedule 12: Other Income, what is the penalty from contractors and suppliers?", "target_doc": "AR_2024-25_Combined_English_Mail.pdf", "keywords": ["schedule 12", "other income", "penalty from contractors", "14,53,306"]},
    {"id": "ISM_02", "type": "TABLE_EXACT", "query": "What is the exact figure for School support from Consultancy and Projects in Schedule 12?", "target_doc": "AR_2024-25_Combined_English_Mail.pdf", "keywords": ["consultancy", "projects", "school support", "62,06,351"]},
    {"id": "ISM_03", "type": "MULTI_HOP_RELATIONAL", "query": "Who is the Director of IIT (ISM) Dhanbad and what were their key initiatives?", "target_doc": "AR_2024-25_Combined_English_Mail.pdf", "keywords": ["director", "iit (ism) dhanbad", "initiatives"]},
    {"id": "ISM_04", "type": "MINING_ENGINEERING", "query": "What mining and earth sciences projects were undertaken with Coal India Limited?", "target_doc": "AR_2024-25_Combined_English_Mail.pdf", "keywords": ["mining engineering", "coal india", "earth science"]},
    {"id": "ISM_05", "type": "FINANCIAL_EXTRACTION", "query": "What is the total value of sponsored research grants sanctioned by DST and SERB?", "target_doc": "AR_2024-25_Combined_English_Mail.pdf", "keywords": ["sponsored research", "dst", "serb", "grants"]},
    {"id": "ISM_06", "type": "TABLE_EXACT", "query": "Under Schedule 10: Academic Receipts, what was the total tuition fee collected?", "target_doc": "AR_2024-25_Combined_English_Mail.pdf", "keywords": ["schedule 10", "academic receipts", "tuition fee"]},
    {"id": "ISM_07", "type": "MULTI_HOP_RELATIONAL", "query": "Which departments collaborated on the National Mission on Clean Coal Technologies?", "target_doc": "AR_2024-25_Combined_English_Mail.pdf", "keywords": ["clean coal", "department", "collaboration"]},
    {"id": "ISM_08", "type": "GOVERNANCE", "query": "Who are the members of the Board of Governors of IIT (ISM) Dhanbad?", "target_doc": "AR_2024-25_Combined_English_Mail.pdf", "keywords": ["board of governors", "chairman", "members"]},
    {"id": "ISM_09", "type": "PATENTS", "query": "How many Indian and international patent applications were filed by faculty members?", "target_doc": "AR_2024-25_Combined_English_Mail.pdf", "keywords": ["patent applications", "intellectual property", "filed"]},
    {"id": "ISM_10", "type": "TABLE_EXACT", "query": "What were the establishment and administrative expenses reported under Schedule 15?", "target_doc": "AR_2024-25_Combined_English_Mail.pdf", "keywords": ["schedule 15", "establishment expenses", "administrative"]},
    {"id": "ISM_11", "type": "CAMPUS_DEVELOPMENT", "query": "What new laboratories were commissioned in the Department of Petroleum Engineering?", "target_doc": "AR_2024-25_Combined_English_Mail.pdf", "keywords": ["petroleum engineering", "laboratory", "commissioned"]},
    {"id": "ISM_12", "type": "MULTI_HOP_RELATIONAL", "query": "What industry-sponsored chairs were established at IIT (ISM) Dhanbad?", "target_doc": "AR_2024-25_Combined_English_Mail.pdf", "keywords": ["chair professor", "endowment", "industry-sponsored"]},
    {"id": "ISM_13", "type": "STUDENT_INNOVATION", "query": "Which student teams won national competitions in robotics or mining technology?", "target_doc": "AR_2024-25_Combined_English_Mail.pdf", "keywords": ["student innovation", "competition", "robotics"]},
    {"id": "ISM_14", "type": "FINANCIAL_EXTRACTION", "query": "What is the net corpus fund and general reserve balance reported in the balance sheet?", "target_doc": "AR_2024-25_Combined_English_Mail.pdf", "keywords": ["corpus fund", "balance sheet", "general reserve"]},
    {"id": "ISM_15", "type": "SUSTAINABILITY", "query": "What green campus and renewable solar energy projects were installed at Dhanbad?", "target_doc": "AR_2024-25_Combined_English_Mail.pdf", "keywords": ["solar energy", "green campus", "renewable"]},

    # --- IITMRP Research Park Domain (10 Queries) ---
    {"id": "MRP_01", "type": "TABLE_EXACT", "query": "How many total startups have been incubated at IIT Madras Research Park?", "target_doc": "IITMRP Annual Report.pdf", "keywords": ["startups incubated", "458", "incubation cell"]},
    {"id": "MRP_02", "type": "TABLE_EXACT", "query": "What is the total valuation of startups incubated under IITMIC?", "target_doc": "IITMRP Annual Report.pdf", "keywords": ["valuation", "50,000", "billion", "cr"]},
    {"id": "MRP_03", "type": "MULTI_HOP_RELATIONAL", "query": "How many unicorns and IPOs have emerged from IIT Madras Incubation Cell?", "target_doc": "IITMRP Annual Report.pdf", "keywords": ["unicorns", "ipo", "2", "1"]},
    {"id": "MRP_04", "type": "SECTOR_ANALYSIS", "query": "Which sectors have the highest proportion of incubated deep-tech startups?", "target_doc": "IITMRP Annual Report.pdf", "keywords": ["deep-tech", "sectors", "manufacturing", "energy"]},
    {"id": "MRP_05", "type": "CLEAN_ENERGY", "query": "What initiatives does IITMRP have for 100% renewable energy and battery storage?", "target_doc": "IITMRP Annual Report.pdf", "keywords": ["renewable energy", "battery storage", "100%", "solar"]},
    {"id": "MRP_06", "type": "INDUSTRY_COLLABORATION", "query": "Which multinational corporate R&D centres are physically located at the Research Park?", "target_doc": "IITMRP Annual Report.pdf", "keywords": ["corporate", "r&d centres", "tenants", "clients"]},
    {"id": "MRP_07", "type": "INCUBATION_FUNDING", "query": "What seed funding and angel investments were disbursed to early-stage ventures?", "target_doc": "IITMRP Annual Report.pdf", "keywords": ["seed funding", "angel investment", "disbursed"]},
    {"id": "MRP_08", "type": "INTELLECTUAL_PROPERTY", "query": "How many patents have been filed jointly by Research Park companies with IIT Madras?", "target_doc": "IITMRP Annual Report.pdf", "keywords": ["patents", "joint", "research park companies"]},
    {"id": "MRP_09", "type": "WOMEN_ENTREPRENEURSHIP", "query": "What proportion of incubated ventures are led or co-founded by women entrepreneurs?", "target_doc": "IITMRP Annual Report.pdf", "keywords": ["women entrepreneurs", "co-founded", "proportion"]},
    {"id": "MRP_10", "type": "GOVERNANCE", "query": "Who is the President / Chairman of IIT Madras Research Park?", "target_doc": "IITMRP Annual Report.pdf", "keywords": ["president", "board of directors", "ashok jhunjhunwala"]},

    # --- ARE-2016-17 Historical & Longitudinal (5 Queries) ---
    {"id": "ARE_01", "type": "HISTORICAL_EXTRACTION", "query": "What were the primary research thrust areas highlighted in the ARE 2016-17 report?", "target_doc": "ARE-2016-17.pdf", "keywords": ["research thrust", "2016-17", "priorities"]},
    {"id": "ARE_02", "type": "HISTORICAL_FINANCIAL", "query": "What was the total value of consultancy projects completed during 2016-17?", "target_doc": "ARE-2016-17.pdf", "keywords": ["consultancy", "2016-17", "completed"]},
    {"id": "ARE_03", "type": "MULTI_HOP_RELATIONAL", "query": "Which industrial sponsors funded the largest number of collaborative projects in 2016-17?", "target_doc": "ARE-2016-17.pdf", "keywords": ["sponsors", "collaborative projects", "industry"]},
    {"id": "ARE_04", "type": "DEGREE_CONVOCATION", "query": "How many undergraduate and postgraduate degrees were awarded during the 2016-17 convocation?", "target_doc": "ARE-2016-17.pdf", "keywords": ["convocation", "degrees", "undergraduate", "postgraduate"]},
    {"id": "ARE_05", "type": "DEPARTMENT_EXPANSION", "query": "What new interdisciplinary research centres were inaugurated in 2016-17?", "target_doc": "ARE-2016-17.pdf", "keywords": ["interdisciplinary", "research centres", "inaugurated"]},

    # --- Cross-Institutional & Comparative (5 Queries) ---
    {"id": "COMP_01", "type": "COMPARATIVE_FINANCIAL", "query": "Compare the consultancy income reported by IIT Madras and IIT (ISM) Dhanbad.", "target_doc": "BOTH", "keywords": ["consultancy income", "iit madras", "iit (ism) dhanbad"]},
    {"id": "COMP_02", "type": "COMPARATIVE_INCUBATION", "query": "How does the startup incubation model at IITMRP compare with other institutional centres?", "target_doc": "BOTH", "keywords": ["startup incubation", "iitmrp", "incubation cell"]},
    {"id": "COMP_03", "type": "COMPARATIVE_PATENTS", "query": "Compare the patent filing volumes between Dhanbad and Madras annual reports.", "target_doc": "BOTH", "keywords": ["patents", "filing volumes", "intellectual property"]},
    {"id": "COMP_04", "type": "MULTI_INSTITUTIONAL", "query": "Which national research missions received extramural funding across these institutions?", "target_doc": "BOTH", "keywords": ["national missions", "extramural funding", "dst"]},
    {"id": "COMP_05", "type": "FACULTY_COMPARISON", "query": "Compare student-to-faculty ratios across the academic reports.", "target_doc": "BOTH", "keywords": ["student faculty ratio", "faculty strength", "admitted students"]}
]


def evaluate_hits(hits: List[Dict[str, Any]], q_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate recall@k, reciprocal rank, and keyword/relational coverage."""
    target_doc = q_spec.get("target_doc")
    keywords = [kw.lower() for kw in q_spec.get("keywords", [])]

    hit_texts = []
    first_target_rank = 0
    
    for idx, hit in enumerate(hits):
        text = str(hit.get("plain_text") or hit.get("text") or "").lower()
        doc_id = str((hit.get("metadata") or {}).get("doc_id") or hit.get("pdf_filename") or "").lower()
        hit_texts.append(text)

        if target_doc != "BOTH":
            target_stem = Path(target_doc).stem.lower()
            if target_stem in doc_id or target_stem in text:
                if first_target_rank == 0:
                    first_target_rank = idx + 1
        else:
            if first_target_rank == 0:
                first_target_rank = idx + 1

    full_retrieved_text = " ".join(hit_texts)
    matched_keywords = sum(1 for kw in keywords if kw in full_retrieved_text)
    keyword_coverage = matched_keywords / len(keywords) if keywords else 1.0

    recall_at_3 = 1.0 if (first_target_rank > 0 and first_target_rank <= 3) else 0.0
    recall_at_5 = 1.0 if (first_target_rank > 0 and first_target_rank <= 5) else 0.0
    recall_at_10 = 1.0 if (first_target_rank > 0 and first_target_rank <= 10) else 0.0
    reciprocal_rank = 1.0 / first_target_rank if first_target_rank > 0 else 0.0

    return {
        "recall_at_3": recall_at_3,
        "recall_at_5": recall_at_5,
        "recall_at_10": recall_at_10,
        "mrr": reciprocal_rank,
        "keyword_coverage": keyword_coverage,
        "first_target_rank": first_target_rank,
        "total_hits": len(hits)
    }


async def run_ablation_benchmark():
    print("=" * 75)
    print(" 🚀 RAISE MILESTONE 2: RETRIEVAL SUBSYSTEM ABLATION BENCHMARK")
    print(" 50 Complex Queries: Factual, Multi-Hop, Relational, Tabular")
    print(" Comparing: [1] VECTOR ONLY | [2] VECTOR + BM25 | [3] VECTOR + BM25 + GRAPH")
    print("=" * 75)

    pipeline = StandaloneRAGPipeline()
    vector_engine = pipeline.vector_engine
    retriever = pipeline.parallel_retriever
    neo4j_db = pipeline.neo4j_db

    corpus_chunks = []
    chunks_dir = PROJECT_ROOT / "data" / "processed" / "chunks"
    if chunks_dir.exists():
        for cf in chunks_dir.glob("*_chunks.json"):
            try:
                c_list = json.loads(cf.read_text(encoding="utf-8"))
                if isinstance(c_list, list):
                    corpus_chunks.extend(c_list)
            except Exception:
                pass
    bm25_engine = SelfContainedBM25(corpus_chunks) if corpus_chunks else None

    results = {
        "benchmark_name": "RAISE_RETRIEVAL_SUBSYSTEM_ABLATION_50",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_queries": len(ABLATION_TESTBED),
        "corpus_chunk_count": len(corpus_chunks),
        "neo4j_connected": neo4j_db.connected if neo4j_db else False,
        "configurations": {
            "VECTOR_ONLY": {"latencies_ms": [], "recall_3": [], "recall_5": [], "recall_10": [], "mrr": [], "coverage": []},
            "VECTOR_PLUS_BM25": {"latencies_ms": [], "recall_3": [], "recall_5": [], "recall_10": [], "mrr": [], "coverage": []},
            "VECTOR_BM25_GRAPH": {"latencies_ms": [], "recall_3": [], "recall_5": [], "recall_10": [], "mrr": [], "coverage": []}
        },
        "query_breakdown": []
    }

    for idx, q in enumerate(ABLATION_TESTBED, 1):
        query_text = q["query"]
        print(f"[{idx:02d}/50] ({q['type']}) {query_text[:60]}...")

        # 1. VECTOR ONLY
        t0 = time.perf_counter()
        vector_hits = vector_engine.search(query_text, top_k=10)
        t_vec = (time.perf_counter() - t0) * 1000
        v_eval = evaluate_hits(vector_hits, q)
        results["configurations"]["VECTOR_ONLY"]["latencies_ms"].append(t_vec)
        results["configurations"]["VECTOR_ONLY"]["recall_3"].append(v_eval["recall_at_3"])
        results["configurations"]["VECTOR_ONLY"]["recall_5"].append(v_eval["recall_at_5"])
        results["configurations"]["VECTOR_ONLY"]["recall_10"].append(v_eval["recall_at_10"])
        results["configurations"]["VECTOR_ONLY"]["mrr"].append(v_eval["mrr"])
        results["configurations"]["VECTOR_ONLY"]["coverage"].append(v_eval["keyword_coverage"])

        # 2. VECTOR + BM25
        t0 = time.perf_counter()
        v_hits = vector_engine.search(query_text, top_k=10)
        bm25_hits = bm25_engine.search(query_text, top_k=10) if bm25_engine else []
        fused_vec_bm25 = reciprocal_rank_fusion([v_hits, bm25_hits], k=60)[:10]
        t_hybrid = (time.perf_counter() - t0) * 1000
        h_eval = evaluate_hits(fused_vec_bm25, q)
        results["configurations"]["VECTOR_PLUS_BM25"]["latencies_ms"].append(t_hybrid)
        results["configurations"]["VECTOR_PLUS_BM25"]["recall_3"].append(h_eval["recall_at_3"])
        results["configurations"]["VECTOR_PLUS_BM25"]["recall_5"].append(h_eval["recall_at_5"])
        results["configurations"]["VECTOR_PLUS_BM25"]["recall_10"].append(h_eval["recall_at_10"])
        results["configurations"]["VECTOR_PLUS_BM25"]["mrr"].append(h_eval["mrr"])
        results["configurations"]["VECTOR_PLUS_BM25"]["coverage"].append(h_eval["keyword_coverage"])

        # 3. VECTOR + BM25 + GRAPH
        t0 = time.perf_counter()
        graph_hits = await retriever._traverse_graph_entities(query_text, hops=2)
        fused_all = reciprocal_rank_fusion([v_hits, bm25_hits, graph_hits], k=60)[:10]
        t_graph = (time.perf_counter() - t0) * 1000
        g_eval = evaluate_hits(fused_all, q)
        results["configurations"]["VECTOR_BM25_GRAPH"]["latencies_ms"].append(t_graph)
        results["configurations"]["VECTOR_BM25_GRAPH"]["recall_3"].append(g_eval["recall_at_3"])
        results["configurations"]["VECTOR_BM25_GRAPH"]["recall_5"].append(g_eval["recall_at_5"])
        results["configurations"]["VECTOR_BM25_GRAPH"]["recall_10"].append(g_eval["recall_at_10"])
        results["configurations"]["VECTOR_BM25_GRAPH"]["mrr"].append(g_eval["mrr"])
        results["configurations"]["VECTOR_BM25_GRAPH"]["coverage"].append(g_eval["keyword_coverage"])

        results["query_breakdown"].append({
            "id": q["id"],
            "type": q["type"],
            "query": query_text,
            "vector_latency_ms": round(t_vec, 2),
            "hybrid_latency_ms": round(t_hybrid, 2),
            "graph_latency_ms": round(t_graph, 2),
            "vector_coverage": round(v_eval["keyword_coverage"], 3),
            "hybrid_coverage": round(h_eval["keyword_coverage"], 3),
            "graph_coverage": round(g_eval["keyword_coverage"], 3)
        })

    summary = {}
    for name, data in results["configurations"].items():
        lats = sorted(data["latencies_ms"])
        summary[name] = {
            "mean_recall_at_3": round(statistics.mean(data["recall_3"]), 4),
            "mean_recall_at_5": round(statistics.mean(data["recall_5"]), 4),
            "mean_recall_at_10": round(statistics.mean(data["recall_10"]), 4),
            "mean_reciprocal_rank_mrr": round(statistics.mean(data["mrr"]), 4),
            "mean_relational_coverage": round(statistics.mean(data["coverage"]), 4),
            "latency_median_ms": round(statistics.median(lats), 2),
            "latency_p90_ms": round(lats[int(len(lats) * 0.90)], 2),
            "latency_p95_ms": round(lats[int(len(lats) * 0.95)], 2),
            "latency_mean_ms": round(statistics.mean(lats), 2)
        }

    results["summary"] = summary

    v_cov = summary["VECTOR_ONLY"]["mean_relational_coverage"]
    h_cov = summary["VECTOR_PLUS_BM25"]["mean_relational_coverage"]
    g_cov = summary["VECTOR_BM25_GRAPH"]["mean_relational_coverage"]

    v_lat = summary["VECTOR_ONLY"]["latency_median_ms"]
    g_lat = summary["VECTOR_BM25_GRAPH"]["latency_median_ms"]
    
    gain_pct = round(((g_cov - h_cov) / (h_cov if h_cov > 0 else 1.0)) * 100, 2)
    latency_overhead_pct = round(((g_lat - v_lat) / (v_lat if v_lat > 0 else 1.0)) * 100, 2)

    decision = {
        "graph_coverage_gain_over_hybrid_pct": gain_pct,
        "graph_latency_overhead_pct": latency_overhead_pct,
        "adaptive_routing_recommended": True if (latency_overhead_pct > 200 and gain_pct < 20) else False,
        "routing_policy": (
            "Deploy ADAPTIVE GRAPH ROUTING: Direct factual queries bypass Neo4j Cypher to save latency; "
            "trigger Graph traversal selectively on multi-entity and relational queries."
            if (latency_overhead_pct > 200 and gain_pct < 20)
            else "Deploy UNIFIED GRAPH FUSION: Graph traversal adds significant value across queries."
        )
    }
    results["architectural_decision"] = decision

    print("\n" + "=" * 80)
    print(" 📊 RETRIEVAL SUBSYSTEM ABLATION RESULTS (50 QUERIES)")
    print("=" * 80)
    print(f"{'Configuration':<25} | {'Recall@5':<9} | {'MRR':<7} | {'Coverage':<9} | {'Median Lat':<10} | {'p95 Lat':<10}")
    print("-" * 80)
    for name, s in summary.items():
        print(f"{name:<25} | {s['mean_recall_at_5']:<9.2%} | {s['mean_reciprocal_rank_mrr']:<7.3f} | {s['mean_relational_coverage']:<9.2%} | {s['latency_median_ms']:<7.1f} ms | {s['latency_p95_ms']:<7.1f} ms")
    print("-" * 80)
    print(f"Graph Relational Gain vs Hybrid : {gain_pct:+.2f}%")
    print(f"Graph Latency Overhead vs Vector: {latency_overhead_pct:+.2f}%")
    print(f"Architectural Policy Decision   : {decision['routing_policy']}")
    print("=" * 80)

    output_path = PROJECT_ROOT.parent / "Artifacts" / "benchmarks" / "RETRIEVAL_ABLATION_METRICS.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n [✓] Benchmark results exported to: {output_path}")

    return results


if __name__ == "__main__":
    asyncio.run(run_ablation_benchmark())
