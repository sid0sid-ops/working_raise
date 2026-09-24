"""
Graph Retrieval & Cypher Query Generation Prompt with Complete Graph Schema Definition
"""

RETRIEVAL_QA_CHAT_PROMPT = """Task: Translate the user's natural language question into a syntactically correct, schema-compliant Cypher query to retrieve information from a Graph Database built from institutional annual reports.

==================================================
GRAPH SCHEMA DEFINITION
==================================================

1. NODE LABELS & PROPERTIES:

   - Institution: 
       • name: String (e.g., "IIT Madras", "BRIC", "Harvard University", "NUS", "IIT (ISM) Dhanbad")
       • type: String (e.g., "University", "Research Council", "Foundation")
       • location: String

   - AnnualReport: 
       • fiscal_year: String (e.g., "2024-25", "2025", "2016-17")
       • title: String

   - Section: 
       • parent_institution: String
       • type: String (Allowed values: 
           "Executive Summary", 
           "Financial Statements & Budgets", 
           "Sponsored Research Projects & Grants", 
           "Patents & Intellectual Property", 
           "Startups & Incubation", 
           "Academic Programs & Degrees", 
           "Governance & Strategic Initiatives", 
           "Global Partnerships & MoUs", 
           "Endowments & Investments", 
           "Facilities & Infrastructure",
           "Audit & Compliance Reports")

   - Chunk: 
       • chunk_id: String
       • text: String
       • page_number: Integer

   - Table: 
       • table_id: String
       • caption: String
       • headers: List of Strings

   - Department: 
       • name: String (e.g., "Department of Computer Science", "Department of Chemistry")

   - CentreOfExcellence: 
       • name: String (e.g., "Hydrogen Valley Innovation Hub", "S Ramakrishnan Centre")

   - BoardOfGovernors: 
       • name: String

   - ExecutiveRole: 
       • title: String (e.g., "Director", "Vice-Chancellor", "Dean", "Treasurer")

   - Person: 
       • name: String (e.g., "Dr. Sushanta Kumar Panigrahi", "Dr. Karthik Raman")
       • designation: String (e.g., "Professor", "Principal Investigator", "Director General")

   - Award: 
       • title: String
       • year: String

   - SponsorAgency: 
       • name: String (e.g., "DST", "DBT", "MeitY", "Hyundai Motor", "Gates Foundation")
       • type: String (e.g., "Government", "Industry", "Foundation")

   - Grant: 
       • title: String
       • grant_id: String
       • sponsor_agency: String
       • amount_inr_lakh: Float

   - Equipment: 
       • name: String (e.g., "Cryo-EM", "ESR", "XPS-UPS", "AFM")
       • cost: Float

   - Patent: 
       • title: String
       • patent_id: String
       • status: String (Allowed values: "Filed", "Granted")
       • filing_year: String

   - Technology: 
       • name: String (e.g., "ADVIKA", "SAATVIK", "IndRA 90K Array", "TMAP")

   - IndustryPartner: 
       • name: String (e.g., "Cirkla Technologies", "Optum Technology", "Pfizer")

   - FinancialStream: 
       • type: String
       • amount: Float

   - Incubator: 
       • name: String (e.g., "IITM Incubation Cell", "Bio-Incubator Hub")

   - Startup: 
       • name: String (e.g., "Ather Energy", "The ePlane Company", "Mindgrove", "Xyma Analytics", "VinMax Biotech")
       • valuation: String
       • sector: String (e.g., "Deep-Tech", "Healthcare", "E-Mobility")

   - Investor: 
       • name: String

   - Milestone: 
       • description: String (e.g., "IPO Listing", "DGCA Certification", "Test Tapeout")

   - AcademicProgram: 
       • name: String (e.g., "BS in Data Science", "Web MTech in E-Mobility", "Joint MSc in Sustainable Energy Systems")
       • degree_level: String (e.g., "UG", "PG", "PhD", "Dual Degree")

   - ForeignUniversity: 
       • name: String (e.g., "University of Birmingham", "RWTH Aachen", "TU Dresden", "Arizona State University")
       • country: String

   - Student: 
       • student_id: String

   - Fellowship: 
       • name: String (e.g., "Bioentrepreneur-in-Residence (EIR)", "Pre-Doctoral Fellowship")

   - MoU: 
       • title: String
       • date_signed: String

   - ResearchArea: 
       • name: String (e.g., "Quantum Engineering", "Clean Energy", "Robotics", "E-Mobility")

   - CorporateEntity: 
       • name: String (e.g., "HSBC", "Hyundai Hope on Wheels Foundation", "Karkinos Healthcare")

   - EndowmentFund: 
       • name: String
       • corpus_value: Float

   - FinancialStatement: 
       • type: String (Allowed values: "Balance Sheet", "Income & Expenditure", "Cash Flow")
       • fiscal_year: String

   - RevenueStream: 
       • source: String (e.g., "Sponsored Research", "Consultancy", "Tuition", "Govt Grants")
       • amount: Float

   - ExpenseCategory: 
       • category: String (e.g., "Salaries", "Equipment Maintenance", "Infrastructure")
       • amount: Float

   - Scholarship: 
       • name: String

   - AuditFirm: 
       • name: String

   - Facility: 
       • name: String

2. RELATIONSHIP TYPES:

   [Document Hierarchy & Chunking]
   - (:Institution)-[:PUBLISHED]->(:AnnualReport)
   - (:AnnualReport)-[:HAS_SECTION]->(:Section)
   - (:Section)-[:HAS_SUBSECTION]->(:Section)
   - (:Section)-[:HAS_CHUNK]->(:Chunk)
   - (:Chunk)-[:CONTAINS_TABLE]->(:Table)
   - (:Section)-[:MENTIONS]->(:Patent | :Startup | :Grant | :Person | :Facility)

   [Governance & Organizational Structure]
   - (:Institution)-[:HAS_DEPARTMENT]->(:Department)
   - (:Institution)-[:OPERATES_CENTRE]->(:CentreOfExcellence)
   - (:Institution)-[:GOVERNED_BY]->(:BoardOfGovernors)
   - (:Person)-[:SERVES_ON]->(:BoardOfGovernors)
   - (:Person)-[:HOLDS_ROLE]->(:ExecutiveRole)

   [Faculty & Personnel]
   - (:Institution)-[:EMPLOYEES_FACULTY]->(:Person)
   - (:Department)-[:AFFILIATED_WITH]->(:Person)
   - (:Person)-[:SUPERVISES]->(:Person)
   - (:Person)-[:AWARDED_HONOR]->(:Award)

   [Grants & Sponsored Research]
   - (:Institution)-[:SECURED_GRANT]->(:Grant)
   - (:SponsorAgency)-[:FUNDED_GRANT]->(:Grant)
   - (:Person)-[:PRINCIPAL_INVESTIGATOR]->(:Grant)
   - (:Person)-[:CO_INVESTIGATOR]->(:Grant)
   - (:Department)-[:HOSTS_PROJECT]->(:Grant)
   - (:Grant)-[:FUNDED_EQUIPMENT]->(:Equipment)

   [Patents & Tech Transfer]
   - (:Institution)-[:FILED_PATENT]->(:Patent)
   - (:Institution)-[:GRANTED_PATENT]->(:Patent)
   - (:Person)-[:INVENTED]->(:Patent)
   - (:Institution)-[:LICENSED_TECHNOLOGY]->(:Technology)
   - (:Technology)-[:LICENSED_TO]->(:IndustryPartner)
   - (:Institution)-[:EARNED_ROYALTY]->(:FinancialStream)

   [Incubation & Startups]
   - (:Institution)-[:OPERATES_INCUBATOR]->(:Incubator)
   - (:Incubator)-[:INCUBATED]->(:Startup)
   - (:Person)-[:FOUNDED]->(:Startup)
   - (:Startup)-[:ORIGINATED_FROM]->(:Technology)
   - (:Investor)-[:INVESTED_IN]->(:Startup)
   - (:Startup)-[:ACHIEVED_MILESTONE]->(:Milestone)

   [Academic Programs & Fellowships]
   - (:Institution)-[:OFFERS_PROGRAM]->(:AcademicProgram)
   - (:Department)-[:ADMINISTERS_DEGREE]->(:AcademicProgram)
   - (:AcademicProgram)-[:PARTNERED_WITH]->(:ForeignUniversity)
   - (:Student)-[:ENROLLED_IN]->(:AcademicProgram)
   - (:Person)-[:AWARDED_FELLOWSHIP]->(:Fellowship)

   [Global Partnerships & Alliances]
   - (:Institution)-[:COLLABORATED_WITH]->(:Institution)
   - (:Institution)-[:ENTERED_MOU]->(:MoU)
   - (:MoU)-[:FOCUSES_ON]->(:ResearchArea)
   - (:Institution)-[:PARTNERED_INDUSTRY]->(:CorporateEntity)

   [Financials, Endowments & Audit]
   - (:Institution)-[:MANAGES_ENDOWMENT]->(:EndowmentFund)
   - (:AnnualReport)-[:CONTAINS_FINANCIAL_STATEMENT]->(:FinancialStatement)
   - (:FinancialStatement)-[:REPORTS_REVENUE]->(:RevenueStream)
   - (:FinancialStatement)-[:REPORTS_EXPENSE]->(:ExpenseCategory)
   - (:EndowmentFund)-[:ALLOCATED_TO]->(:Scholarship)
   - (:AuditFirm)-[:AUDITED]->(:FinancialStatement)

   [Facilities & Infrastructure]
   - (:Institution)-[:HOUSES_EQUIPMENT]->(:Equipment)
   - (:Department)-[:UTILIZES_FACILITY]->(:Facility)

3. RELATIONSHIP MODULE DESCRIPTIONS:
   1. Document Hierarchy & Vector Chunking Module:
      • (:Institution)-[:PUBLISHED]->(:AnnualReport) — Links an educational/research institution to its published annual report.
      • (:AnnualReport)-[:HAS_SECTION]->(:Section) — Connects an annual report to its primary thematic sections (e.g., Financial Statements, Research & Development, Incubation).
      • (:Section)-[:HAS_SUBSECTION]->(:Section) — Captures nested sub-sections within complex report chapters.
      • (:Section)-[:HAS_CHUNK]->(:Chunk) — Connects a section to indexed text passages or vector embeddings for semantic search.
      • (:Chunk)-[:CONTAINS_TABLE]->(:Table) — Connects a text chunk to extracted structured tabular data.
      • (:Section)-[:MENTIONS]->(:Patent | :Startup | :Grant | :Person | :Facility) — Represents direct semantic entity extractions from section text.

   2. Governance, Administrative & Organizational Structure:
      • (:Institution)-[:HAS_DEPARTMENT]->(:Department) — Links an institution to its academic departments, schools, or faculties.
      • (:Institution)-[:OPERATES_CENTRE]->(:CentreOfExcellence) — Connects an institution to specialized interdisciplinary research centers or centers of excellence.
      • (:Institution)-[:GOVERNED_BY]->(:BoardOfGovernors) — Links an institution to its governing board, board of trustees, or syndicate.
      • (:Person)-[:SERVES_ON]->(:BoardOfGovernors) — Connects executive personnel, external advisors, or trustees to institutional boards.
      • (:Person)-[:HOLDS_ROLE]->(:ExecutiveRole) — Associates personnel with administrative positions (e.g., Director, Vice-Chancellor, Dean, Treasurer).

   3. Faculty, Researchers & Human Capital:
      • (:Institution)-[:EMPLOYEES_FACULTY]->(:Person) — Links professors, scientists, and principal investigators to their employing institution.
      • (:Department)-[:AFFILIATED_WITH]->(:Person) — Maps researchers and faculty members to their primary or joint department.
      • (:Person)-[:SUPERVISES]->(:Person) — Captures thesis advisorship and mentorship between PIs and PhD candidates/Postdocs.
      • (:Person)-[:AWARDED_HONOR]->(:Award) — Links faculty members or researchers to academic, national, or international honors received during the reporting year.

   4. Research Grants & Sponsored Projects:
      • (:Institution)-[:SECURED_GRANT]->(:Grant) — Links an institution to external sponsored research projects and research grants.
      • (:SponsorAgency)-[:FUNDED_GRANT]->(:Grant) — Connects government bodies or private foundations (e.g., DST, DBT, MeitY, Gates Foundation) to funded projects.
      • (:Person)-[:PRINCIPAL_INVESTIGATOR]->(:Grant) — Identifies the primary scientist or faculty member leading a funded research project.
      • (:Person)-[:CO_INVESTIGATOR]->(:Grant) — Connects co-PIs and collaborating researchers to a grant.
      • (:Department)-[:HOSTS_PROJECT]->(:Grant) — Maps a sponsored project to the department hosting its execution.
      • (:Grant)-[:FUNDED_EQUIPMENT]->(:Equipment) — Connects specific grant allocations to procured high-value scientific instruments.

   5. Patents, Intellectual Property & Tech Transfer:
      • (:Institution)-[:FILED_PATENT]->(:Patent) — Connects an institution as an applicant to patent applications filed during the fiscal year.
      • (:Institution)-[:GRANTED_PATENT]->(:Patent) — Identifies patents officially granted to an institution during the fiscal year.
      • (:Person)-[:INVENTED]->(:Patent) — Connects inventors (faculty, students, scientists) to a patent.
      • (:Institution)-[:LICENSED_TECHNOLOGY]->(:Technology) — Links an institution to patented technologies or inventions licensed out to industry.
      • (:Technology)-[:LICENSED_TO]->(:IndustryPartner) — Connects institutional IP or tech transfers to commercial industry licensees.
      • (:Institution)-[:EARNED_ROYALTY]->(:FinancialStream) — Links technology licensing actions to institutional royalty and IP revenue streams.

   6. Entrepreneurship, Incubation & Spin-off Startups:
      • (:Institution)-[:OPERATES_INCUBATOR]->(:Incubator) — Links an institution to its technology business incubator or research park (e.g., IITM Incubation Cell).
      • (:Incubator)-[:INCUBATED]->(:Startup) — Connects an incubator to deep-tech spin-off startups nurtured during the fiscal year.
      • (:Person)-[:FOUNDED]->(:Startup) — Connects faculty, alumni, or student founders to spin-off ventures.
      • (:Startup)-[:ORIGINATED_FROM]->(:Technology) — Links a deep-tech startup to the foundational core research or patent developed at the institution.
      • (:Investor)-[:INVESTED_IN]->(:Startup) — Captures seed funding, angel, or venture capital investments made in incubated startups.
      • (:Startup)-[:ACHIEVED_MILESTONE]->(:Milestone) — Tracks key startup growth events (e.g., IPO listing, regulatory certification, product launch).

   7. Academic Programs, Degrees & Fellowships:
      • (:Institution)-[:OFFERS_PROGRAM]->(:AcademicProgram) — Links an institution to degree/diploma programs (e.g., BS, MTech, Online BS, Joint PhD).
      • (:Department)-[:ADMINISTERS_DEGREE]->(:AcademicProgram) — Maps academic degree offerings to their managing departments.
      • (:AcademicProgram)-[:PARTNERED_WITH]->(:ForeignUniversity) — Links joint degree or dual-degree offerings to partner international universities.
      • (:Student)-[:ENROLLED_IN]->(:AcademicProgram) — Connects student cohorts or scholarship recipients to specific programs.
      • (:Person)-[:AWARDED_FELLOWSHIP]->(:Fellowship) — Links researchers or students to prestigious fellowships (e.g., EIR, PMRF, Post-doctoral Fellowships).

   8. Global Alliances, Partnerships & MoUs:
      • (:Institution)-[:COLLABORATED_WITH]->(:Institution) — Captures bilateral research or academic partnerships between universities and councils.
      • (:Institution)-[:ENTERED_MOU]->(:MoU) — Connects institutions to formal Memoranda of Understanding signed during the reporting period.
      • (:MoU)-[:FOCUSES_ON]->(:ResearchArea) — Connects MoUs to target fields (e.g., Quantum Computing, Clean Energy, Robotics).
      • (:Institution)-[:PARTNERED_INDUSTRY]->(:CorporateEntity) — Links universities to corporate R&D partners and CSR program sponsors.

   9. Financial Statements, Endowments & Budgets:
      • (:Institution)-[:MANAGES_ENDOWMENT]->(:EndowmentFund) — Connects an institution to its permanent endowment pool or foundation.
      • (:AnnualReport)-[:CONTAINS_FINANCIAL_STATEMENT]->(:FinancialStatement) — Links a report to detailed accounting statements (Balance Sheet, Income & Expenditure).
      • (:FinancialStatement)-[:REPORTS_REVENUE]->(:RevenueStream) — Maps income sources (e.g., Tuition, Sponsored Research, Government Appropriations, Consultancy).
      • (:FinancialStatement)-[:REPORTS_EXPENSE]->(:ExpenseCategory) — Maps expenditure categories (e.g., Salaries, Equipment Maintenance, R&D Infrastructure).
      • (:EndowmentFund)-[:ALLOCATED_TO]->(:Scholarship) — Connects endowment yields to financial aid, student living support, or endowed faculty chairs.
      • (:AuditFirm)-[:AUDITED]->(:FinancialStatement) — Links independent external auditors or state audit agencies to certified institutional accounts.

   10. Facilities, Infrastructure & Shared Resources:
      • (:Institution)-[:HOUSES_EQUIPMENT]->(:Equipment) — Connects an institution to major shared research infrastructure (e.g., Supercomputers, Cryo-EM, Cleanrooms).
      • (:Department)-[:UTILIZES_FACILITY]->(:Facility) — Links specific research groups or departments to central instrumentation facilities.

==================================================
INSTRUCTIONS & COMPLIANCE RULES
==================================================

1. STRICT SCHEMA GROUNDING & ANTI-HALLUCINATION:
   - Use ONLY the node labels, relationship types, and property keys explicitly defined in the provided schema.
   - NEVER introduce, infer, or hallucinate node labels, relationship types, or properties not listed in the schema.
   - If the user's question asks for an entity or concept not supported by the schema, fall back to matching Section or Chunk nodes that contain relevant text terms.

2. READ-ONLY SECURITY CONSTRAINTS:
   - Generate STRICTLY READ-ONLY Cypher queries using MATCH, OPTIONAL MATCH, WITH, WHERE, RETURN, ORDER BY, and LIMIT clauses.
   - ABSOLUTELY FORBIDDEN: Any mutating clauses such as CREATE, MERGE, SET, DELETE, REMOVE, DETACH DELETE, DROP, or CALL apoc.* procedures that alter data.

3. DOCUMENT HIERARCHY & SECTION-BASED SCOPING:
   - Annual reports contain diverse topics (e.g., finances, patents, faculty awards). To prevent context contamination across unrelated chapters, ALWAYS traverse through Section nodes to reach Chunk nodes when extracting free-text context.
   - Filter Section nodes by `type` when the query domain is clear (e.g., `sec.type = 'Patents & Intellectual Property'`, `sec.type = 'Sponsored Research Projects & Grants'`, `sec.type = 'Startups & Incubation'`, `sec.type = 'Financial Statements & Budgets'`).
   - If the target Section type is ambiguous or unspecified, traverse all Section nodes connected to the target AnnualReport without restricting `sec.type`.

4. ENTITY RESOLUTION, TYPO CORRECTION & FUZZY MATCHING:
   - Correct common entity typos, spelling errors, or name variants prior to matching.
   - Standardize institutional abbreviations and acronyms (e.g., "IITM" / "IIT Madras" -> "IIT Madras", "BRIC" -> "Biotechnology Research and Innovation Council", "NUS" -> "National University of Singapore").
   - Use CASE-INSENSITIVE and Partial Matching for string property comparisons using `toLower()` or regex matching. Example:
     `WHERE toLower(p.name) CONTAINS toLower("panigrahi")` or `WHERE inst.name =~ '(?i).*iit madras.*'`

5. CYPHER SYNTAX, TRAVERSAL & PERFORMANCE GUARDRAILS:
   - Respect Directed Edge Directions as defined in the schema. Do not reverse edge arrows.
   - Always use `DISTINCT` in RETURN clauses or aggregation functions (`count(DISTINCT x)`, `collect(DISTINCT y)`) to prevent returning duplicate paths.
   - Avoid unbounded variable-length path traversals (e.g., NEVER use `-[*]-`). If variable-length traversal is required, bound the depth strictly (e.g., `-[:HAS_SUBSECTION*1..3]->`).
   - Use `OPTIONAL MATCH` when joining secondary attributes or related entities so that primary records are not dropped if an optional link is missing.

6. AGGREGATION, TYPE CASTING & NULL SAFETY:
   - When performing numeric operations, comparisons, or summaries (SUM, AVG, MIN, MAX), explicitly cast properties if needed using `toFloat()`, `toInteger()`, or `date()`.
   - Handle NULL values gracefully using `coalesce()` or `IS NOT NULL` checks before arithmetic calculations.

7. OUTPUT FORMATTING & ZERO-COMMENTARY RULE:
   - Output ONLY the raw executable Cypher query.
   - Do NOT wrap the query in markdown commentary, explanations, preambles, or postscripts.
   - Return the query directly or wrapped cleanly in `<query>` tags if required by the downstream parser.
"""

retrieval_qa_chat_prompt = RETRIEVAL_QA_CHAT_PROMPT
