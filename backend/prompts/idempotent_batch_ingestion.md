# Idempotent Cypher Schema and Parameterized Batch Ingestion

## 1. Uniqueness Constraints & Transactional Indices Pre-Establishment
To prevent Cartesian product explosions, avoid duplicate graph entity generation across multiple document ingestion runs, and maintain sub-second transactional lookups, uniqueness constraints and property indices are established prior to data ingestion.

### A. Idempotent Schema Constraints:
```cypher
// Identity & Uniqueness Constraints
CREATE CONSTRAINT institution_name_unique IF NOT EXISTS FOR (n:Institution) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE;
CREATE CONSTRAINT grant_id_unique IF NOT EXISTS FOR (g:Grant) REQUIRE g.grant_id IS UNIQUE;
CREATE CONSTRAINT patent_id_unique IF NOT EXISTS FOR (p:Patent) REQUIRE p.patent_id IS UNIQUE;
CREATE CONSTRAINT table_id_unique IF NOT EXISTS FOR (t:Table) REQUIRE t.table_id IS UNIQUE;
CREATE CONSTRAINT student_id_unique IF NOT EXISTS FOR (s:Student) REQUIRE s.student_id IS UNIQUE;
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE;
```

### B. High-Selectivity Property Indices:
```cypher
CREATE INDEX chunk_doc_idx IF NOT EXISTS FOR (c:Chunk) ON (c.document_id);
CREATE INDEX section_type_idx IF NOT EXISTS FOR (n:Section) ON (n.type);
CREATE INDEX department_name_idx IF NOT EXISTS FOR (n:Department) ON (n.name);
CREATE INDEX centre_name_idx IF NOT EXISTS FOR (n:CentreOfExcellence) ON (n.name);
CREATE INDEX person_name_idx IF NOT EXISTS FOR (n:Person) ON (n.name);
CREATE INDEX role_title_idx IF NOT EXISTS FOR (n:ExecutiveRole) ON (n.title);
CREATE INDEX sponsor_name_idx IF NOT EXISTS FOR (n:SponsorAgency) ON (n.name);
CREATE INDEX startup_name_idx IF NOT EXISTS FOR (n:Startup) ON (n.name);
CREATE INDEX incubator_name_idx IF NOT EXISTS FOR (n:Incubator) ON (n.name);
CREATE INDEX industry_partner_idx IF NOT EXISTS FOR (n:IndustryPartner) ON (n.name);
CREATE INDEX program_name_idx IF NOT EXISTS FOR (n:AcademicProgram) ON (n.name);
CREATE INDEX fin_stmt_fy_idx IF NOT EXISTS FOR (n:FinancialStatement) ON (n.fiscal_year);
CREATE INDEX equipment_name_idx IF NOT EXISTS FOR (n:Equipment) ON (n.name);
CREATE INDEX facility_name_idx IF NOT EXISTS FOR (n:Facility) ON (n.name);
```

---

## 2. Parameterized Batch Ingestion Pattern
Ingestion operations are executed in batches via parameterized Cypher scripts using `MERGE` clauses. By avoiding direct string concatenation, this pattern prevents Cypher injection vulnerabilities and enables query compilation caching within the Neo4j transactional planner.

### A. Parameterized Node Batch Ingestion (`UNWIND $batch`):
```cypher
UNWIND $batch AS item
MERGE (n:Entity {id: item.id})
ON CREATE SET 
    n.name = item.name,
    n.label = item.label,
    n.type = item.type,
    n.page = item.page,
    n.document_id = item.document_id,
    n.properties = item.properties,
    n.created_at = timestamp()
ON MATCH SET 
    n.name = coalesce(item.name, n.name),
    n.type = coalesce(item.type, n.type),
    n.page = coalesce(item.page, n.page),
    n.document_id = coalesce(item.document_id, n.document_id),
    n.updated_at = timestamp();
```

### B. Parameterized Edge / Relationship Batch Ingestion:
```cypher
UNWIND $batch AS rel
MATCH (src {id: rel.source_id})
MATCH (tgt {id: rel.target_id})
MERGE (src)-[r:RELATED_TO {type: rel.type}]->(tgt)
ON CREATE SET 
    r.created_at = timestamp(),
    r.confidence = coalesce(rel.confidence, 1.0),
    r.document_id = rel.document_id
ON MATCH SET 
    r.updated_at = timestamp();
```

---

## 3. Operational Performance Characteristics
1. **Compilation Plan Caching**: Because parameterized queries (`$batch`) maintain static Cypher ASTs, the Neo4j planner executes subsequent batches with zero re-planning overhead.
2. **Zero Injection Risk**: Arbitrary user or parsed textual strings are isolated within the binary parameter envelope rather than evaluated in the query grammar.
3. **Locking & Deadlock Avoidance**: Nodes are sorted by `id` prior to executing batch `UNWIND` statements, ensuring deterministic locking order during concurrent writes.
