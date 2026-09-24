# Latency, Concurrency, and Resource Optimization

## Overview
Running GraphRAG systems under production concurrent traffic requires proactive resource allocation across the database, vector indexing, and inference tiers to maintain sub-second response latencies and high throughput.

---

## 1. vLLM Key-Value (KV) Cache Management
Serving Qwen 2.5 7B with **vLLM** eliminates GPU memory fragmentation through **PagedAttention**:
1. **PagedAttention Block Allocation**:
   - Manages KV cache memory in non-contiguous virtual memory blocks (e.g., `block_size=16` or `32` tokens), reducing VRAM waste from >60% to <4%.
2. **Automatic Prefix Caching**:
   - Reuses pre-computed KV cache tensors across requests that share identical system prompts, static `GRAPH SCHEMA DEFINITION` strings, and few-shot examples.
3. **GPU Memory Allocation**:
   - `gpu_memory_utilization=0.90`: Reserves 90% of GPU VRAM for model weights and dynamic KV cache expansion while preventing Out-of-Memory (OOM) spikes during concurrent batching.

---

## 2. Context Window Budgets (8,192 Token Budget Allocation)
To prevent context overflow and preserve attention focus during synthesis, the total context budget is strictly partitioned:

| Budget Tier | Max Tokens | Allocation % | Purpose |
| :--- | :--- | :--- | :--- |
| **System & Prompt Instructions** | 500 | ~6% | Persona, anti-hallucination rules, citation format. |
| **Graph Schema & Triplet Evidence** | 1,500 | ~18% | Active node/edge schema definitions + extracted multi-hop triples. |
| **Dense Vector Passages** | 3,500 | ~43% | Top 3–5 Cross-Encoder reranked document chunks. |
| **Conversational History (Turns)** | 1,500 | ~18% | Checkpointed short-term conversational turns. |
| **Generation Buffer** | 1,192 | ~15% | Reserved completion space for grounded answer and citations. |
| **TOTAL** | **8,192** | **100%** | Full context window constraint for Qwen 2.5 7B. |

---

## 3. Query Result Caching (Tiered Cache Architecture)
To bypass redundant LLM inference and database graph queries for repeated or high-frequency queries:

```
User Query ──► [Normalize & Hash: SHA-256(q)]
                      │
                      ├──► [Tier 1: In-Memory LRU Cache] ──► (Hit: Latency < 1ms)
                      │          │ (Miss)
                      │          ▼
                      ├──► [Tier 2: Persistent Disk Cache (TTL = 24h)] ──► (Hit: Latency < 5ms)
                      │          │ (Miss)
                      │          ▼
                      └──► [Full GraphRAG Execution: LangGraph + Neo4j + Qwen]
```

- **Deterministic Query Normalization**: Lowercase, whitespace stripping, and sorted entity parameter binding.
- **Granular Cache Invalidation**: Automated cache invalidation when new document reports are ingested or graph schema definitions evolve.
