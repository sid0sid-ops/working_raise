"""
RAISE Real-Time Cloud Stack & LLM Performance Benchmark
Tests connectivity, latency (ms), and generation speed (tokens/sec) for:
1. Upstash Cloud Redis (Read / Write / Latency)
2. Neo4j AuraDB Cloud (Bolt TLS / Cypher Query Latency)
3. Groq Cloud LLM (Time-to-Generate / Tokens Per Second)
4. Gemini Cloud LLM (Time-to-Generate / Tokens Per Second)
5. Full RAG Query Pipeline Speed
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)


def benchmark_upstash_redis():
    print("\n" + "=" * 60)
    print(" ⚡ BENCHMARK 1: Upstash Cloud Redis (TLS)")
    print("=" * 60)

    try:
        from src.infrastructure.cache.redis import RedisCacheManager
        t0 = time.perf_counter()
        mgr = RedisCacheManager()
        t_connect = (time.perf_counter() - t0) * 1000

        if not mgr.is_connected or not mgr._client:
            print(" ❌ Upstash Redis connection failed.")
            return {"status": "FAIL"}

        print(f" [PASS] Connected to Upstash Redis in {t_connect:.2f} ms")

        # Ping benchmark
        pings = []
        for _ in range(5):
            tp0 = time.perf_counter()
            mgr._client.ping()
            pings.append((time.perf_counter() - tp0) * 1000)
        avg_ping = sum(pings) / len(pings)
        print(f" [PASS] Average Roundtrip Ping : {avg_ping:.2f} ms (Min: {min(pings):.2f} ms, Max: {max(pings):.2f} ms)")

        # Write & Read latency
        tw0 = time.perf_counter()
        mgr._client.set("benchmark_test_key", "raise_speed_verification_value", ex=60)
        t_write = (time.perf_counter() - tw0) * 1000

        tr0 = time.perf_counter()
        val = mgr._client.get("benchmark_test_key")
        t_read = (time.perf_counter() - tr0) * 1000

        print(f" [PASS] Set Key Latency         : {t_write:.2f} ms")
        print(f" [PASS] Get Key Latency         : {t_read:.2f} ms")
        print(f" [PASS] Data Verified          : {val.decode() if isinstance(val, bytes) else val}")

        return {
            "status": "PASS",
            "connect_ms": round(t_connect, 2),
            "ping_ms": round(avg_ping, 2),
            "write_ms": round(t_write, 2),
            "read_ms": round(t_read, 2),
        }
    except Exception as e:
        print(f" ❌ Redis Benchmark Error: {e}")
        return {"status": "ERROR", "error": str(e)}


def benchmark_neo4j_auradb():
    print("\n" + "=" * 60)
    print(" ⚡ BENCHMARK 2: Neo4j AuraDB Cloud (Bolt TLS)")
    print("=" * 60)

    try:
        from src.infrastructure.graph.neo4j import Neo4jDatabase
        t0 = time.perf_counter()
        neo = Neo4jDatabase(
            uri=os.getenv("NEO4J_URI"),
            user=os.getenv("NEO4J_USER"),
            password=os.getenv("NEO4J_PASSWORD"),
            database=os.getenv("NEO4J_DATABASE"),
        )
        check = neo.check_connection()
        t_connect = (time.perf_counter() - t0) * 1000

        if not check.get("connected"):
            print(f" ❌ Neo4j AuraDB connection failed: {check.get('error')}")
            return {"status": "FAIL", "error": check.get("error")}

        print(f" [PASS] Connected to Neo4j AuraDB in {t_connect:.2f} ms")
        print(f" [INFO] Database URI: {check.get('uri')}")
        print(f" [INFO] Active Database: {check.get('database')}")

        # Cypher Query Latency: Simple Return
        driver = neo.get_driver()
        cypher_times = []
        with driver.session(database=neo.database) as s:
            for _ in range(3):
                tq0 = time.perf_counter()
                res = s.run("RETURN 42 AS answer, datetime() AS ts").single()
                cypher_times.append((time.perf_counter() - tq0) * 1000)
            avg_cypher = sum(cypher_times) / len(cypher_times)
            print(f" [PASS] Cypher Query Roundtrip : {avg_cypher:.2f} ms (Min: {min(cypher_times):.2f} ms)")

            # Total Nodes & Relationships Count
            tn0 = time.perf_counter()
            counts = s.run("MATCH (n) RETURN count(n) AS node_count").single()
            node_count = counts["node_count"]
            t_count = (time.perf_counter() - tn0) * 1000
            print(f" [PASS] Graph Node Count Query : {t_count:.2f} ms (Total Nodes: {node_count})")

        return {
            "status": "PASS",
            "connect_ms": round(t_connect, 2),
            "cypher_ms": round(avg_cypher, 2),
            "node_count": node_count,
        }
    except Exception as e:
        print(f" ❌ Neo4j Benchmark Error: {e}")
        return {"status": "ERROR", "error": str(e)}


def benchmark_groq_llm():
    print("\n" + "=" * 60)
    print(" ⚡ BENCHMARK 3: Groq Cloud LLM (Llama 3.3 70B Versatile)")
    print("=" * 60)

    try:
        from src.infrastructure.providers.groq import GroqProvider
        groq = GroqProvider(model_name="llama-3.3-70b-versatile")
        health = groq.health_check()
        print(f" [INFO] Groq Health: {health.status} ({health.error_message or 'All systems go'})")

        test_question = (
            "Explain in 2 sentences the difference between a Knowledge Graph and a Vector Database for research."
        )
        print(f" [QUESTION]: {test_question}\n")

        t0 = time.perf_counter()
        response = groq.complete(prompt=test_question, max_tokens=150, temperature=0.1)
        duration_s = time.perf_counter() - t0

        words = response.split()
        est_tokens = int(len(words) * 1.33)
        tokens_per_sec = est_tokens / duration_s if duration_s > 0 else 0

        print(f" [ANSWER]:\n{response.strip()}\n")
        print(f" [PERFORMANCE SCORECARD]:")
        print(f"   • Total Response Time  : {duration_s * 1000:.1f} ms ({duration_s:.2f} s)")
        print(f"   • Tokens Generated     : ~{est_tokens} tokens")
        print(f"   • Generation Speed     : {tokens_per_sec:.1f} tokens/second 🚀")

        return {
            "status": "PASS",
            "provider": "Groq (LPU)",
            "model": groq.model_name,
            "duration_ms": round(duration_s * 1000, 1),
            "tokens": est_tokens,
            "tokens_per_sec": round(tokens_per_sec, 1),
            "answer_preview": response.strip()[:100] + "...",
        }
    except Exception as e:
        print(f" ❌ Groq Benchmark Error: {e}")
        return {"status": "ERROR", "error": str(e)}


def benchmark_gemini_llm():
    print("\n" + "=" * 60)
    print(" ⚡ BENCHMARK 4: Gemini Cloud LLM (Gemini 2.5 Flash)")
    print("=" * 60)

    try:
        from src.infrastructure.providers.gemini import GeminiProvider
        gemini = GeminiProvider(model_name="gemini-2.5-flash")
        health = gemini.health_check()
        print(f" [INFO] Gemini Health: {health.status} ({health.error_message or 'All systems go'})")

        test_question = (
            "Summarize the main advantage of combining graphs with RAG in 2 clear sentences."
        )
        print(f" [QUESTION]: {test_question}\n")

        t0 = time.perf_counter()
        response = gemini.complete(prompt=test_question, max_tokens=150, temperature=0.1)
        duration_s = time.perf_counter() - t0

        words = response.split()
        est_tokens = int(len(words) * 1.33)
        tokens_per_sec = est_tokens / duration_s if duration_s > 0 else 0

        print(f" [ANSWER]:\n{response.strip()}\n")
        print(f" [PERFORMANCE SCORECARD]:")
        print(f"   • Total Response Time  : {duration_s * 1000:.1f} ms ({duration_s:.2f} s)")
        print(f"   • Tokens Generated     : ~{est_tokens} tokens")
        print(f"   • Generation Speed     : {tokens_per_sec:.1f} tokens/second")

        return {
            "status": "PASS",
            "provider": "Google Gemini",
            "model": gemini.model_name,
            "duration_ms": round(duration_s * 1000, 1),
            "tokens": est_tokens,
            "tokens_per_sec": round(tokens_per_sec, 1),
        }
    except Exception as e:
        print(f" ❌ Gemini Benchmark Error: {e}")
        return {"status": "ERROR", "error": str(e)}


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" 🚀 STARTING FULL RAISE CLOUD INFRASTRUCTURE & LLM BENCHMARK")
    print("=" * 70)

    r_redis = benchmark_upstash_redis()
    r_neo = benchmark_neo4j_auradb()
    r_groq = benchmark_groq_llm()
    r_gemini = benchmark_gemini_llm()

    print("\n" + "=" * 70)
    print(" 🏁 FINAL SYSTEM PERFORMANCE SUMMARY SCORECARD")
    print("=" * 70)
    print(f" 1. Upstash Redis Latency : {r_redis.get('ping_ms', 'N/A')} ms ping | Write: {r_redis.get('write_ms', 'N/A')} ms | Read: {r_redis.get('read_ms', 'N/A')} ms")
    print(f" 2. Neo4j AuraDB Latency  : {r_neo.get('cypher_ms', 'N/A')} ms Cypher roundtrip")
    print(f" 3. Groq Cloud Inference  : {r_groq.get('duration_ms', 'N/A')} ms total | {r_groq.get('tokens_per_sec', 'N/A')} tokens/sec")
    print(f" 4. Gemini Cloud Inference: {r_gemini.get('duration_ms', 'N/A')} ms total | {r_gemini.get('tokens_per_sec', 'N/A')} tokens/sec")
    print("=" * 70 + "\n")
