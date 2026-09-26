"""
Benchmark Downloader & Sampler Script for Academic RAG Baselines
Downloads representative 200-300 question evaluation subsets for:
1. Retrieval: BEIR (SciFact), TREC Deep Learning 2019, TREC Deep Learning 2020
2. Reasoning: HotpotQA, 2WikiMultihopQA, MuSiQue, FRAMES (Google frames-benchmark)
3. Generation / QA: Natural Questions (NQ), TriviaQA

All downloads strictly sample 200-300 items to adhere to memory/storage limits.
All outputs are saved to RAG/data/benchmarks/<benchmark>/ and RAG/evaluation/datasets/<benchmark>/.
"""

import csv
import gzip
import io
import json
import logging
import os
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("raise.eval.downloader")

ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_DATA_DIR = ROOT / "data" / "benchmarks"
EVAL_DATASETS_DIR = ROOT / "evaluation" / "datasets"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_json(data: Any, path: Path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(data) if isinstance(data, list) else 1} items to {path}")


def save_jsonl(data: List[Dict[str, Any]], path: Path):
    with open(path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    logger.info(f"Saved {len(data)} lines to {path}")


# =========================================================================
# 1. BEIR (SciFact)
# =========================================================================
def download_beir_scifact(sample_limit: int = 300) -> Dict[str, Any]:
    logger.info("--> Fetching BEIR (SciFact)...")
    url = "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        queries_raw = [json.loads(line) for line in z.read("scifact/queries.jsonl").decode("utf-8").splitlines() if line.strip()]
        
        # Load test qrels
        qrels_raw = z.read("scifact/qrels/test.tsv").decode("utf-8").splitlines()
        qrels = {}
        for line in qrels_raw[1:]:  # skip header
            parts = line.strip().split("\t")
            if len(parts) >= 3:
                qid, docid, score = parts[0], parts[1], int(parts[2])
                if qid not in qrels:
                    qrels[qid] = []
                qrels[qid].append({"doc_id": docid, "score": score})
        
        # Load corpus
        corpus_lines = [json.loads(line) for line in z.read("scifact/corpus.jsonl").decode("utf-8").splitlines() if line.strip()]
        corpus_map = {doc["_id"]: doc for doc in corpus_lines}

    # Sample queries that have test qrels first
    queries_with_qrels = [q for q in queries_raw if q["_id"] in qrels]
    sampled_queries = queries_with_qrels[:sample_limit]
    
    standardized = []
    for q in sampled_queries:
        qid = q["_id"]
        q_rel = qrels.get(qid, [])
        supporting_docs = [corpus_map[rel["doc_id"]]["title"] + ": " + corpus_map[rel["doc_id"]]["text"] 
                           for rel in q_rel if rel["doc_id"] in corpus_map and rel["score"] > 0]
        
        standardized.append({
            "q_id": f"BEIR_SCIFACT_{qid}",
            "benchmark": "BEIR",
            "dataset": "beir/scifact",
            "tier": "Retrieval Benchmark",
            "question": q["text"],
            "ground_truth_answer": None,
            "relevant_doc_ids": [r["doc_id"] for r in q_rel],
            "supporting_facts": supporting_docs[:5],
            "hop_count": 1,
            "is_unanswerable": len(q_rel) == 0,
            "metadata": {"raw_query_id": qid, "qrels": q_rel}
        })

    out_dirs = [BENCHMARK_DATA_DIR / "beir", EVAL_DATASETS_DIR / "beir" / "scifact"]
    for d in out_dirs:
        ensure_dir(d)
        save_jsonl(standardized, d / "samples_300.jsonl")
        save_json(standardized, d / "samples_300.json")

    return {"benchmark": "BEIR-SciFact", "count": len(standardized), "status": "SUCCESS"}


# =========================================================================
# 2. TREC Deep Learning 2019
# =========================================================================
def download_trec_dl_2019(sample_limit: int = 200) -> Dict[str, Any]:
    logger.info("--> Fetching TREC Deep Learning 2019...")
    q_url = "https://msmarco.z22.web.core.windows.net/msmarcoranking/msmarco-test2019-queries.tsv.gz"
    qrel_url = "https://trec.nist.gov/data/deep/2019qrels-pass.txt"
    
    # Download queries
    r_q = requests.get(q_url, headers=HEADERS, timeout=30)
    r_q.raise_for_status()
    q_tsv = gzip.decompress(r_q.content).decode("utf-8").splitlines()
    queries = {}
    for line in q_tsv:
        parts = line.strip().split("\t")
        if len(parts) >= 2:
            queries[parts[0]] = parts[1]

    # Download qrels
    r_qrel = requests.get(qrel_url, headers=HEADERS, timeout=30)
    r_qrel.raise_for_status()
    qrels = {}
    for line in r_qrel.text.splitlines():
        parts = line.strip().split()
        if len(parts) >= 4:
            qid, _, docid, rel = parts[0], parts[1], parts[2], int(parts[3])
            if qid not in qrels:
                qrels[qid] = []
            qrels[qid].append({"doc_id": docid, "relevance": rel})

    standardized = []
    for qid, qtext in list(queries.items())[:sample_limit]:
        rel_list = qrels.get(qid, [])
        positive_docs = [r["doc_id"] for r in rel_list if r["relevance"] >= 2]
        standardized.append({
            "q_id": f"TREC_DL_2019_{qid}",
            "benchmark": "TREC-DL-2019",
            "dataset": "trec-dl-2019-passage",
            "tier": "Passage Ranking",
            "question": qtext,
            "ground_truth_answer": None,
            "relevant_doc_ids": positive_docs,
            "supporting_facts": [],
            "hop_count": 1,
            "is_unanswerable": len(positive_docs) == 0,
            "metadata": {"qid": qid, "total_judged": len(rel_list), "positive_count": len(positive_docs)}
        })

    out_dirs = [BENCHMARK_DATA_DIR / "trec_dl_2019", EVAL_DATASETS_DIR / "trec_dl" / "2019"]
    for d in out_dirs:
        ensure_dir(d)
        save_jsonl(standardized, d / "samples_200.jsonl")
        save_json(standardized, d / "samples_200.json")

    return {"benchmark": "TREC-DL-2019", "count": len(standardized), "status": "SUCCESS"}


# =========================================================================
# 3. TREC Deep Learning 2020
# =========================================================================
def download_trec_dl_2020(sample_limit: int = 200) -> Dict[str, Any]:
    logger.info("--> Fetching TREC Deep Learning 2020...")
    q_url = "https://msmarco.z22.web.core.windows.net/msmarcoranking/msmarco-test2020-queries.tsv.gz"
    qrel_url = "https://trec.nist.gov/data/deep/2020qrels-pass.txt"
    
    # Download queries
    r_q = requests.get(q_url, headers=HEADERS, timeout=30)
    r_q.raise_for_status()
    q_tsv = gzip.decompress(r_q.content).decode("utf-8").splitlines()
    queries = {}
    for line in q_tsv:
        parts = line.strip().split("\t")
        if len(parts) >= 2:
            queries[parts[0]] = parts[1]

    # Download qrels
    r_qrel = requests.get(qrel_url, headers=HEADERS, timeout=30)
    r_qrel.raise_for_status()
    qrels = {}
    for line in r_qrel.text.splitlines():
        parts = line.strip().split()
        if len(parts) >= 4:
            qid, _, docid, rel = parts[0], parts[1], parts[2], int(parts[3])
            if qid not in qrels:
                qrels[qid] = []
            qrels[qid].append({"doc_id": docid, "relevance": rel})

    standardized = []
    for qid, qtext in list(queries.items())[:sample_limit]:
        rel_list = qrels.get(qid, [])
        positive_docs = [r["doc_id"] for r in rel_list if r["relevance"] >= 2]
        standardized.append({
            "q_id": f"TREC_DL_2020_{qid}",
            "benchmark": "TREC-DL-2020",
            "dataset": "trec-dl-2020-passage",
            "tier": "Passage Ranking",
            "question": qtext,
            "ground_truth_answer": None,
            "relevant_doc_ids": positive_docs,
            "supporting_facts": [],
            "hop_count": 1,
            "is_unanswerable": len(positive_docs) == 0,
            "metadata": {"qid": qid, "total_judged": len(rel_list), "positive_count": len(positive_docs)}
        })

    out_dirs = [BENCHMARK_DATA_DIR / "trec_dl_2020", EVAL_DATASETS_DIR / "trec_dl" / "2020"]
    for d in out_dirs:
        ensure_dir(d)
        save_jsonl(standardized, d / "samples_200.jsonl")
        save_json(standardized, d / "samples_200.json")

    return {"benchmark": "TREC-DL-2020", "count": len(standardized), "status": "SUCCESS"}


# =========================================================================
# 4. HotpotQA
# =========================================================================
def download_hotpotqa(sample_limit: int = 300) -> Dict[str, Any]:
    logger.info("--> Fetching HotpotQA (distractor dev)...")
    url_tmpl = "https://datasets-server.huggingface.co/rows?dataset=hotpotqa%2Fhotpot_qa&config=distractor&split=validation&offset={offset}&limit=100"
    
    rows = []
    for offset in [0, 100, 200]:
        if len(rows) >= sample_limit:
            break
        r = requests.get(url_tmpl.format(offset=offset), headers=HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
        batch = [item["row"] for item in data.get("rows", [])]
        rows.extend(batch)
    
    rows = rows[:sample_limit]
    
    raw_hotpot_format = []
    standardized = []
    
    for r in rows:
        sp_facts = [f"{sp[0]} (Sentence {sp[1]})" for sp in r.get("supporting_facts", [])]
        raw_hotpot_format.append({
            "_id": r.get("id"),
            "question": r.get("question"),
            "answer": r.get("answer"),
            "type": r.get("type"),
            "level": r.get("level"),
            "supporting_facts": r.get("supporting_facts", []),
            "context": r.get("context", [])
        })
        
        standardized.append({
            "q_id": f"HOTPOT_{r.get('id')}",
            "benchmark": "HotpotQA",
            "dataset": "hotpot_dev_distractor_v1",
            "tier": f"2-Hop Multi-Hop ({r.get('level', 'medium')})",
            "question": r.get("question", "").strip(),
            "ground_truth_answer": r.get("answer", "").strip(),
            "supporting_facts": sp_facts,
            "hop_count": 2,
            "is_unanswerable": False,
            "metadata": {
                "type": r.get("type"),
                "level": r.get("level"),
                "context_titles": [c[0] for c in r.get("context", [])] if r.get("context") else []
            }
        })

    out_dirs = [BENCHMARK_DATA_DIR / "hotpotqa", EVAL_DATASETS_DIR / "hotpotqa"]
    for d in out_dirs:
        ensure_dir(d)
        save_json(raw_hotpot_format, d / "hotpot_dev_distractor_v1.json")
        save_jsonl(standardized, d / "samples_300.jsonl")
        save_json(standardized, d / "samples_300.json")

    return {"benchmark": "HotpotQA", "count": len(standardized), "status": "SUCCESS"}


# =========================================================================
# 5. 2WikiMultihopQA
# =========================================================================
def download_2wikimultihop(sample_limit: int = 300) -> Dict[str, Any]:
    logger.info("--> Fetching 2WikiMultihopQA (dev.parquet)...")
    url = "https://huggingface.co/datasets/xanhho/2WikiMultihopQA/resolve/main/dev.parquet"
    df = pd.read_parquet(url)
    sampled_df = df.iloc[:sample_limit]
    
    raw_2wiki_format = []
    standardized = []
    
    for _, row in sampled_df.iterrows():
        sp_facts = []
        if isinstance(row.get("supporting_facts"), list):
            sp_facts = [f"{sp[0]} (Sentence {sp[1]})" for sp in row.get("supporting_facts", [])]
        
        raw_2wiki_format.append({
            "_id": str(row.get("_id")),
            "type": str(row.get("type")),
            "question": str(row.get("question")),
            "context": row.get("context").tolist() if hasattr(row.get("context"), "tolist") else row.get("context"),
            "supporting_facts": row.get("supporting_facts").tolist() if hasattr(row.get("supporting_facts"), "tolist") else row.get("supporting_facts"),
            "evidences": row.get("evidences").tolist() if hasattr(row.get("evidences"), "tolist") else row.get("evidences"),
            "answer": str(row.get("answer"))
        })
        
        standardized.append({
            "q_id": f"2WIKI_{row.get('_id')}",
            "benchmark": "2WikiMultihopQA",
            "dataset": "2wikimultihopqa-dev",
            "tier": f"Relational Multi-Hop ({row.get('type')})",
            "question": str(row.get("question", "")).strip(),
            "ground_truth_answer": str(row.get("answer", "")).strip(),
            "supporting_facts": sp_facts,
            "hop_count": 2,
            "is_unanswerable": False,
            "metadata": {
                "type": str(row.get("type")),
                "evidences_count": len(row.get("evidences", [])) if isinstance(row.get("evidences"), (list, tuple)) else 0
            }
        })

    out_dirs = [BENCHMARK_DATA_DIR / "2wikimultihopqa", EVAL_DATASETS_DIR / "2wikimultihopqa"]
    for d in out_dirs:
        ensure_dir(d)
        save_json(raw_2wiki_format, d / "dev.json")
        save_jsonl(standardized, d / "samples_300.jsonl")
        save_json(standardized, d / "samples_300.json")

    return {"benchmark": "2WikiMultihopQA", "count": len(standardized), "status": "SUCCESS"}


# =========================================================================
# 6. MuSiQue
# =========================================================================
def download_musique(sample_limit: int = 300) -> Dict[str, Any]:
    logger.info("--> Fetching MuSiQue (dev split)...")
    url_tmpl = "https://datasets-server.huggingface.co/rows?dataset=bdsaglam%2Fmusique&config=default&split=validation&offset={offset}&limit=100"
    
    rows = []
    for offset in [0, 100, 200]:
        if len(rows) >= sample_limit:
            break
        r = requests.get(url_tmpl.format(offset=offset), headers=HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
        batch = [item["row"] for item in data.get("rows", [])]
        rows.extend(batch)
    
    rows = rows[:sample_limit]
    
    raw_musique_format = []
    standardized = []
    
    for r in rows:
        decomp = r.get("question_decomposition", [])
        hop_count = len(decomp) if decomp else 2
        is_ans = r.get("answerable", True)
        ans = r.get("answer", "")
        
        raw_musique_format.append(r)
        standardized.append({
            "q_id": f"MUSIQUE_{r.get('id')}",
            "benchmark": "MuSiQue",
            "dataset": "musique-dev",
            "tier": f"{hop_count}-Hop Reasoning",
            "question": r.get("question", "").strip(),
            "ground_truth_answer": ans,
            "supporting_facts": [d.get("question", "") for d in decomp] if decomp else [],
            "hop_count": hop_count,
            "is_unanswerable": not is_ans,
            "metadata": {
                "answerable": is_ans,
                "answer_aliases": r.get("answer_aliases", []),
                "question_decomposition": decomp
            }
        })

    out_dirs = [BENCHMARK_DATA_DIR / "musique", EVAL_DATASETS_DIR / "musique"]
    for d in out_dirs:
        ensure_dir(d)
        save_jsonl(raw_musique_format, d / "musique_ans_v1.0_dev.jsonl")
        save_jsonl(standardized, d / "samples_300.jsonl")
        save_json(standardized, d / "samples_300.json")

    return {"benchmark": "MuSiQue", "count": len(standardized), "status": "SUCCESS"}


# =========================================================================
# 7. FRAMES (Google frames-benchmark)
# =========================================================================
def sample_frames(sample_limit: int = 300) -> Dict[str, Any]:
    logger.info("--> Processing FRAMES (Google frames-benchmark)...")
    local_tsv = ROOT.parent / "backend" / "evaluation" / "benchmarks" / "frames" / "data" / "frames_test.tsv"
    
    if not local_tsv.exists():
        logger.info("Downloading frames_test.tsv from HuggingFace...")
        url = "https://huggingface.co/datasets/google/frames-benchmark/raw/main/test.tsv"
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        ensure_dir(local_tsv.parent)
        local_tsv.write_bytes(r.content)

    standardized = []
    with open(local_tsv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for idx, row in enumerate(reader):
            if idx >= sample_limit:
                break
            
            q_text = row.get("Prompt", row.get("question", "")).strip()
            ans = row.get("Answer", row.get("answer", "")).strip()
            r_types = row.get("reasoning_types", "")
            is_unans = "unanswerable" in r_types.lower() or "insufficient" in ans.lower()
            
            standardized.append({
                "q_id": f"FRAMES_{idx+1:04d}",
                "benchmark": "FRAMES",
                "dataset": "google/frames-benchmark",
                "tier": "Multi-Hop Reasoning",
                "question": q_text,
                "ground_truth_answer": ans,
                "supporting_facts": [],
                "hop_count": 2,
                "is_unanswerable": is_unans,
                "metadata": {"reasoning_types": r_types}
            })

    out_dirs = [BENCHMARK_DATA_DIR / "frames"]
    for d in out_dirs:
        ensure_dir(d)
        save_jsonl(standardized, d / "samples_300.jsonl")
        save_json(standardized, d / "samples_300.json")

    return {"benchmark": "FRAMES", "count": len(standardized), "status": "SUCCESS"}


# =========================================================================
# 8. Natural Questions (NQ)
# =========================================================================
def download_nq(sample_limit: int = 300) -> Dict[str, Any]:
    logger.info("--> Fetching Natural Questions (NQ)...")
    url_tmpl = "https://datasets-server.huggingface.co/rows?dataset=lucadiliello%2Fnaturalquestionsshortqa&config=default&split=validation&offset={offset}&limit=100"
    
    rows = []
    for offset in [0, 100, 200]:
        if len(rows) >= sample_limit:
            break
        r = requests.get(url_tmpl.format(offset=offset), headers=HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
        batch = [item["row"] for item in data.get("rows", [])]
        rows.extend(batch)
    
    rows = rows[:sample_limit]
    
    raw_nq_format = []
    standardized = []
    
    for idx, r in enumerate(rows):
        q_text = r.get("question", "").strip()
        ans_list = r.get("answers", [])
        primary_ans = ans_list[0] if ans_list else ""
        context = r.get("context", "")
        
        raw_nq_format.append(r)
        standardized.append({
            "q_id": f"NQ_{r.get('key', idx)}",
            "benchmark": "Natural Questions",
            "dataset": "google/natural-questions",
            "tier": "Open-Domain QA",
            "question": q_text,
            "ground_truth_answer": primary_ans,
            "supporting_facts": [context[:300]] if context else [],
            "hop_count": 1,
            "is_unanswerable": len(ans_list) == 0,
            "metadata": {
                "all_answers": ans_list,
                "context_length": len(context)
            }
        })

    out_dirs = [BENCHMARK_DATA_DIR / "nq", EVAL_DATASETS_DIR / "nq" / "dev"]
    for d in out_dirs:
        ensure_dir(d)
        save_jsonl(raw_nq_format, d / "dev_samples_300.jsonl")
        save_jsonl(standardized, d / "samples_300.jsonl")
        save_json(standardized, d / "samples_300.json")

    return {"benchmark": "Natural Questions", "count": len(standardized), "status": "SUCCESS"}


# =========================================================================
# 9. TriviaQA
# =========================================================================
def download_triviaqa(sample_limit: int = 300) -> Dict[str, Any]:
    logger.info("--> Fetching TriviaQA (rc.nocontext validation)...")
    url_tmpl = "https://datasets-server.huggingface.co/rows?dataset=mandarjoshi%2Ftrivia_qa&config=rc.nocontext&split=validation&offset={offset}&limit=100"
    
    rows = []
    for offset in [0, 100, 200]:
        if len(rows) >= sample_limit:
            break
        r = requests.get(url_tmpl.format(offset=offset), headers=HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
        batch = [item["row"] for item in data.get("rows", [])]
        rows.extend(batch)
    
    rows = rows[:sample_limit]
    
    standardized = []
    for r in rows:
        ans_obj = r.get("answer", {})
        val = ans_obj.get("value", "")
        aliases = ans_obj.get("aliases", [])
        
        standardized.append({
            "q_id": f"TRIVIA_{r.get('question_id')}",
            "benchmark": "TriviaQA",
            "dataset": "mandarjoshi/trivia_qa",
            "tier": "Knowledge QA",
            "question": r.get("question", "").strip(),
            "ground_truth_answer": val,
            "supporting_facts": [],
            "hop_count": 1,
            "is_unanswerable": False,
            "metadata": {
                "question_source": r.get("question_source"),
                "aliases": aliases
            }
        })

    out_dirs = [BENCHMARK_DATA_DIR / "triviaqa", EVAL_DATASETS_DIR / "triviaqa"]
    for d in out_dirs:
        ensure_dir(d)
        save_jsonl(standardized, d / "samples_300.jsonl")
        save_json(standardized, d / "samples_300.json")

    return {"benchmark": "TriviaQA", "count": len(standardized), "status": "SUCCESS"}


# =========================================================================
# Master Runner
# =========================================================================
def run_all_downloads():
    logger.info("=================================================================")
    logger.info("STARTING ACADEMIC RAG BENCHMARK DOWNLOADS (200-300 SAMPLES EACH)")
    logger.info("=================================================================")
    
    summary = []
    tasks = [
        ("BEIR (SciFact)", lambda: download_beir_scifact(300)),
        ("TREC Deep Learning 2019", lambda: download_trec_dl_2019(200)),
        ("TREC Deep Learning 2020", lambda: download_trec_dl_2020(200)),
        ("HotpotQA", lambda: download_hotpotqa(300)),
        ("2WikiMultihopQA", lambda: download_2wikimultihop(300)),
        ("MuSiQue", lambda: download_musique(300)),
        ("FRAMES", lambda: sample_frames(300)),
        ("Natural Questions", lambda: download_nq(300)),
        ("TriviaQA", lambda: download_triviaqa(300)),
    ]

    for name, func in tasks:
        try:
            res = func()
            summary.append(res)
            logger.info(f"[SUCCESS] {name}: {res['count']} items saved.")
        except Exception as e:
            logger.error(f"[FAILED] {name}: {e}", exc_info=True)
            summary.append({"benchmark": name, "count": 0, "status": f"FAILED: {e}"})

    # Save summary report
    report_path = BENCHMARK_DATA_DIR / "benchmark_inventory.json"
    save_json(summary, report_path)
    logger.info(f"All benchmarks processed. Inventory saved to {report_path}")
    print("\n" + "="*60)
    print("BENCHMARK ACQUISITION SUMMARY:")
    for s in summary:
        print(f" - {s['benchmark']}: {s.get('count', 0)} samples -> {s.get('status')}")
    print("="*60)


if __name__ == "__main__":
    run_all_downloads()
