# Mitigating Cypher Injection Vulnerabilities in GraphRAG

## Threat Model & Attack Surface
Exposing a database interface to automated language model generation introduces significant security vulnerabilities. Malicious user inputs or adversarial prompt injections can attempt to:
1. **Mutate Database State**: Inject write/delete clauses (e.g., `MATCH (n) DETACH DELETE n`, `DROP CONSTRAINT`, `CREATE (n:Backdoor)`).
2. **Exfiltrate Metadata**: Execute administrative system calls (e.g., `CALL dbms.security.listUsers()`, `CALL apoc.export.*`).
3. **Trigger Denial-of-Service**: Execute unbounded Cartesian joins (`MATCH (a), (b), (c) ...`).

---

## Three-Tier Defense-in-Depth Architecture

```
┌────────────────────────────────────────────────────────┐
│ 1. Role-Based Access Control (RBAC) Driver Level       │
│    - Session configured with default_access_mode=READ  │
│    - Restricts driver credentials to read-only role    │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ 2. Static AST & Lexer Analysis (Pre-Execution Gate)    │
│    - Tokenizes Cypher grammar into clause AST          │
│    - Blocks mutating tokens & administrative calls     │
│    - Strips malicious comments & multiline injections  │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ 3. Query Parameterization Engine                       │
│    - Converts inline literal constants to $param maps  │
│    - Eliminates raw string interpolation               │
└────────────────────────────────────────────────────────┘
```

---

## 1. Role-Based Access Control (RBAC)
The Neo4j database driver connects using credentials restricted to read-only access (e.g. `reader` role in Neo4j enterprise / community read-only sessions), ensuring that any accidental or injected write operation fails directly at the database engine level:
```python
with driver.session(database="neo4j", default_access_mode="READ") as session:
    result = session.run(query, parameters)
```

---

## 2. Static AST Analysis & Lexer Verification
Before any generated Cypher query reaches the database driver, it is parsed by a lexical AST analyzer that enforces:
- **Zero Modifying Operations**: Complete rejection of `CREATE`, `MERGE`, `SET`, `DELETE`, `REMOVE`, `DETACH`, `DROP`, `ALTER`, `GRANT`, `REVOKE`.
- **Administrative Procedure Blacklist**: Blocks `CALL dbms.*`, `CALL apoc.create.*`, `CALL apoc.refactor.*`, `CALL apoc.export.*`.
- **Read-Only Whitelist**: The statement must strictly consist of `MATCH`, `OPTIONAL MATCH`, `WITH`, `WHERE`, `UNWIND`, `RETURN`, `ORDER BY`, `LIMIT`, and safe schema inspection procedures (`CALL db.labels()`).
- **Comment Injection Neutralization**: Strip inline comments (`//`, `/* */`) that attackers use to bypass trailing validation logic.

---

## 3. Query Parameterization Pattern
When extracting specific entity names, keywords, or numeric filters, values are extracted as discrete parameters and passed via the Cypher parameter map (`$param`) rather than concatenated directly into the query string:

### Insecure String Concatenation (Vulnerable):
```cypher
MATCH (p:Person)-[:PRINCIPAL_INVESTIGATOR]->(g:Grant)
WHERE toLower(p.name) CONTAINS " + user_input + "
RETURN p, g
```

### Parameterized Execution (Secure):
```cypher
MATCH (p:Person)-[:PRINCIPAL_INVESTIGATOR]->(g:Grant)
WHERE toLower(p.name) CONTAINS toLower($person_name)
RETURN p, g
```
Parameters: `{"person_name": "Panigrahi"}`
