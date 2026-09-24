# RAISE Grounding & Anti-Hallucination Quality Gate

**Version**: 2.5.0  
**Status**: CANONICAL & AUTHORITATIVE  
**Verification Date**: 2026-09-14  

---

## 1. Grounding Philosophy

In academic, institutional, and financial research, hallucinations are catastrophic. A fabricated research grant figure or non-existent board resolution completely destroys system trustworthiness. 

RAISE operates under a **zero-tolerance policy for ungrounded claims**. Answers are permitted to reach the user if and only if every factual proposition is corroborated by retrieved evidence down to exact pages and numbers.

---

## 2. 4-Tier Hybrid Escalation Architecture

Neural Natural Language Inference (NLI) is computationally expensive (~15-40ms per claim forward pass) and can suffer from GPU compute preemption if executed concurrently with LLM token streaming. 

To maximize throughput while guaranteeing mathematical exactness, RAISE employs a **4-Tier Escalation Gating Cascade**:

```mermaid
flowchart TD
    Claim["Extracted Atomic Claim C_i"] --> Tier1{"Tier 1: Deterministic Constraints<br/>(Numbers / Dates / Currencies / Negatives)"}
    
    Tier1 -->|Numerical Mismatch| Contradiction1["FAIL: Status = NUMERICAL_MISMATCH"]
    Tier1 -->|Negative Assertion Verified| Pass1["DIRECT PASS: Status = SUPPORTED"]
    Tier1 -->|Numbers Verified / No Numbers| Tier2{"Tier 2: Lexical Fast-Path (<= 1ms)<br/>Overlap >= 70% or N-gram >= 80%"}
    
    Tier2 -->|High Overlap| Pass2["DIRECT PASS: Status = DIRECT"]
    Tier2 -->|Ambiguous Overlap (0.20 <= Overlap < 0.70)| Tier3{"Tier 3: FineCat-NLI Engine<br/>ModernBERT-Large (8k context) on GPU"}
    
    Tier3 -->|P(Contradiction) >= 0.50| Contradiction2["FAIL: Status = CONTRADICTION"]
    Tier3 -->|P(Entailment) >= 0.60 and P(C) < 0.20| Pass3["PASS: Status = NLI_ENTAILED"]
    Tier3 -->|Neutral / Ambiguous (0.20 <= P(E) < 0.60)| Tier4{"Tier 4: Soft Containment & Multi-Hop Fallback<br/>Context Expansion"}
    
    Tier4 -->|Containment Verified| Pass4["PASS: Status = SUPPORTED (Fallback)"]
    Tier4 -->|Uncorroborated| FailFinal["FAIL: Status = UNSUPPORTED"]
    
    Pass1 --> QualityGateAggregator["Quality Gate Aggregator<br/>Faithfulness = Supported / Total Claims"]
    Pass2 --> QualityGateAggregator
    Pass3 --> QualityGateAggregator
    Pass4 --> QualityGateAggregator
    Contradiction1 --> QualityGateAggregator
    Contradiction2 --> QualityGateAggregator
    FailFinal --> QualityGateAggregator
```

### Tier Descriptions & Decision Rules

1. **Tier 1: Deterministic Math & Constraints Engine (`math_engine.py`)**:
   - Extracts all floating-point numbers, percentages, dates, and monetary amounts via regex.
   - Verifies exact presence or pairwise arithmetic derivation within $\pm 0.05$ tolerance (e.g. verifying aggregated revenue derived from $e_1 + e_2$).
   - If any number in the claim is contradicted by the evidence, immediately marks `NUMERICAL_MISMATCH` (rejection).
   - Verifies grounded negative assertions (e.g. *"the report does not state..."*) to prevent false rejection of honest refusals.

2. **Tier 2: Lexical Fast-Path ($\le 1	ext{ ms}$)**:
   - Computes token overlap ratio and consecutive bigram/n-gram ratios.
   - Claims with $\ge 70\%$ grounding score or $\ge 80\%$ token overlap pass immediately with `status="DIRECT"`, resolving 82.7% of claims in sub-millisecond latency.

