# RAISE Telemetry & Hardware Resource Accounting

**Version**: 2.5.0  
**Status**: CANONICAL & AUTHORITATIVE  
**Verification Date**: 2026-09-14  

---

## 1. Strict Typing: MetricValue Architecture

To eliminate silent metric fabrication and floating-point ambiguity, RAISE enforces the `MetricValue` typed contract across all telemetry fields:

```python
class MetricSource(str, Enum):
    MEASURED = "MEASURED"       # Empirically measured directly from instrumentation
    DERIVED = "DERIVED"         # Computed via deterministic mathematical formula
    ESTIMATED = "ESTIMATED"     # Heuristic or statistical approximation
    UNAVAILABLE = "UNAVAILABLE" # Data could not be acquired (never fabricated as 0.0)

class MetricValue(BaseModel):
    value: Optional[float]
    source: MetricSource
    unit: str
    confidence: Optional[float] = None
    detail: Optional[str] = None
```

### Invariant Rules
1. If a value is unmeasured, it **must** be emitted as `source="UNAVAILABLE"` with `value=None`. Emitting `0.0` or synthetic numbers is strictly rejected by `test_telemetry_invariants.py`.
2. Timing reconciliation requires that $\ge 90\%$ of overall pipeline wall-clock latency is accounted for by reported sub-stage latencies.

---

## 2. Decoupled Semantic Metrics

Telemetry strictly separates query-evidence relevance from answer-evidence truthfulness:
- `retrieval_relevance_score`: Measures whether retrieved chunks are relevant to the user's question ($[0.0, 1.0]$).
- `nli_entailment_prob` / `nli_contradiction_prob`: Measures whether the generated answer claims are factually truthful according to the retrieved chunks ($[0.0, 1.0]$).

---

## 3. Forensic VRAM Telemetry Breakdown (NVIDIA RTX 3090 — 24 GB)

Direct summation of static model weights (13.1 GB) does not reflect actual operational memory safety. Dynamic KV caching, CUDA allocator reservations, activation workspaces, and Desktop Compositor (DWM) dictate peak stability:

```text
┌────────────────────────────────────────────────────────────────────────┐
│               NVIDIA GeForce RTX 3090 (24,576 MB Total VRAM)          │
├──────────────────────────────────────────────┬─────────────────────────┤
│ ALLOCATION LAYER                             │ VRAM USAGE              │
├──────────────────────────────────────────────┼─────────────────────────┤
│ 1. STATIC MODEL WEIGHTS (Baseline)           │                         │
│    • Qwen 2.5 14B Instruct (GPTQ-Int4)      │  9,216 MB (9.2 GB)      │
│    • FineCat-NLI ModernBERT-Large (FP16)     │  1,536 MB (1.5 GB)      │
│    • BGE-Reranker-Large CrossEncoder (FP16)  │  1,228 MB (1.2 GB)      │
│    • BGE-Large-en-v1.5 Dense Embedder (FP16) │  1,126 MB (1.1 GB)      │
│    Subtotal Static Weights                   │ 13,106 MB (13.1 GB)     │
├──────────────────────────────────────────────┼─────────────────────────┤
│ 2. DYNAMIC RUNTIME RESERVATIONS              │                         │
│    • vLLM PagedAttention KV Cache (at 0.55)  │  3,840 MB (3.8 GB)      │
│    • PyTorch CUDA Caching Allocator Reserve  │  1,536 MB (1.5 GB)      │
│    • Temporary Activation Tensors (Reranker) │  1,228 MB (1.2 GB)      │
│    • Forward Pass Scratchpad & Attention WS  │    768 MB (0.8 GB)      │
│    • Windows DWM Desktop Compositor & Display│    820 MB (0.8 GB)      │
│    Subtotal Dynamic Overhead                 │  8,192 MB (8.2 GB)      │
├──────────────────────────────────────────────┼─────────────────────────┤
│ OBSERVED PEAK RUNTIME VRAM                   │ 21,298 MB (21.3 GB)     │
│ CRITICAL SAFETY MARGIN (Headroom to OOM)     │  3,278 MB (3.3 GB)      │
└──────────────────────────────────────────────┴─────────────────────────┘
```

> [!WARNING]
> If vLLM is launched with standard default `--gpu-memory-utilization 0.90` (22.1 GB reserved), loading BGE-Reranker or FineCat-NLI onto the same GPU triggers instant `torch.cuda.OutOfMemoryError`. vLLM **must** be capped strictly at `--gpu-memory-utilization 0.55`.
