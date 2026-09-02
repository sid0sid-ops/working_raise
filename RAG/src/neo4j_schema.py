"""
Comprehensive Neo4j Schema Definition and Indexing Helper for RAISE Academic GraphRAG.
Defines all 35+ Node Labels, Properties, 50 Relationship Types, and automatically
applies performance-optimized Neo4j indexes and constraints.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Any

if TYPE_CHECKING:
    from .neo4j_engine import Neo4jDatabase

# Comprehensive Schema Node Labels
NODE_LABELS = [
    "Institution", "AnnualReport", "Section", "Chunk", "Table",
    "Department", "CentreOfExcellence", "BoardOfGovernors", "ExecutiveRole",
    "Person", "Award", "SponsorAgency", "Grant", "Equipment",
    "Patent", "Technology", "IndustryPartner", "FinancialStream",
    "Incubator", "Startup", "Investor", "Milestone",
    "AcademicProgram", "ForeignUniversity", "Student", "Fellowship",
    "MoU", "ResearchArea", "CorporateEntity", "EndowmentFund",
    "FinancialStatement", "RevenueStream", "ExpenseCategory",
    "Scholarship", "AuditFirm", "Facility"
]

# 50 Structured Cypher Relationships
RELATIONSHIP_TYPES = [
    # 1. Document Hierarchy & Vector Chunking Module
    "PUBLISHED", "HAS_SECTION", "HAS_SUBSECTION", "HAS_CHUNK", "CONTAINS_TABLE", "MENTIONS",
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

INDEX_CYPHER_STATEMENTS = [
    # Generic & Chunk Indexes
    "CREATE INDEX chunk_id_idx IF NOT EXISTS FOR (c:Chunk) ON (c.chunk_id)",
    "CREATE INDEX chunk_doc_idx IF NOT EXISTS FOR (c:Chunk) ON (c.document_id)",
    "CREATE INDEX table_id_idx IF NOT EXISTS FOR (t:Table) ON (t.table_id)",
    "CREATE INDEX entity_id_idx IF NOT EXISTS FOR (e:Entity) ON (e.id)",
    "CREATE INDEX generic_doc_idx IF NOT EXISTS FOR (n:Entity) ON (n.document_id)",

    # Institution & Document Structure
    "CREATE INDEX institution_name_idx IF NOT EXISTS FOR (n:Institution) ON (n.name)",
    "CREATE INDEX annual_report_fy_idx IF NOT EXISTS FOR (n:AnnualReport) ON (n.fiscal_year)",
    "CREATE INDEX section_type_idx IF NOT EXISTS FOR (n:Section) ON (n.type)",

    # Organization & Governance
    "CREATE INDEX department_name_idx IF NOT EXISTS FOR (n:Department) ON (n.name)",
    "CREATE INDEX centre_name_idx IF NOT EXISTS FOR (n:CentreOfExcellence) ON (n.name)",
    "CREATE INDEX person_name_idx IF NOT EXISTS FOR (n:Person) ON (n.name)",
    "CREATE INDEX role_title_idx IF NOT EXISTS FOR (n:ExecutiveRole) ON (n.title)",

    # R&D, Grants & IP
    "CREATE INDEX sponsor_name_idx IF NOT EXISTS FOR (n:SponsorAgency) ON (n.name)",
    "CREATE INDEX grant_id_idx IF NOT EXISTS FOR (n:Grant) ON (n.grant_id)",
    "CREATE INDEX patent_id_idx IF NOT EXISTS FOR (n:Patent) ON (n.patent_id)",
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
    Applies the full Neo4j index schema safely using IF NOT EXISTS.
    """
    results = []
    for stmt in INDEX_CYPHER_STATEMENTS:
        res = db.run_cypher(stmt.strip())
        results.append({"statement": stmt.strip(), "result": res})
    return results
