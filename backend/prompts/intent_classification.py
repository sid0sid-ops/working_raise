"""
RAISE Academic GraphRAG Studio - Query Intent Classification Prompt Module
Formats incoming natural language user queries for deterministic classification
into strategic GraphRAG retrieval modalities (Global, Local Cypher, Hybrid Vector, Table Math).
"""

from typing import Any, Dict, List, Optional


INTENT_CLASSIFICATION_PROMPT = """<system_role>
You are an intent classification and query planning model for the RAISE Academic GraphRAG Studio.
Your objective is to analyze the user's research query regarding academic and corporate annual reports and classify it into one primary retrieval mode.
</system_role>

<classification_categories>
1. ACADEMIC_RESEARCH:
   - Inquiries about academic curricula, research programs, faculty publications, patents, labs, and competitive grants.
2. FINANCIAL_FACT:
   - Specific queries about revenue, profit, turnover, EBITDA, budget allocations, academic fees, fellowship funds, or financial statement line items.
3. INSTITUTIONAL_PROFILE:
   - Queries regarding organizational vision, leadership, departments, centers of excellence, boards of governors, or institutional history.
4. STATISTICAL_METRIC:
   - Specific counts or rankings: student enrollments, faculty counts, graduation numbers, placements, or accreditation metrics.
5. MULTI_HOP_RELATION:
   - Complex graph paths: startup mentorship chains, industry spin-offs, interdisciplinary initiatives, foreign university MoUs.
6. OUT_OF_SCOPE:
   - General trivia, conversational greetings, or questions outside document contents.
</classification_categories>

<output_contract>
Respond strictly in valid JSON format with no additional markdown preamble:
{
  "intent": "ACADEMIC_RESEARCH | FINANCIAL_FACT | INSTITUTIONAL_PROFILE | STATISTICAL_METRIC | MULTI_HOP_RELATION | OUT_OF_SCOPE",
  "entities": ["entity1", "entity2"],
  "requires_graph": true,
  "requires_vector": true,
  "requires_tables": false,
  "reasoning": "Short justification for chosen intent"
}
</output_contract>
"""


def get_intent_classification_prompt() -> str:
    """Returns the intent classification system prompt."""
    return INTENT_CLASSIFICATION_PROMPT.strip()


def build_intent_classification_messages(query: str) -> List[Dict[str, str]]:
    """Builds chat messages for intent classification."""
    return [
        {"role": "system", "content": get_intent_classification_prompt()},
        {"role": "user", "content": f"Classify the following query:\n\n{query.strip()}"}
    ]