"""
FineCat-NLI Local Inference Engine
===================================
Harnesses dleemiller/finecat-nli-l (ModernBERT-large, 395M parameters)
for high-precision semantic entailment and contradiction detection.

Hardware Target : cuda:0 (auto-detected GPU) / FP16
Context Length  : 8,192 tokens (ModernBERT native RoPE)
Label Mapping   : 0: entailment, 1: neutral, 2: contradiction
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Global model cache to prevent redundant PyTorch allocations
_CACHED_MODEL = None
_CACHED_TOKENIZER = None
_CACHED_DEVICE = None
_LOAD_FAILED = False


class FineCatNLIVerifier:
    """
    Local Cross-Encoder NLI Verifier utilizing ModernBERT-large backbone
    specifically fine-tuned on curated multi-source NLI benchmarks.
    """

    MODEL_ID = "dleemiller/finecat-nli-l"
    LABEL_MAPPING = {0: "ENTAILMENT", 1: "NEUTRAL", 2: "CONTRADICTION"}

    def __init__(self, model_id: Optional[str] = None, max_length: int = 4096):
        self.model_id = model_id or self.MODEL_ID
        self.max_length = max_length

    @classmethod
    def _ensure_loaded(cls, model_id: str = MODEL_ID) -> bool:
        """Loads weights and tokenizer once into GPU VRAM as a singleton."""
        global _CACHED_MODEL, _CACHED_TOKENIZER, _CACHED_DEVICE, _LOAD_FAILED
        if _CACHED_MODEL is not None and _CACHED_TOKENIZER is not None:
            return True
        if _LOAD_FAILED:
            return False

        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            device = "cuda:0" if torch.cuda.is_available() else "cpu"
            model_dtype = torch.float16 if "cuda" in device else torch.float32

            token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
            try:
                tokenizer = AutoTokenizer.from_pretrained(model_id, token=token, local_files_only=True)
                model = AutoModelForSequenceClassification.from_pretrained(
                    model_id,
                    dtype=model_dtype,
                    token=token,
                    local_files_only=True,
                )
            except Exception:
                tokenizer = AutoTokenizer.from_pretrained(model_id, token=token)
                model = AutoModelForSequenceClassification.from_pretrained(
                    model_id,
                    dtype=model_dtype,
                    token=token,
                )
            model.to(device)
            model.eval()

            _CACHED_MODEL = model
            _CACHED_TOKENIZER = tokenizer
            _CACHED_DEVICE = device
            _LOAD_FAILED = False
            logger.info("FineCat-NLI (%s) loaded successfully on %s", model_id, device)
            return True
        except Exception as exc:
            logger.warning("Could not initialize FineCat-NLI locally: %s. Falling back to heuristic NLI.", exc)
            _LOAD_FAILED = True
            return False

    @property
    def is_available(self) -> bool:
        return _CACHED_MODEL is not None and _CACHED_TOKENIZER is not None

    def classify_pair(self, premise: str, hypothesis: str) -> Dict[str, Any]:
        """
        Evaluates a single (premise, hypothesis) pair.
        Returns probabilities and discrete verdict: ENTAILMENT, NEUTRAL, or CONTRADICTION.
        """
        batch_res = self.classify_batch([(premise, hypothesis)])
        return batch_res[0] if batch_res else self._heuristic_fallback(premise, hypothesis)

    def classify_batch(self, pairs: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """
        Executes batched NLI inference over multiple (premise, hypothesis) pairs.
        """
        if not pairs:
            return []

        if not self.is_available and not self._ensure_loaded(self.model_id):
            return [self._heuristic_fallback(p, h) for p, h in pairs]

        import torch

        results: List[Dict[str, Any]] = []
        t0 = time.perf_counter()

        try:
            premises = [p for p, _ in pairs]
            hypotheses = [h for _, h in pairs]

            inputs = _CACHED_TOKENIZER(
                premises,
                hypotheses,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            ).to(_CACHED_DEVICE)

            with torch.inference_mode():
                outputs = _CACHED_MODEL(**inputs)
                logits = outputs.logits
                logits_np = logits.cpu().float().numpy()
                probs = torch.softmax(logits, dim=-1).cpu().float().numpy()

            elapsed_ms = (time.perf_counter() - t0) * 1000.0 / max(len(pairs), 1)

            for logit_row, prob_row in zip(logits_np, probs):
                ent_prob = float(prob_row[0])
                neu_prob = float(prob_row[1])
                con_prob = float(prob_row[2])

                raw_logits = {
                    "entailment": round(float(logit_row[0]), 4),
                    "neutral": round(float(logit_row[1]), 4),
                    "contradiction": round(float(logit_row[2]), 4),
                }
                softmax_probs = {
                    "entailment": round(ent_prob, 4),
                    "neutral": round(neu_prob, 4),
                    "contradiction": round(con_prob, 4),
                }

                # Tri-State Decision Logic:
                # 1. Hard contradiction check
                # 2. Strong entailment check
                # 3. Neutral / uncertain (insufficient evidence)
                if con_prob >= 0.50:
                    verdict = "CONTRADICTION"
                    is_entailed = False
                    is_contradiction = True
                    decision_reason = f"Contradiction detected (P(C)={con_prob:.2f} >= 0.50); claim conflicts with premise."
                elif ent_prob >= 0.60 and con_prob < 0.20:
                    verdict = "ENTAILMENT"
                    is_entailed = True
                    is_contradiction = False
                    decision_reason = f"Entailment verified (P(E)={ent_prob:.2f} >= 0.60, P(C)={con_prob:.2f} < 0.20)."
                else:
                    verdict = "NEUTRAL"
                    is_entailed = False
                    is_contradiction = False
                    decision_reason = f"Neutral / Insufficient evidence (P(N)={neu_prob:.2f}, P(E)={ent_prob:.2f}, P(C)={con_prob:.2f}); path uncertain."

                results.append({
                    "entailment_prob": round(ent_prob, 4),
                    "neutral_prob": round(neu_prob, 4),
                    "contradiction_prob": round(con_prob, 4),
                    "raw_logits": raw_logits,
                    "softmax_probs": softmax_probs,
                    "calibration_status": "UNVALIDATED_RAW_SOFTMAX",
                    "decision_reason": decision_reason,
                    "verdict": verdict,
                    "is_entailed": is_entailed,
                    "is_contradiction": is_contradiction,
                    "latency_ms": round(elapsed_ms, 2),
                    "fallback": False,
                })
            return results
        except Exception as exc:
            logger.warning("FineCat-NLI inference failed: %s. Falling back to heuristic.", exc)
            return [self._heuristic_fallback(p, h) for p, h in pairs]

    def _heuristic_fallback(self, premise: str, hypothesis: str) -> Dict[str, Any]:
        """
        Zero-crash offline fallback using token and n-gram overlap.
        """
        p_lower = premise.lower()
        h_words = [w for w in hypothesis.lower().split() if len(w) > 3]
        if not h_words:
            return {
                "entailment_prob": 1.0,
                "neutral_prob": 0.0,
                "contradiction_prob": 0.0,
                "raw_logits": None,
                "softmax_probs": {"entailment": 1.0, "neutral": 0.0, "contradiction": 0.0},
                "calibration_status": "UNVALIDATED_HEURISTIC",
                "decision_reason": "Trivially entailed; hypothesis contains no content tokens.",
                "verdict": "ENTAILMENT",
                "is_entailed": True,
                "is_contradiction": False,
                "latency_ms": 0.0,
                "fallback": True,
            }

        hits = sum(1 for w in h_words if w in p_lower)
        ratio = hits / len(h_words)

        has_negation = any(neg in hypothesis.lower() for neg in [" not ", " never ", " no ", " neither "])
        has_premise_neg = any(neg in p_lower for neg in [" not ", " never ", " no ", " neither "])

        if has_negation != has_premise_neg and ratio > 0.6:
            con_prob = 0.70
            ent_prob = 0.15
            neu_prob = 0.15
            verdict = "CONTRADICTION"
            decision_reason = "Contradiction detected via negation mismatch on shared keyword content."
        elif ratio >= 0.75:
            ent_prob = round(ratio, 4)
            neu_prob = round(1.0 - ratio, 4)
            con_prob = 0.0
            verdict = "ENTAILMENT"
            decision_reason = f"Heuristic high lexical entailment ({ratio*100:.1f}% token overlap)."
        elif ratio >= 0.40:
            ent_prob = round(ratio, 4)
            neu_prob = round(max(0.0, 1.0 - ratio - 0.05), 4)
            con_prob = 0.05
            verdict = "ENTAILMENT" if ratio >= 0.60 else "NEUTRAL"
            decision_reason = f"Heuristic moderate overlap ({ratio*100:.1f}% token overlap); verdict={verdict}."
        else:
            ent_prob = round(ratio, 4)
            neu_prob = 0.60
            con_prob = 0.20
            verdict = "NEUTRAL"
            decision_reason = f"Heuristic low overlap ({ratio*100:.1f}% token overlap); insufficient evidence."

        return {
            "entailment_prob": ent_prob,
            "neutral_prob": neu_prob,
            "contradiction_prob": con_prob,
            "raw_logits": None,
            "softmax_probs": {
                "entailment": ent_prob,
                "neutral": neu_prob,
                "contradiction": con_prob,
            },
            "calibration_status": "UNVALIDATED_HEURISTIC",
            "decision_reason": decision_reason,
            "verdict": verdict,
            "is_entailed": (ent_prob >= 0.60 and con_prob < 0.20),
            "is_contradiction": (con_prob >= 0.50),
            "latency_ms": 0.0,
            "fallback": True,
        }


# Module-level instance for convenient import
nli_verifier = FineCatNLIVerifier()
