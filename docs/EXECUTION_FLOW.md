# RAISE Execution Flow Specification

**Version**: 2.5.0  
**Status**: CANONICAL & AUTHORITATIVE  
**Verification Date**: 2026-09-14  

---

## 1. Overview

This document details the exact runtime call stacks, sequence diagrams, and execution paths for:
1. **Interactive Query & Chat Stream Turn** (`POST /api/chat?stream=True`)
2. **LangGraph 16-Node Cyclical Agent Execution**
3. **Isolated Evaluation Sandbox Turn (FRAMES Benchmark)**

---

## 2. Interactive Chat Stream Sequence (`POST /api/chat?stream=True`)

```mermaid
sequenceDiagram
    autonumber
    actor Client as User / Frontend
    participant Shield as ASGISecurityShield
    participant Router as ChatRouter (chat.py)
    participant Intake as QueryIntakeEngine
    participant Redis as Redis 7 (Cache)
    participant Retriever as ParallelRetriever
    participant Substrates as ChromaDB / BM25 / Neo4j
    participant Fusion as RRF & BGE-Reranker
    participant vLLM as vLLM (Qwen 2.5 14B)
    participant Verifier as 4-Tier Grounding Engine
    participant Postgres as PostgreSQL 16

    Client->>Shield: POST /api/chat (query, session_id, stream=True)
    Shield->>Shield: Validate IP, Rate Limit & 4KB Payload Cap
    Shield->>Router: Forward Request
    
    Router->>Intake: analyze_query(query)
    Intake-->>Router: Intent, Coreference Resolved, Deictic Cleaned
    
    Router->>Redis: Check Query Cache (rag:query:hash)
    alt Cache Hit
        Redis-->>Router: Return Cached Envelope
        Router-->>Client: Stream Cached Tokens + Final Event
    else Cache Miss
        Router->>Retriever: retrieve(query, session_drawer_docs)
        par Concurrent Retrieval
            Retriever->>Substrates: Dense Query (ChromaDB)
            Retriever->>Substrates: Sparse Query (BM25)
            Retriever->>Substrates: Graph Cypher (Neo4j)
            Retriever->>Substrates: Table Scan (TableEngine)
        end
        Substrates-->>Retriever: Multi-Substrate Candidates
        
        Retriever->>Fusion: reciprocal_rank_fusion(candidates, k=60)
        Fusion->>Fusion: Cross-Encoder Reranking (BGE-Reranker Singleton)
        Fusion-->>Router: Top-k Fused & Reranked Evidence Chunks
        
        Router->>vLLM: Stream Completions (Prompt Context + Query)
        loop Token Generation
            vLLM-->>Router: Chunk Token
            Router-->>Client: data: {"token": "..."}
        end
        vLLM-->>Router: Generation Complete
        
        Router->>Verifier: verify_claims(generated_text, retrieved_context)
        Verifier->>Verifier: Tier 1: Math & Number Tolerances (+-0.05)
        Verifier->>Verifier: Tier 2: Lexical Fast-Path
        Verifier->>Verifier: Tier 3: FineCat-NLI (ModernBERT FP16)
        Verifier->>Verifier: Tier 4: Context Expansion Fallback
        Verifier-->>Router: ClaimVerificationRecord Array + Faithfulness Score
        
        alt Faithfulness >= 0.80 and No Numerical Mismatch
            Router->>Postgres: Store Message Turn (Dual-Key: text + content)
            Router->>Redis: Cache Query Response
            Router-->>Client: event: final, data: {grounded_answer, citations, subgraph}
        else Quality Gate Rejection
            Router->>Postgres: Store Sanitized Refusal Turn
            Router-->>Client: event: final, data: {grounded_answer: "INSUFFICIENT REASONING PATH..."}
        end
        Router-->>Client: data: [DONE]
    end
```

---

## 3. LangGraph 16-Node Cyclical Agent Execution

For complex research and autonomous comparative tasks, RAISE activates the 16-node LangGraph state machine (`RAG/src/features/agent/workflow.py`):

```mermaid
stateDiagram-v2
    [*] --> Start: User Query
    Start --> AnalyzeIntent: intent_classifier
    
    AnalyzeIntent --> ConversationalResponse: greeting / off-topic
    AnalyzeIntent --> DecomposeQuery: complex / multi-hop
    AnalyzeIntent --> DirectRetrieval: single-fact
    
    DecomposeQuery --> SubQueryDispatcher: subquestions generated
    SubQueryDispatcher --> DirectRetrieval: query hop 1
    
    DirectRetrieval --> VectorSearch: parallel branch
    DirectRetrieval --> BM25Search: parallel branch
    DirectRetrieval --> GraphSearch: parallel branch
    DirectRetrieval --> TableSearch: parallel branch
    
    VectorSearch --> ReciprocalRankFusion: candidates
    BM25Search --> ReciprocalRankFusion: candidates
    GraphSearch --> ReciprocalRankFusion: candidates
    TableSearch --> ReciprocalRankFusion: candidates
    
    ReciprocalRankFusion --> CrossEncoderRerank: fused list
    CrossEncoderRerank --> EvaluateContextSufficient: top candidates
    
    EvaluateContextSufficient --> ExpandEvidenceGraph: insufficient info
    ExpandEvidenceGraph --> DirectRetrieval: hop 2 traversal
    
    EvaluateContextSufficient --> SynthesizeDraft: context complete
    SynthesizeDraft --> ExtractAtomicClaims: draft text
    
    ExtractAtomicClaims --> GroundingVerification: atomic claims
    GroundingVerification --> QualityGateDecision: verification ledger
    
    QualityGateDecision --> FormatFinalAnswer: pass (>=80%)
    QualityGateDecision --> RefinePrompt: retry (attempts < 2)
    RefinePrompt --> SynthesizeDraft: refined prompt
    QualityGateDecision --> SafeAbstention: fail / exhausted retries
    
    FormatFinalAnswer --> End: [DONE]
    ConversationalResponse --> End: [DONE]
    SafeAbstention --> End: [DONE]
```

---

## 4. Isolated FRAMES Benchmark Execution Flow

The Google Research FRAMES benchmark runner (`RAG/evaluation/benchmarks/frames/runners/runner.py`) uses an isolated sandbox harness (`IsolatedFramesHarness`):

1. **Question Selection**: `FramesDatasetLoader` extracts questions filtered by reasoning type (`Multi-hop`, `Numerical`, `Temporal`, `Tabular`).
2. **Anti-Leakage Verification**: Asserts that ground-truth reference answers are never indexed into the retrieval corpus.
3. **Ephemeral Ingestion**: Wikipedia articles linked to the target questions are fetched, chunked into section-aware passages, embedded via `bge-large-en-v1.5`, and indexed into an ephemeral ChromaDB collection and in-memory NetworkX graph.
4. **Isolated Hybrid Retrieval**: Executes dense vector search, in-memory BM25, and NetworkX 2-hop graph expansion.
5. **Context Assembly**: Compiles `[Source 1]... [Source 2]... [Knowledge Graph Connections]...`.
6. **vLLM Synthesis**: Calls local vLLM server (`Qwen 2.5 14B`) with temperature `0.0` requesting `Final Answer: <concise answer>`.
7. **Safe Abstention Check**: If reasoning path is unestablished, emits `INSUFFICIENT REASONING PATH: Required reasoning chain could not be established. No answer released.`
8. **Evaluator Scoring**: Evaluates factuality, reasoning, and retrieval coverage without writing to production databases.
