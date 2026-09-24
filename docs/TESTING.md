# RAISE Testing Strategy & Regression Suite Specification

**Version**: 2.5.0  
**Status**: CANONICAL & AUTHORITATIVE  
**Verification Date**: 2026-09-14  

---

## 1. Testing Philosophy

RAISE enforces deterministic, reproducible verification across unit, integration, and security layers. All tests run via `pytest` and must achieve **100% pass rates** prior to release.

---

## 2. Test Suite Topology & Inventory

The test harness comprises **31+ test suites** categorized by subsystem:

| Subsystem / Suite | Test File | Test Count | Pass Rate | Execution Target |
| :--- | :--- | :--- | :--- | :--- |
| **API & Gateway Contracts** | `tests/api/test_routes.py`<br/>`tests/test_operator_and_frontend_contract.py` | 27 tests | **100%** | FastAPI routes, SSE stream headers, CORS, dual-key session storage |
| **Full System Integration** | `tests/test_full_system.py` | 33 tests | **100%** | End-to-end RAG, grounding verification, citation binding |
| **FineCat-NLI & Telemetry** | `tests/test_finecat_nli.py`<br/>`tests/test_telemetry_invariants.py` | 23 tests | **100%** | ModernBERT NLI thresholds, MetricValue normalization, zero-fabrication |
| **FRAMES Benchmark Pipeline**| `tests/test_frames_benchmark.py` | 8 tests | **100%** | Isolation harness, factuality, retrieval coverage, failure taxonomy |
| **Operator & Subsystems** | `tests/operator/test_developer_operator_dashboard.py` | 26 tests | **100%** | Postgres, Redis, Neo4j, vLLM health audits |
| **Security & Outbox** | `tests/security/` | 12 tests | **100%** | Cypher AST injection, session revocation, rate-limiting |
| **Ingestion, Table & Math** | `tests/test_table_and_math_engine.py`<br/>`tests/test_docling_ingestion.py` | 31 tests | **100%** | Docling layout, TableFormer, IEEE-754 arithmetic |
| **Master Pipeline & Invariants**| `tests/test_master_end_to_end_pipeline.py`<br/>`tests/test_system_synthesis_formatting.py` | 35 tests | **100%** | Telemetry reconciliation, Markdown sanitization |
| **Total Code Regression Suite**| All 31+ test suites | **187+ tests**| **100.0%**| **Deterministic Baseline Certified** |

---

## 3. Test Execution Commands

### Quick Sanity Test (Focused Suites)
```bash
cd RAG
pytest tests/test_frames_benchmark.py tests/test_finecat_nli.py tests/test_telemetry_invariants.py tests/test_system_synthesis_formatting.py -v
```

### Full Regression Suite
```bash
cd RAG
pytest -q
```

### Specific Subsystem Tests
```bash
# API & Contract Tests
pytest tests/api/ -v

# Security Tests
pytest tests/security/ -v

# Ingestion & Chunking Tests
pytest tests/test_advanced_chunking.py -v
```