3. **Tier 3: FineCat-NLI Neural Entailment (`nli_verifier.py`)**:
   - Evaluates ambiguous, paraphrased, or synthesized claims using **FineCat-NLI** (`dleemiller/finecat-nli-l`).
   - **Backbone**: ModernBERT-large (395M parameters, native 8,192 token rotary position embeddings, FP16 inference on `cuda:0`).
   - **Tri-State Gating Rules**:
     $$P(	ext{contradiction}) \ge 0.50 \implies 	ext{CONTRADICTION}$$
     $$P(	ext{entailment}) \ge 0.60 \land P(	ext{contradiction}) < 0.20 \implies 	ext{NLI\_ENTAILED}$$
     $$	ext{Otherwise} \implies 	ext{NEUTRAL (Escalate to Tier 4)}$$

4. **Tier 4: Soft Containment & Context Expansion Fallback**:
   - Broadens evidence window across parent chunks and linked graph entities.
   - Evaluates multi-chunk containment ($grounding \ge 0.35$ or $overlap \ge 0.45$).
   - If evidence remains unestablished, marks claim as `UNSUPPORTED`.

---

## 3. Canonical Claim Verification Contract (`ClaimVerificationRecord`)

Every claim evaluated by `RAG/src/features/evaluation/engine.py:verify_claims` emits a structured record:

```python
class ClaimVerificationRecord:
    claim_text: str
    status: str                         # "SUPPORTED" | "CONTRADICTION" | "UNSUPPORTED"
    grounding_score: float              # [0.0, 1.0]
    verification_path: VerificationPath # Enum: DETERMINISTIC, NLI, DETERMINISTIC+NLI, EVIDENCE_EXPANSION+NLI, CONTROLLED_ABSTENTION
    decision_reason: str                # Explanatory causal rationale
    raw_logits: Optional[Dict[str, float]]    # Unscaled logits {"contradiction": l_c, "neutral": l_u, "entailment": l_e}
    softmax_probs: Optional[Dict[str, float]] # Softmax probabilities summing to 1.0
    calibration_status: str             # "UNVALIDATED_RAW_SOFTMAX"
```

### Logits vs. Softmax vs. Calibration Rationale
- **Raw Logits**: Preserved directly from the neural classification head before non-linear compression.
- **Softmax Probabilities**: Normalized exponential distribution over the three classes. Softmax normalization enforces $\sum P_i = 1.0$, but does **not** guarantee true calibration under out-of-domain distribution shift.
- **Calibration Status**: Explicitly set to `"UNVALIDATED_RAW_SOFTMAX"` to prevent downstream systems from treating raw softmax outputs as true Bayesian posterior probabilities.

---

## 4. Controlled Safe Abstention vs. Fallback Dumping

In complex multi-hop institutional reasoning, when evidence fails to establish a rigorous deductive chain:
- **Anti-Pattern Rejected (Source Dumping)**: Emitting raw retrieved chunk summaries produces non-responsive text that technically scores low on hallucinations but fails answer correctness.
- **Architectural Policy**: When multi-hop reasoning fails or quality gating rejects the synthesized chain, the pipeline triggers **Controlled Safe Abstention**:
  ```text
  INSUFFICIENT REASONING PATH
  Required reasoning chain could not be established.
  No answer released.
  ```
- **Benchmark Distinction**: Enables evaluators to cleanly distinguish between `correct`, `wrong`, and `abstained` without rewarding non-responsive text.

---

## 5. Quality Gate Evaluation Thresholds

- **Faithfulness Score**:
  $$	ext{Faithfulness} = rac{	ext{Count}(	ext{Supported Claims})}{	ext{Total Extracted Claims}}$$
- **Acceptance Threshold**: $	ext{Faithfulness} \ge 0.80$ with **zero** numerical contradictions.
- If rejected, the answer is replaced with the safe refusal envelope and audited in PostgreSQL and telemetry logs.
