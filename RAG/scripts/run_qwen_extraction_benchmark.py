"""
RAISE Real Qwen 14B Isolated Extraction Benchmark
Loads Qwen2.5-14B-Instruct with 4-bit NF4 quantization on NVIDIA RTX 3090 (24 GB VRAM).
Runs real inference on 3 real university PDF chunks from Download/.
Measures GPU VRAM before/after, latency, token count, and saves verifiable test artifact.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
import fitz
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# Real input PDFs
download_dir = Path("/mnt/c/Users/Siddharth Tripathi/Documents/raise/Download")
out_file = Path("/mnt/c/Users/Siddharth Tripathi/Documents/raise/RAG/data/processed/llm_tests/qwen3_14b_extraction_test.json")
out_file.parent.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print(" 🚀 STARTING ISOLATED QWEN 14B REAL EXTRACTION BENCHMARK")
print(f" Target Device: {torch.cuda.get_device_name(0)} (24 GB VRAM)")
print("=" * 80)

# Step 1: Select 3 Real High-Density Chunks from University PDFs
test_chunks = []

# Chunk 1: IIT Madras (Page 10) - 1,200 chars (Curriculum Task Force, NEP, Programs)
pdf1 = download_dir / "Annual Report 2024-25 final upload.pdf"
doc1 = fitz.open(str(pdf1))
txt1 = doc1[9].get_text("text").strip()
doc1.close()
cleaned1 = re.sub(r"\s+", " ", txt1).strip()
test_chunks.append({
    "source_pdf": pdf1.name,
    "page": 10,
    "chunk_id": "iitm_ar25_p010",
    "institution": "Indian Institute of Technology Madras (IIT Madras)",
    "input_text": cleaned1[:1200]
})

# Chunk 2: BRIC (Page 11) - 977 chars (13 Autonomous Research Institutes & Centres)
pdf2 = download_dir / "BRIC-Annual-Report-2025-English.pdf"
doc2 = fitz.open(str(pdf2))
txt2 = doc2[10].get_text("text").strip()  # Page 11
doc2.close()
cleaned2 = re.sub(r"\s+", " ", txt2).strip()
test_chunks.append({
    "source_pdf": pdf2.name,
    "page": 11,
    "chunk_id": "bric_ar25_p011",
    "institution": "Biotechnology Research and Innovation Council (BRIC)",
    "input_text": cleaned2
})

# Chunk 3: NIPGR (Page 3) - 950 chars (Financial Audit, Plant Genome Research, Balance Sheet)
pdf3 = download_dir / "NIPGR_Annual_Report_2024-25.pdf"
doc3 = fitz.open(str(pdf3))
txt3 = doc3[2].get_text("text").strip()  # Page 3
doc3.close()
cleaned3 = re.sub(r"\s+", " ", txt3).strip()
test_chunks.append({
    "source_pdf": pdf3.name,
    "page": 3,
    "chunk_id": "nipgr_ar25_p003",
    "institution": "National Institute of Plant Genome Research (NIPGR)",
    "input_text": cleaned3
})

print(f"Selected {len(test_chunks)} real high-density academic chunks from university PDFs:")
for tc in test_chunks:
    print(f" - [{tc['chunk_id']}] {tc['source_pdf']} (p.{tc['page']}): {len(tc['input_text'])} chars")

# Step 2: Load Qwen 14B in 4-bit NF4 Quantization from local HuggingFace cache
MODEL_ID = "Qwen/Qwen2.5-14B-Instruct"
print(f"\nLoading Model '{MODEL_ID}' from local cache in 4-bit NF4 Quantization onto RTX 3090...")

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16
)

t_load_start = time.time()
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True
)
load_time = round(time.time() - t_load_start, 2)
vram_model_loaded = round(torch.cuda.memory_allocated(0) / (1024 * 1024), 2)
print(f"✅ Model Loaded Successfully in {load_time}s! VRAM Allocated: {vram_model_loaded} MB")

# Step 3: Run Isolated Extraction on each chunk
extraction_results = []

SYSTEM_PROMPT = """You are an expert Academic Knowledge Graph Extraction AI.
Extract structured academic entities and directed relationships from the provided university text.
Strictly return a valid JSON object matching this schema:
{
  "entities": [
    {"name": "...", "type": "University|Department|Centre|Program|Faculty_Person|AdministrativeRole|AcademicRegulation|Requirement|MetricFact", "properties": {}}
  ],
  "relationships": [
    {"subject": "...", "predicate": "HAS_DEPARTMENT|OFFERS_PROGRAM|HAS_CENTRE|GOVERNED_BY|HOLDS_ROLE|REPORTED_METRIC", "object": "..."}
  ]
}
Do not include any conversational preamble or markdown codeblocks outside the JSON."""

def clean_and_parse_json(raw_text: str) -> Tuple[Dict[str, Any], str]:
    text = re.sub(r"^```(?:json)?\s*", "", raw_text.strip())
    text = re.sub(r"```$", "", text).strip()
    try:
        data = json.loads(text)
        return data, "VALID_JSON"
    except Exception as e:
        # Attempt recovery if truncated
        try:
            # Fix trailing comma and close brackets
            recovered = text.rstrip(", \n\r\t")
            if not recovered.endswith("]}") and not recovered.endswith("}"):
                if '"relationships":' in recovered and not recovered.endswith("]"):
                    recovered = recovered.rstrip(", \n\r\t{") + "]}"
                elif not recovered.endswith("}"):
                    recovered = recovered + "}"
            data = json.loads(recovered)
            return data, "RECOVERED_TRUNCATED_JSON"
        except Exception as e2:
            return {}, f"JSON_PARSE_ERROR: {str(e)}"

for idx, chunk in enumerate(test_chunks):
    print(f"\n--- [Executing Chunk {idx+1}/3: {chunk['chunk_id']}] ---")
    
    user_prompt = f"Source Document: {chunk['source_pdf']} (Page {chunk['page']})\nInstitution: {chunk['institution']}\n\nText:\n{chunk['input_text']}"
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    
    text_input = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text_input], return_tensors="pt").to("cuda")
    
    vram_before = round(torch.cuda.memory_allocated(0) / (1024 * 1024), 2)
    t0 = time.time()
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=1536,
            do_sample=False
        )
    
    latency = round(time.time() - t0, 3)
    vram_after = round(torch.cuda.memory_allocated(0) / (1024 * 1024), 2)
    
    generated_tokens = outputs[0][inputs.input_ids.shape[1]:]
    token_count = len(generated_tokens)
    raw_output = tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
    
    parsed_json, validation_status = clean_and_parse_json(raw_output)
    
    res_record = {
        "model_id": MODEL_ID,
        "execution_device": torch.cuda.get_device_name(0),
        "quantization": "bitsandbytes 4-bit NF4",
        "source_pdf": chunk["source_pdf"],
        "page": chunk["page"],
        "chunk_id": chunk["chunk_id"],
        "input_text": chunk["input_text"],
        "inference_telemetry": {
            "vram_allocated_before_mb": vram_before,
            "vram_allocated_after_mb": vram_after,
            "latency_seconds": latency,
            "tokens_generated": token_count,
            "tokens_per_second": round(token_count / latency, 2) if latency > 0 else 0
        },
        "raw_model_output": raw_output,
        "parsed_entities": parsed_json.get("entities", []),
        "parsed_relationships": parsed_json.get("relationships", []),
        "validation_status": validation_status
    }
    
    extraction_results.append(res_record)
    print(f"  Result: {validation_status} in {latency}s ({res_record['inference_telemetry']['tokens_per_second']} tok/s)")
    print(f"  Extracted Entities: {len(res_record['parsed_entities'])} | Relationships: {len(res_record['parsed_relationships'])}")

# Save artifact
benchmark_output = {
    "benchmark_name": "Qwen 14B Real University Extraction Benchmark",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "model_id": MODEL_ID,
    "quantization": "4-bit NF4",
    "device": torch.cuda.get_device_name(0),
    "model_load_vram_mb": vram_model_loaded,
    "total_chunks_tested": len(extraction_results),
    "results": extraction_results
}

out_file.write_text(json.dumps(benchmark_output, indent=2), encoding="utf-8")
print("\n" + "=" * 80)
print(f" ✅ BENCHMARK COMPLETE! Results saved to:")
print(f"    {out_file}")
print("=" * 80)
