# Query Intent Classification Prompt

Analyze the user's research query regarding academic and university annual reports.

## Intent Categories:
1. `ACADEMIC_RESEARCH`: Research programs, faculty publications, patents, labs, grants.
2. `FINANCIAL_FACT`: Budget allocations, revenue, expenses, fees, fellowships, funding numbers.
3. `INSTITUTIONAL_PROFILE`: Vision, mission, leadership, departments, centers, history.
4. `STATISTICAL_METRIC`: Student counts, faculty counts, graduation rates, rankings.
5. `MULTI_HOP_RELATION`: Interdisciplinary partnerships, spin-offs, collaborative projects.
6. `OUT_OF_SCOPE`: Non-academic queries, personal advice, general trivia outside institutional reports.

## Output Format:
Return a JSON object:
```json
{
  "intent": "ACADEMIC_RESEARCH",
  "entities": ["extracted_keywords"],
  "requires_graph": true,
  "requires_vector": true,
  "requires_tables": false
}
```
