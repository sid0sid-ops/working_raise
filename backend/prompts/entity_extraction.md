# Academic Entity and Relationship Extraction Prompt

Extract academic domain entities and their directed relationships from the provided university document text.

## Target Entity Labels:
- University, Department, Centre, Facility
- Faculty, Researcher, Scholar, Leadership
- Program, Degree, Course
- ResearchProject, Grant, FundingAgency
- Publication, Journal, Patent, Technology
- Startup, Incubator, IndustryPartner
- Award, Honour, Metric, FinancialAllocation

## Target Relationship Types:
- AFFILIATED_WITH, HOSTED_BY, DIRECTED_BY
- OFFERS_PROGRAM, CONDUCTS_RESEARCH, FUNDED_BY
- PUBLISHED, GRANTED_PATENT, INCUBATED
- RECEIVED_AWARD, ALLOCATED_BUDGET, PARTNERED_WITH

## Output Format:
Return a JSON object containing `entities` and `relations`:
```json
{
  "entities": [
    {"name": "Entity Name", "label": "EntityType", "properties": {"page": 1}}
  ],
  "relations": [
    {"source": "Entity1", "target": "Entity2", "type": "RELATION_TYPE"}
  ]
}
```
