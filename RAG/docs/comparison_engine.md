# RAISE Multi-University Comparative Reasoning Engine

## 1. Objective
Enable objective, transparent comparative evaluations across institutions without human interpretation bias.

---

## 2. Metric & Currency Normalization Matrix

### Currency Multipliers
All monetary values are parsed with explicit scale multipliers:
* `Crore / Crores / Cr`: $\times 10,000,000$ ($10^7$)
* `Lakh / Lakhs / Lac`: $\times 100,000$ ($10^5$)
* `Million / Millions / M`: $\times 1,000,000$ ($10^6$)
* `Billion / Billions / B`: $\times 1,000,000,000$ ($10^9$)
* `Thousand / K`: $\times 1,000$ ($10^3$)

### Temporal Period Alignment
* **Financial Year (FY)**: E.g., `FY 2023-24` $\to$ start: `2023-04-01`, end: `2024-03-31`, normalized: `2024`.
* **Academic Year (AY)**: E.g., `AY 2023-24` $\to$ start: `2023-07-01`, end: `2024-06-30`, normalized: `2024`.
* **Calendar Year**: E.g., `2024` $\to$ start: `2024-01-01`, end: `2024-12-31`, normalized: `2024`.

---

## 3. Comparability Assessment Rules

| Condition | Comparability Status | System Behavior |
| :--- | :--- | :--- |
| **Identical Units & Normalized Periods** | `COMPARABLE` | Computes direct variance ratio and growth delta with full citations. |
| **Unit or Currency Mismatch** | `PARTIALLY_COMPARABLE` | Reports values side-by-side; explicitly disallows naive ratio calculation without FX conversion. |
| **Scope Mismatch (Gross vs Net)** | `PARTIALLY_COMPARABLE` | Flags institutional scope differences in summary findings. |
| **Missing Data for One Institution** | `INSUFFICIENT_EVIDENCE` | Exposes data absence rather than hallucinating comparison figures. |

---

## 4. Machine-Readable Comparative Output Contract

```json
{
  "university_a": "Panjab University",
  "university_b": "Delhi University",
  "comparison_topic": "research_expenditure",
  "temporal_scope": "2024",
  "comparability_status": "COMPARABLE",
  "metric_rows": [
    {
      "metric_name": "research_expenditure",
      "university_a": "Panjab University",
      "value_a_raw": "₹ 125.70 Crores",
      "value_a_normalized": 1257000000.0,
      "unit_a": "currency",
      "year_a": "2023-2024",
      "provenance_a": { "source_document": "PU_AR_2024.pdf", "page_number": 87 },
      "university_b": "Delhi University",
      "value_b_raw": "₹ 109.40 Crores",
      "value_b_normalized": 1094000000.0,
      "unit_b": "currency",
      "year_b": "2023-2024",
      "provenance_b": { "source_document": "DU_AR_2024.pdf", "page_number": 91 },
      "comparability": "COMPARABLE",
      "variance_ratio": 1.15,
      "comparability_reason": "Identical unit (currency) and currency (INR)."
    }
  ],
  "summary_findings": [
    "For Research Expenditure, Panjab University reported ₹ 125.70 Crores vs Delhi University reported ₹ 109.40 Crores (Comparable)."
  ]
}
```
