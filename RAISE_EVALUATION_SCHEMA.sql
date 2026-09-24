-- ==============================================================================
-- RAISE Academic GraphRAG — Authoritative Evaluation Database Schema
-- Version: 1.0.0
-- Database: PostgreSQL 16
-- Compliance: Immutable Evaluation Sessions, Provenance, & Metric Scorecards
-- ==============================================================================

-- 1. Ensure Extension for UUID Generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Master Evaluation Runs Table (Immutable)
CREATE TABLE IF NOT EXISTS evaluation_runs (
    run_id VARCHAR(100) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES session_metadata(id) ON DELETE CASCADE,
    benchmark VARCHAR(100) NOT NULL,
    dataset VARCHAR(100) NOT NULL,
    split VARCHAR(50) NOT NULL DEFAULT 'test',
    experiment_id VARCHAR(100) NOT NULL DEFAULT 'EXP-0000',
    git_commit VARCHAR(64) NOT NULL,
    config_hash VARCHAR(64) NOT NULL,
    model_manifest JSONB NOT NULL DEFAULT '{}'::jsonb,
    runtime_manifest JSONB NOT NULL DEFAULT '{}'::jsonb,
    ablation_config VARCHAR(50) NOT NULL DEFAULT 'ABL-G',
    evaluation_mode VARCHAR(50) NOT NULL DEFAULT 'MODE_B_END_TO_END',
    total_cases INT NOT NULL DEFAULT 0,
    passed_cases INT NOT NULL DEFAULT 0,
    failed_cases INT NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'RUNNING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_eval_runs_benchmark ON evaluation_runs(benchmark);
CREATE INDEX IF NOT EXISTS idx_eval_runs_session ON evaluation_runs(session_id);
CREATE INDEX IF NOT EXISTS idx_eval_runs_experiment ON evaluation_runs(experiment_id);

-- 3. Individual Test Case Evaluations (Question-Level Records)
CREATE TABLE IF NOT EXISTS evaluation_cases (
    case_id VARCHAR(160) PRIMARY KEY, -- {run_id}_{question_id}
    run_id VARCHAR(100) NOT NULL REFERENCES evaluation_runs(run_id) ON DELETE CASCADE,
    question_id VARCHAR(100) NOT NULL,
    question_text TEXT NOT NULL,
    target_document VARCHAR(255),
    gold_answer TEXT,
    gold_evidence JSONB DEFAULT '{}'::jsonb,
    query_route VARCHAR(50) DEFAULT 'HYBRID_VECTOR',
    generated_answer TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'SUCCESS',
    execution_time_ms DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_eval_cases_run ON evaluation_cases(run_id);
CREATE INDEX IF NOT EXISTS idx_eval_cases_qid ON evaluation_cases(question_id);
CREATE INDEX IF NOT EXISTS idx_eval_cases_status ON evaluation_cases(status);

-- 4. Retrieval & Ranking Stage Tracing (Candidate Substrates & Fusion)
CREATE TABLE IF NOT EXISTS evaluation_retrieval_trace (
    case_id VARCHAR(160) PRIMARY KEY REFERENCES evaluation_cases(case_id) ON DELETE CASCADE,
    run_id VARCHAR(100) NOT NULL REFERENCES evaluation_runs(run_id) ON DELETE CASCADE,
    vector_candidates JSONB DEFAULT '[]'::jsonb,
    bm25_candidates JSONB DEFAULT '[]'::jsonb,
    graph_candidates JSONB DEFAULT '[]'::jsonb,
    rrf_candidates JSONB DEFAULT '[]'::jsonb,
    reranked_candidates JSONB DEFAULT '[]'::jsonb,
    gold_present_in_vector BOOLEAN DEFAULT FALSE,
    gold_present_in_bm25 BOOLEAN DEFAULT FALSE,
    gold_present_in_graph BOOLEAN DEFAULT FALSE,
    gold_present_in_rrf BOOLEAN DEFAULT FALSE,
    gold_present_in_reranked BOOLEAN DEFAULT FALSE,
    rank_vector INT DEFAULT -1,
    rank_bm25 INT DEFAULT -1,
    rank_graph INT DEFAULT -1,
    rank_rrf INT DEFAULT -1,
    rank_reranked INT DEFAULT -1,
    retrieval_latency_ms DOUBLE PRECISION DEFAULT 0.0,
    rerank_latency_ms DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_retrieval_trace_run ON evaluation_retrieval_trace(run_id);

-- 5. QA Accuracy, Grounding & Safety Results
CREATE TABLE IF NOT EXISTS evaluation_qa_results (
    case_id VARCHAR(160) PRIMARY KEY REFERENCES evaluation_cases(case_id) ON DELETE CASCADE,
    run_id VARCHAR(100) NOT NULL REFERENCES evaluation_runs(run_id) ON DELETE CASCADE,
    exact_match BOOLEAN DEFAULT FALSE,
    token_f1 DOUBLE PRECISION DEFAULT 0.0,
    rouge_l DOUBLE PRECISION DEFAULT 0.0,
    numeric_exact_match BOOLEAN DEFAULT FALSE,
    supporting_fact_precision DOUBLE PRECISION DEFAULT 0.0,
    supporting_fact_recall DOUBLE PRECISION DEFAULT 0.0,
    supporting_fact_f1 DOUBLE PRECISION DEFAULT 0.0,
    hop_count_expected INT DEFAULT 1,
    hop_count_completed INT DEFAULT 1,
    faithfulness_score DOUBLE PRECISION DEFAULT 1.0,
    quality_gate_decision VARCHAR(50) DEFAULT 'ACCEPT',
    citations_valid BOOLEAN DEFAULT TRUE,
    unsupported_answer BOOLEAN DEFAULT FALSE,
    unnecessary_abstention BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_qa_results_run ON evaluation_qa_results(run_id);

-- 6. Forensic Failure Categorization (22-Category Taxonomy)
CREATE TABLE IF NOT EXISTS evaluation_failures (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(160) NOT NULL REFERENCES evaluation_cases(case_id) ON DELETE CASCADE,
    run_id VARCHAR(100) NOT NULL REFERENCES evaluation_runs(run_id) ON DELETE CASCADE,
    root_cause VARCHAR(100) NOT NULL,
    secondary_cause VARCHAR(100),
    affected_component VARCHAR(100) NOT NULL,
    failure_evidence TEXT,
    trace_stage VARCHAR(100) NOT NULL,
    recommended_fix TEXT,
    confidence DOUBLE PRECISION DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_failures_run ON evaluation_failures(run_id);
CREATE INDEX IF NOT EXISTS idx_failures_root_cause ON evaluation_failures(root_cause);
CREATE INDEX IF NOT EXISTS idx_failures_component ON evaluation_failures(affected_component);

-- 7. High-Resolution Event Telemetry Log
CREATE TABLE IF NOT EXISTS evaluation_events (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(100) NOT NULL REFERENCES evaluation_runs(run_id) ON DELETE CASCADE,
    case_id VARCHAR(160),
    stage VARCHAR(100) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    duration_ms DOUBLE PRECISION DEFAULT 0.0,
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_eval_events_run ON evaluation_events(run_id);

-- 8. Aggregate Scorecard Metrics per Layer
CREATE TABLE IF NOT EXISTS evaluation_metrics (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(100) NOT NULL REFERENCES evaluation_runs(run_id) ON DELETE CASCADE,
    layer VARCHAR(50) NOT NULL, -- RETRIEVAL, RANKING, QA, GROUNDING, SAFETY, SYSTEM, MEMORY
    metric_name VARCHAR(100) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    confidence_interval_low DOUBLE PRECISION,
    confidence_interval_high DOUBLE PRECISION,
    sample_size INT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_eval_metrics_run ON evaluation_metrics(run_id);
CREATE INDEX IF NOT EXISTS idx_eval_metrics_layer ON evaluation_metrics(layer);

-- 9. PostgreSQL 16 + Redis 7 Conversational Memory Evaluation
CREATE TABLE IF NOT EXISTS memory_evaluation (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(100) NOT NULL REFERENCES evaluation_runs(run_id) ON DELETE CASCADE,
    session_id VARCHAR(255) NOT NULL,
    turn_index INT NOT NULL,
    declared_fact TEXT NOT NULL,
    recall_probe TEXT NOT NULL,
    recalled_value TEXT,
    write_success BOOLEAN NOT NULL DEFAULT FALSE,
    read_success BOOLEAN NOT NULL DEFAULT FALSE,
    recall_accuracy DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    memory_source VARCHAR(50) NOT NULL, -- POSTGRESQL, REDIS, MEMORY_COMBINED
    contamination_detected BOOLEAN NOT NULL DEFAULT FALSE,
    latency_ms DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_memory_eval_run ON memory_evaluation(run_id);
