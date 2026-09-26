"""
PostgreSQL 16 Authoritative Evaluation Logger
Persists immutable evaluation runs, cases, retrieval traces, failures, and scorecard metrics into raise_db.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import psycopg2

logger = logging.getLogger("raise.eval.pg_logger")


class PostgresEvaluationLogger:
    """
    Connects to PostgreSQL 16 and records all evaluation telemetry into the canonical evaluation schema.
    """

    def __init__(self, host="localhost", port=5432, dbname="raise_db", user="raise_user", password="raise_password"):
        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self.password = password
        self.conn = None
        self._connect()

    def _connect(self):
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.dbname,
                user=self.user,
                password=self.password
            )
            logger.info("Connected to PostgreSQL 16 for evaluation logging.")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            self.conn = None

    def _get_cursor(self):
        if not self.conn or self.conn.closed:
            self._connect()
        return self.conn.cursor() if self.conn else None

    def register_run(
        self,
        run_id: str,
        benchmark: str,
        dataset: str,
        split: str,
        experiment_id: str,
        git_commit: str,
        config_hash: str,
        model_manifest: Dict[str, Any],
        runtime_manifest: Dict[str, Any],
        ablation_config: str = "ABL-G",
        evaluation_mode: str = "MODE_B_END_TO_END",
    ) -> bool:
        cur = self._get_cursor()
        if not cur:
            return False

        try:
            session_id = f"EVAL::{benchmark}::{run_id}"
            title = f"Evaluation Run: {benchmark} ({run_id})"

            # 1. Create native RAISE session in session_metadata
            cur.execute("""
                INSERT INTO session_metadata (id, title, attached_docs, created_at, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO NOTHING;
            """, (session_id, title, json.dumps([])))

            # 2. Register run in evaluation_runs
            cur.execute("""
                INSERT INTO evaluation_runs (
                    run_id, session_id, benchmark, dataset, split, experiment_id,
                    git_commit, config_hash, model_manifest, runtime_manifest,
                    ablation_config, evaluation_mode, status, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'RUNNING', CURRENT_TIMESTAMP)
                ON CONFLICT (run_id) DO UPDATE SET status = 'RUNNING';
            """, (
                run_id, session_id, benchmark, dataset, split, experiment_id,
                git_commit, config_hash, json.dumps(model_manifest), json.dumps(runtime_manifest),
                ablation_config, evaluation_mode
            ))
            self.conn.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f"Error registering evaluation run in PostgreSQL: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def log_case(
        self,
        case_id: str,
        run_id: str,
        question_id: str,
        question_text: str,
        target_document: Optional[str],
        gold_answer: Optional[str],
        gold_evidence: Dict[str, Any],
        query_route: str,
        generated_answer: str,
        status: str,
        execution_time_ms: float,
    ) -> bool:
        cur = self._get_cursor()
        if not cur:
            return False

        try:
            # Insert case
            cur.execute("""
                INSERT INTO evaluation_cases (
                    case_id, run_id, question_id, question_text, target_document,
                    gold_answer, gold_evidence, query_route, generated_answer,
                    status, execution_time_ms, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (case_id) DO UPDATE SET
                    generated_answer = EXCLUDED.generated_answer,
                    status = EXCLUDED.status,
                    execution_time_ms = EXCLUDED.execution_time_ms;
            """, (
                case_id, run_id, question_id, question_text, target_document,
                gold_answer, json.dumps(gold_evidence), query_route, generated_answer,
                status, execution_time_ms
            ))

            # Also log into chat_messages as conversation turn
            session_id = f"EVAL::case::{run_id}"
            cur.execute("""
                INSERT INTO chat_messages (session_id, role, content, mode, created_at)
                VALUES (%s, 'user', %s, 'eval', CURRENT_TIMESTAMP);
            """, (session_id, question_text))
            cur.execute("""
                INSERT INTO chat_messages (session_id, role, content, mode, created_at)
                VALUES (%s, 'assistant', %s, 'eval', CURRENT_TIMESTAMP);
            """, (session_id, generated_answer))

            self.conn.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f"Error logging case {case_id} in PostgreSQL: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def log_retrieval_trace(self, case_id: str, run_id: str, trace_data: Dict[str, Any]) -> bool:
        cur = self._get_cursor()
        if not cur:
            return False

        try:
            cur.execute("""
                INSERT INTO evaluation_retrieval_trace (
                    case_id, run_id, vector_candidates, bm25_candidates, graph_candidates,
                    rrf_candidates, reranked_candidates,
                    gold_present_in_vector, gold_present_in_bm25, gold_present_in_graph,
                    gold_present_in_rrf, gold_present_in_reranked,
                    rank_vector, rank_bm25, rank_graph, rank_rrf, rank_reranked,
                    retrieval_latency_ms, rerank_latency_ms, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (case_id) DO NOTHING;
            """, (
                case_id, run_id,
                json.dumps(trace_data.get("vector_candidates", [])),
                json.dumps(trace_data.get("bm25_candidates", [])),
                json.dumps(trace_data.get("graph_candidates", [])),
                json.dumps(trace_data.get("rrf_candidates", [])),
                json.dumps(trace_data.get("reranked_candidates", [])),
                trace_data.get("gold_present_in_vector", False),
                trace_data.get("gold_present_in_bm25", False),
                trace_data.get("gold_present_in_graph", False),
                trace_data.get("gold_present_in_rrf", False),
                trace_data.get("gold_present_in_reranked", False),
                trace_data.get("rank_vector", -1),
                trace_data.get("rank_bm25", -1),
                trace_data.get("rank_graph", -1),
                trace_data.get("rank_rrf", -1),
                trace_data.get("rank_reranked", -1),
                trace_data.get("retrieval_latency_ms", 0.0),
                trace_data.get("rerank_latency_ms", 0.0)
            ))
            self.conn.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f"Error logging retrieval trace for {case_id}: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def log_qa_result(self, case_id: str, run_id: str, qa_data: Dict[str, Any]) -> bool:
        cur = self._get_cursor()
        if not cur:
            return False

        try:
            cur.execute("""
                INSERT INTO evaluation_qa_results (
                    case_id, run_id, exact_match, token_f1, rouge_l,
                    numeric_exact_match, supporting_fact_precision,
                    supporting_fact_recall, supporting_fact_f1,
                    hop_count_expected, hop_count_completed,
                    faithfulness_score, quality_gate_decision,
                    citations_valid, unsupported_answer, unnecessary_abstention,
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (case_id) DO NOTHING;
            """, (
                case_id, run_id,
                qa_data.get("exact_match", False),
                qa_data.get("token_f1", 0.0),
                qa_data.get("rouge_l", 0.0),
                qa_data.get("numeric_exact_match", False),
                qa_data.get("supporting_fact_precision", 0.0),
                qa_data.get("supporting_fact_recall", 0.0),
                qa_data.get("supporting_fact_f1", 0.0),
                qa_data.get("hop_count_expected", 1),
                qa_data.get("hop_count_completed", 1),
                qa_data.get("faithfulness_score", 1.0),
                qa_data.get("quality_gate_decision", "ACCEPT"),
                qa_data.get("citations_valid", True),
                qa_data.get("unsupported_answer", False),
                qa_data.get("unnecessary_abstention", False)
            ))
            self.conn.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f"Error logging QA result for {case_id}: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def log_failure(self, failure_report: Any) -> bool:
        cur = self._get_cursor()
        if not cur or not failure_report:
            return False

        try:
            cur.execute("""
                INSERT INTO evaluation_failures (
                    case_id, run_id, root_cause, secondary_cause,
                    affected_component, failure_evidence, trace_stage,
                    recommended_fix, confidence, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP);
            """, (
                f"{failure_report.run_id}_{failure_report.question_id}",
                failure_report.run_id,
                failure_report.root_cause,
                failure_report.secondary_cause,
                failure_report.affected_component,
                failure_report.retrieved_evidence,
                failure_report.failure_stage,
                failure_report.proposed_fix,
                failure_report.confidence
            ))
            self.conn.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f"Error logging failure card: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def log_metric(self, run_id: str, layer: str, metric_name: str, value: float, sample_size: int) -> bool:
        cur = self._get_cursor()
        if not cur:
            return False

        try:
            cur.execute("""
                INSERT INTO evaluation_metrics (run_id, layer, metric_name, metric_value, sample_size, created_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP);
            """, (run_id, layer, metric_name, value, sample_size))
            self.conn.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f"Error logging metric {metric_name}: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def complete_run(self, run_id: str, total: int, passed: int, failed: int) -> bool:
        cur = self._get_cursor()
        if not cur:
            return False

        try:
            cur.execute("""
                UPDATE evaluation_runs
                SET status = 'COMPLETED',
                    total_cases = %s,
                    passed_cases = %s,
                    failed_cases = %s,
                    completed_at = CURRENT_TIMESTAMP
                WHERE run_id = %s;
            """, (total, passed, failed, run_id))
            self.conn.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f"Error completing run {run_id}: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()
