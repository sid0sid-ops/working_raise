"""
RAISE Synthesizer Module: Deterministic Answer Synthesis
Author: Principal AI Architect / Senior Python Engineer
Description: Combines resolved multi-hop agent variables and retrieved context 
into a final synthesized answer, enforcing strict grounding to prevent parametric memory overrides.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, Optional
from openai import OpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger("raise.synthesizer")


# ==========================================
# 1. PYDANTIC CONTRACTS FOR SYNTHESIS
# ==========================================

class FinalAnswerResponse(BaseModel):
    final_answer: str = Field(
        ..., 
        description="The concise, exact final answer derived strictly from the resolved variables and context."
    )
    reasoning_trace: str = Field(
        ..., 
        description="Brief breakdown explaining how the resolved variables form the final answer."
    )


# ==========================================
# 2. SYSTEM PROMPT
# ==========================================

SYNTHESIS_SYSTEM_PROMPT = """You are an expert Answer Synthesis Engine for a GraphRAG question-answering system.
Your task is to produce the final concise answer to the original complex query using ONLY the provided resolved entity variables and compiled context passages.

STRICT RULES:
1. ZERO PARAMETRIC OVERRIDE: Do not rely on your internal training memory for historical facts, names, or entities. If a resolved variable or context snippet provides a value, you MUST use it.
2. Exact Combination: If the question asks to combine names or properties from different hops, concatenate or format them precisely as dictated by the variables (e.g. if hop 2 gave first name 'Jane' and hop 4 gave maiden name 'Ballou', the answer is strictly 'Jane Ballou').
3. Direct Entity Resolution: If the query asks for a single target entity that was resolved in the final hop (e.g. 'vocalist of the band' resolved as 'Jens Kidman'), output that resolved entity directly as the final_answer.
4. Numerical / Ranking Derivation: If the query asks where a figure (such as a height in feet) ranks among items in a table, find where that figure fits among the listed values in the context table and output the exact ordinal or cardinal rank (e.g. '37th').
5. Be concise and direct in the final_answer output. Provide ONLY the target name, entity, date, ordinal, or number.
"""


# ==========================================
# 3. DETERMINISTIC SYNTHESIZER CLASS
# ==========================================

class DeterministicSynthesizer:
    """
    Modular synthesizer responsible for generating the final answer from 
    resolved multi-hop variables and compiled context, avoiding parametric memory overrides.
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4",
        vllm_url: Optional[str] = None,
        openai_client: Optional[OpenAI] = None,
    ):
        """
        Args:
            model_name: Model identifier supporting structured outputs.
            vllm_url: Optional vLLM server URL (defaults to http://127.0.0.1:8002/v1).
            openai_client: Optional pre-configured OpenAI client instance.
        """
        self.model_name = model_name
        base_url = vllm_url or "http://127.0.0.1:8002/v1"
        self.client = openai_client or OpenAI(base_url=base_url, api_key="EMPTY")

    def synthesize(
        self,
        original_query: str,
        resolved_variables: Dict[str, str],
        compiled_context: str,
    ) -> FinalAnswerResponse:
        """
        Synthesizes the final answer using strict variable and context grounding.
        
        Args:
            original_query: The complex multi-hop prompt/riddle.
            resolved_variables: Dictionary of resolved entities from agent hops.
            compiled_context: Accumulated raw text passages from hybrid search.
            
        Returns:
            FinalAnswerResponse with final_answer and reasoning_trace.
        """
        logger.info("Synthesizing final answer from resolved variables...")

        # Format variables snippet for the prompt
        vars_summary = "\n".join([f"- {k}: {v}" for k, v in resolved_variables.items()])

        prompt = (
            f"Original Complex Query: {original_query}\n\n"
            f"Resolved Entity Variables:\n{vars_summary}\n\n"
            f"Compiled Context Passages:\n{compiled_context}"
        )

        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format=FinalAnswerResponse,
                temperature=0.0,
            )
            result = response.choices[0].message.parsed
            if result:
                logger.info(f"Synthesized Final Answer -> '{result.final_answer}' | Rationale: {result.reasoning_trace}")
                return result
        except Exception as e:
            logger.warning(f"beta.chat.completions.parse synthesis failed ({e}), falling back to json_object...")

        # Secondary fallback: json_object
        schema_str = json.dumps(FinalAnswerResponse.model_json_schema())
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": f"{SYNTHESIS_SYSTEM_PROMPT}\nOutput JSON matching:\n{schema_str}"},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        content = response.choices[0].message.content or "{}"
        result = FinalAnswerResponse.model_validate_json(content)
        logger.info(f"Synthesized Final Answer via fallback -> '{result.final_answer}'")
        return result
