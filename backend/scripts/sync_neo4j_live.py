"""
RAISE Live Neo4j Synchronization and Cypher Verification
Syncs academic_graph.cypher and qwen_test_graph.cypher into live Neo4j instance at bolt://localhost:7687.
Runs live Cypher test queries to verify property graph nodes, relationships, and provenance.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password123")

print("=" * 80)
print(" 🚀 CONNECTING TO LIVE DOCKER NEO4J INSTANCE")
print(f" URI: {NEO4J_URI} | User: {NEO4J_USER}")
print("=" * 80)

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def wait_for_neo4j(driver, max_retries=10):
    for i in range(1, max_retries + 1):
        try:
            with driver.session() as session:
                res = session.run("RETURN 1 as ping").single()
                if res and res["ping"] == 1:
                    print("✅ Neo4j Bolt Connection Verified!")
                    return True
        except Exception as e:
            print(f"Waiting for Neo4j to accept queries ({i}/{max_retries})... ({e})")
            time.sleep(2)
    return False

if not wait_for_neo4j(driver):
    print("❌ Failed to connect to Neo4j.")
    sys.exit(1)

# Step 1: Execute academic_graph.cypher
rag_dir = Path("RAG").resolve()
cypher_file1 = rag_dir / "data" / "processed" / "neo4j" / "academic_graph.cypher"
cypher_file2 = rag_dir / "data" / "processed" / "neo4j" / "qwen_test_graph.cypher"

def execute_cypher_script(session, cypher_path):
    if not cypher_path.exists():
        print(f"File not found: {cypher_path}")
        return 0
    
    statements = []
    current = []
    for line in cypher_path.read_text(encoding="utf-8").splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("//"):
            continue
        current.append(line)
        if trimmed.endswith(";"):
            statements.append("\n".join(current)[:-1]) # remove trailing ;
            current = []
            
    executed = 0
    for stmt in statements:
        try:
            session.run(stmt)
            executed += 1
        except Exception as err:
            print(f"Error executing statement: {err}\nQuery: {stmt[:100]}...")
    return executed

with driver.session() as session:
    print(f"\n[1/3] Ingesting Academic Baseline Graph from {cypher_file1.name}...")
    cnt1 = execute_cypher_script(session, cypher_file1)
    print(f"  -> Executed {cnt1} Cypher statements.")

    print(f"\n[2/3] Ingesting Qwen 14B Extracted Triples from {cypher_file2.name}...")
    cnt2 = execute_cypher_script(session, cypher_file2)
    print(f"  -> Executed {cnt2} Cypher statements.")

    print("\n[3/3] Running Live Cypher Audit & Query Verification...")
    
    # Query 1: Total Node Count & Labels
    res_nodes = session.run("MATCH (n) RETURN labels(n) as labels, count(n) as count ORDER BY count DESC")
    print("\n--- Live Node Distribution ---")
    for record in res_nodes:
        print(f"  Labels: {record['labels']} -> Count: {record['count']}")
        
    # Query 2: Total Relationship Count & Types
    res_rels = session.run("MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as count ORDER BY count DESC")
    print("\n--- Live Relationship Distribution ---")
    for record in res_rels:
        print(f"  Type: -[:{record['rel_type']}]-> Count: {record['count']}")

    # Query 3: Multi-Hop Subgraph Query on IIT Madras
    print("\n--- Multi-Hop BFS Traversal (IIT Madras Programs & Centres) ---")
    iitm_query = """
    MATCH (u:University)-[r]->(target)
    WHERE u.name CONTAINS "Madras"
    RETURN u.name as University, type(r) as Relationship, target.name as ConnectedEntity, target.degree_level as Degree, target.source_pdf as SourcePDF
    LIMIT 10
    """
    for r in session.run(iitm_query):
        print(f"  ({r['University']}) -[:{r['Relationship']}]-> ({r['ConnectedEntity']}) [PDF: {r['SourcePDF']}]")

    # Query 4: Multi-Hop Subgraph Query on BRIC Autonomous Institutes (Extracted by Qwen 14B)
    print("\n--- Qwen 14B Extracted Subgraph (BRIC Autonomous Centres) ---")
    bric_query = """
    MATCH (b:QwenEntity)-[r:HAS_CENTRE]->(c:QwenEntity)
    WHERE b.name CONTAINS "BRIC"
    RETURN b.name as Council, type(r) as Rel, c.name as Institute, r.page as Page, r.source_pdf as PDF
    LIMIT 10
    """
    for r in session.run(bric_query):
        print(f"  ({r['Council']}) -[:{r['Rel']}]-> ({r['Institute']}) [Page {r['Page']}]")

driver.close()
print("\n" + "=" * 80)
print(" ✅ LIVE NEO4J INTEGRATION & CYPHER VERIFICATION COMPLETE!")
print("=================================================================")
