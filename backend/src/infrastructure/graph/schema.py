"""
Comprehensive Neo4j Schema Definition and Indexing Helper for RAISE Academic GraphRAG.
Defines all 37 Node Labels, Properties, 50 Relationship Types, Uniqueness Constraints,
and automatically applies performance-optimized Neo4j indexes and constraints.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Any

if TYPE_CHECKING:
    from src.infrastructure.graph.neo4j import Neo4jDatabase

# Lean, Simplified 6-Category Schema for Low-Latency, Zero-Hallucination Cypher Generation
SIMPLIFIED_NODE_LABELS = [
    "Startup",           # Deep-tech commercial ventures (e.g., XYMA Analytics, Mindgrove, NeoMotion)
    "EcosystemEnabler",  # Incubation cells, tech parks, accelerators (e.g., IITMIC, IITM Research Park)
    "CoE",               # Centres of Excellence, specialised research labs & departments
    "Institution",       # Core universities and institutions (e.g., IIT Madras, BRIC, Panjab University)
    "Person",            # Key researchers, PIs, founders, and directors
    "Metric",            # Financial grants, patent counts, investments, revenue metrics
]

SIMPLIFIED_RELATIONSHIPS = [
    "INCUBATED",         # (EcosystemEnabler)-[:INCUBATED]->(Startup)
    "FOUNDED_BY",        # (Startup)-[:FOUNDED_BY]->(Person)
    "OPERATES",          # (Institution)-[:OPERATES]->(EcosystemEnabler / CoE)
    "FUNDED_BY",         # (Startup / CoE)-[:FUNDED_BY]->(Metric / Institution)
    "ACHIEVED",          # (Startup)-[:ACHIEVED]->(Metric)
    "AFFILIATED_WITH",   # (Person)-[:AFFILIATED_WITH]->(Institution / CoE)
    "COLLABORATES_WITH", # (Startup / CoE)-[:COLLABORATES_WITH]->(Institution)
]

# Comprehensive Schema Node Labels (37 Types + Hierarchical Extensions)
NODE_LABELS = [
    "Institution", "AnnualReport", "Section", "Chunk", "Table",
    "ParentChunk", "ChildChunk", "Proposition",
    "Department", "CentreOfExcellence", "BoardOfGovernors", "ExecutiveRole",
    "Person", "Award", "SponsorAgency", "Grant", "Equipment",
    "Patent", "Technology", "IndustryPartner", "FinancialStream",
    "Incubator", "Startup", "Investor", "Milestone",
    "AcademicProgram", "ForeignUniversity", "Student", "Fellowship",
    "MoU", "ResearchArea", "CorporateEntity", "EndowmentFund",
    "FinancialStatement", "RevenueStream", "ExpenseCategory",
    "Scholarship", "AuditFirm", "Facility", "Entity"
]

# 50+ Structured Cypher Relationships across 10 Modules
RELATIONSHIP_TYPES = [
    # 1. Document Hierarchy & Vector Chunking Module
    "PUBLISHED", "HAS_SECTION", "HAS_SUBSECTION", "HAS_CHUNK", "CONTAINS_TABLE", "MENTIONS",
    "HAS_CHILD", "SUPPORTS", "BELONGS_TO",

    # 2. Governance, Administrative & Organizational Structure
    "HAS_DEPARTMENT", "OPERATES_CENTRE", "GOVERNED_BY", "SERVES_ON", "HOLDS_ROLE",
    # 3. Faculty, Researchers & Human Capital
    "EMPLOYEES_FACULTY", "AFFILIATED_WITH", "SUPERVISES", "AWARDED_HONOR",
    # 4. Research Grants & Sponsored Projects
    "SECURED_GRANT", "FUNDED_GRANT", "PRINCIPAL_INVESTIGATOR", "CO_INVESTIGATOR", "HOSTS_PROJECT", "FUNDED_EQUIPMENT",
    # 5. Patents, Intellectual Property & Tech Transfer
    "FILED_PATENT", "GRANTED_PATENT", "INVENTED", "LICENSED_TECHNOLOGY", "LICENSED_TO", "EARNED_ROYALTY",
    # 6. Entrepreneurship, Incubation & Spin-off Startups
    "OPERATES_INCUBATOR", "INCUBATED", "FOUNDED", "ORIGINATED_FROM", "INVESTED_IN", "ACHIEVED_MILESTONE",
    # 7. Academic Programs, Degrees & Fellowships
    "OFFERS_PROGRAM", "ADMINISTERS_DEGREE", "PARTNERED_WITH", "ENROLLED_IN", "AWARDED_FELLOWSHIP",
    # 8. Global Alliances, Partnerships & MoUs
    "COLLABORATED_WITH", "ENTERED_MOU", "FOCUSES_ON", "PARTNERED_INDUSTRY",
    # 9. Financial Statements, Endowments & Budgets
    "MANAGES_ENDOWMENT", "CONTAINS_FINANCIAL_STATEMENT", "REPORTS_REVENUE", "REPORTS_EXPENSE", "ALLOCATED_TO", "AUDITED",
    # 10. Facilities, Infrastructure & Shared Resources
    "HOUSES_EQUIPMENT", "UTILIZES_FACILITY"
]

# Idempotent Uniqueness Constraints
CONSTRAINT_CYPHER_STATEMENTS = [
    "CREATE CONSTRAINT institution_name_unique IF NOT EXISTS FOR (n:Institution) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE",
    "CREATE CONSTRAINT parent_chunk_id_unique IF NOT EXISTS FOR (p:ParentChunk) REQUIRE p.chunk_id IS UNIQUE",
    "CREATE CONSTRAINT prop_id_unique IF NOT EXISTS FOR (pr:Proposition) REQUIRE pr.proposition_id IS UNIQUE",
    "CREATE CONSTRAINT grant_id_unique IF NOT EXISTS FOR (g:Grant) REQUIRE g.grant_id IS UNIQUE",
    "CREATE CONSTRAINT patent_id_unique IF NOT EXISTS FOR (p:Patent) REQUIRE p.patent_id IS UNIQUE",
    "CREATE CONSTRAINT table_id_unique IF NOT EXISTS FOR (t:Table) REQUIRE t.table_id IS UNIQUE",
    "CREATE CONSTRAINT student_id_unique IF NOT EXISTS FOR (s:Student) REQUIRE s.student_id IS UNIQUE",
    "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
]

# High-Selectivity Property Indices
INDEX_CYPHER_STATEMENTS = [
    # Generic & Chunk Indexes
    "CREATE INDEX chunk_doc_idx IF NOT EXISTS FOR (c:Chunk) ON (c.document_id)",
    "CREATE INDEX parent_chunk_doc_idx IF NOT EXISTS FOR (p:ParentChunk) ON (p.document_id)",
    "CREATE INDEX generic_doc_idx IF NOT EXISTS FOR (n:Entity) ON (n.document_id)",

    # Institution & Document Structure
    "CREATE INDEX annual_report_fy_idx IF NOT EXISTS FOR (n:AnnualReport) ON (n.fiscal_year)",
    "CREATE INDEX section_type_idx IF NOT EXISTS FOR (n:Section) ON (n.type)",

    # Organization & Governance
    "CREATE INDEX department_name_idx IF NOT EXISTS FOR (n:Department) ON (n.name)",
    "CREATE INDEX centre_name_idx IF NOT EXISTS FOR (n:CentreOfExcellence) ON (n.name)",
    "CREATE INDEX person_name_idx IF NOT EXISTS FOR (n:Person) ON (n.name)",
    "CREATE INDEX role_title_idx IF NOT EXISTS FOR (n:ExecutiveRole) ON (n.title)",

    # R&D, Grants & IP
    "CREATE INDEX sponsor_name_idx IF NOT EXISTS FOR (n:SponsorAgency) ON (n.name)",
    "CREATE INDEX technology_name_idx IF NOT EXISTS FOR (n:Technology) ON (n.name)",

    # Startups, Incubation & Industry
    "CREATE INDEX startup_name_idx IF NOT EXISTS FOR (n:Startup) ON (n.name)",
    "CREATE INDEX incubator_name_idx IF NOT EXISTS FOR (n:Incubator) ON (n.name)",
    "CREATE INDEX industry_partner_idx IF NOT EXISTS FOR (n:IndustryPartner) ON (n.name)",

    # Academics, MoU, Finance & Infrastructure
    "CREATE INDEX program_name_idx IF NOT EXISTS FOR (n:AcademicProgram) ON (n.name)",
    "CREATE INDEX mou_title_idx IF NOT EXISTS FOR (n:MoU) ON (n.title)",
    "CREATE INDEX research_area_idx IF NOT EXISTS FOR (n:ResearchArea) ON (n.name)",
    "CREATE INDEX endowment_name_idx IF NOT EXISTS FOR (n:EndowmentFund) ON (n.name)",
    "CREATE INDEX fin_stmt_fy_idx IF NOT EXISTS FOR (n:FinancialStatement) ON (n.fiscal_year)",
    "CREATE INDEX equipment_name_idx IF NOT EXISTS FOR (n:Equipment) ON (n.name)",
    "CREATE INDEX facility_name_idx IF NOT EXISTS FOR (n:Facility) ON (n.name)",
]


def ensure_basic_indexes(db: Neo4jDatabase) -> List[Dict[str, Any]]:
    """
    Applies the full Neo4j constraint and index schema safely using IF NOT EXISTS.
    """
    results = []
    # 1. Apply Uniqueness Constraints
    for stmt in CONSTRAINT_CYPHER_STATEMENTS:
        res = db.run_cypher(stmt.strip())
        results.append({"type": "constraint", "statement": stmt.strip(), "result": res})

    # 2. Apply Performance Indices
    for stmt in INDEX_CYPHER_STATEMENTS:
        res = db.run_cypher(stmt.strip())
        results.append({"type": "index", "statement": stmt.strip(), "result": res})

    return results
