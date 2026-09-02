# University Annual Report Knowledge Graph Schema & Data Model

## 1. Domain Ontology

### Entity Nodes
* `University`: Root institution node (e.g. `Panjab University`, `Delhi University`, `IIT Delhi`).
* `Campus`: Physical campus location (`Main Campus`, `South Campus`).
* `Department` / `Centre` / `Institute`: Academic units (`Dept. of Biotechnology`, `School of Chemical Sciences`).
* `Person` / `Leadership`: Key individuals (`Vice Chancellor`, `Director`, `Dean`, `Principal Investigator`).
* `ResearchProject`: Specific funded projects or lab initiatives.
* `IntellectualProperty`: Inventions, patents filed, patents granted, technology transfers.
* `StrategicInitiative`: National and institutional programs (e.g. `BioE3`, `SAHAJ`, `Kisan Kavach`).
* `Grant` / `FundingAgency`: Grant providers (`DBT`, `DST`, `ICMR`, `UGC`, `Industry Partners`).
* `FinancialMetric` / `NumericFact`: Specific quantifiable measurements (`Research Expenditure`, `Total Income`, `Student Enrollment`, `Faculty Count`).
* `TemporalYear`: Explicit temporal periods (`FY2023-24`, `AY2024`, `CalendarYear_2024`).
* `Document` / `Section` / `Table`: Structural provenance anchors.

### Directed Relationships
```
(:University)-[:HAS_DEPARTMENT]->(:Department)
(:Department)-[:HAS_FACULTY]->(:Person)
(:Person)-[:LEADS_PROJECT]->(:ResearchProject)
(:ResearchProject)-[:FUNDED_BY]->(:Grant)
(:University)-[:RECEIVED_GRANT]->(:Grant)
(:University)-[:OWNS_PATENT]->(:IntellectualProperty)
(:University)-[:IMPLEMENTS_INITIATIVE]->(:StrategicInitiative)
(:University)-[:REPORTED_FACT]->(:NumericFact)
(:NumericFact)-[:VALID_FOR_YEAR]->(:TemporalYear)
(:NumericFact)-[:EXTRACTED_FROM_TABLE]->(:Table)
(:Table)-[:LOCATED_IN_SECTION]->(:Section)
(:Section)-[:PART_OF_DOCUMENT]->(:Document)
```

---

## 2. Deterministic Numeric Fact Model
Every numerical measurement is captured as a verified, normalized record:

```json
{
  "fact_id": "fact_pu_2024_res_exp_01",
  "document_id": "PU_Annual_Report_2023_2024",
  "university": "Panjab University",
  "metric_name": "research_expenditure",
  "raw_value": "125.70",
  "normalized_value": 125700000.0,
  "unit": "million",
  "currency": "INR",
  "scale": 1000000,
  "temporal_period": {
    "type": "financial_year",
    "label": "2023-2024",
    "start_date": "2023-04-01",
    "end_date": "2024-03-31"
  },
  "provenance": {
    "source_file": "PU_Annual_Report_2023_2024.pdf",
    "page_number": 87,
    "table_id": "table_p87_t1",
    "row_index": 4,
    "col_index": 2,
    "bbox": [54.2, 310.5, 480.0, 520.0],
    "html_node_id": "sec-research-funding-table-r4"
  },
  "confidence": 0.98,
  "authority_tier": "Official Audited Report"
}
```

---

## 3. Strict 7-Tier Provenance Contract
For any comparison answer generated:

$$\text{Final Answer} \longrightarrow \text{Claim} \longrightarrow \text{Graph Entity/Rel} \longrightarrow \text{Numeric Fact Record} \longrightarrow \text{Semantic HTML Node} \longrightarrow \text{Page Number} \longrightarrow \text{Original PDF BBox}$$

If any step in the provenance chain is broken, the claim is marked `UNVERIFIED` and excluded from the comparative answer.
