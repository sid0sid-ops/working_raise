# Production Deployment Architecture: Docker Containerization

## 1. Multi-Service Container Stack Overview
Deploying this architecture in production requires containerizing each component with dedicated volume mounts, resource boundaries, and health checks to manage service dependencies.

The production container stack coordinates four key services:
1. **`neo4j`**: Hosts the persistent property graph via **Neo4j Community Edition**, handling ACID graph storage and parameterized point lookups.
2. **`chromadb`**: Runs the standalone **ChromaDB vector database server** for high-throughput dense vector similarity search.
3. **`vllm`**: Serves **Qwen 2.5 7B Instruct** with GPU acceleration, **PagedAttention**, high throughput batching, and native tool calling via OpenAI-compatible endpoints.
4. **`orchestrator`**: Runs the **LangGraph state machine**, in-memory **NetworkX analytics**, FastAPI application routes, and Claim Verification engines.

```
                  ┌──────────────────────────────────────────────┐
                  │                 Reverse Proxy                │
                  │              (Port 8000 / HTTPS)             │
                  └───────────────────────┬──────────────────────┘
                                          │
                  ┌───────────────────────▼──────────────────────┐
                  │           raise-orchestrator                 │
                  │   FastAPI + LangGraph + NetworkX Engine      │
                  └───────┬───────────────┬───────────────┬──────┘
                          │               │               │
            ┌─────────────┴─────┐   ┌─────┴──────────┐   ┌┴────────────────────┐
            ▼                   ▼   ▼                ▼   ▼                     ▼
     ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────────────┐
     │    neo4j    │     │  chromadb   │     │              vllm               │
     │  Community  │     │   Vector    │     │        Qwen 2.5 7B (GPU)        │
     │  Port 7687  │     │  Port 8000  │     │   PagedAttention / Tool Calling │
     └─────────────┘     └─────────────┘     └─────────────────────────────────┘
```

---

## 2. Service Definitions & Resource Boundaries

### 1. `neo4j` (Graph Store)
- **Image**: `neo4j:5.26-community`
- **Port Bindings**: `7474:7474` (Browser UI), `7687:7687` (Bolt Protocol)
- **Volume Mounts**: `neo4j_data:/data`, `neo4j_logs:/logs`, `neo4j_import:/var/lib/neo4j/import`
- **Memory Boundaries**: Initial Heap: `1G`, Max Heap: `4G`, PageCache: `2G`
- **Health Check**: `cypher-shell -u neo4j -p password123 'RETURN 1;'`

### 2. `chromadb` (Vector Store)
- **Image**: `chromadb/chroma:latest`
- **Port Bindings**: `8001:8000` (Vector REST API)
- **Volume Mounts**: `chroma_data:/chroma/chroma`
- **Health Check**: `curl -f http://localhost:8000/api/v1/heartbeat`

### 3. `vllm` (LLM Inference Engine)
- **Image**: `vllm/vllm-openai:latest`
- **Command**: `--model Qwen/Qwen2.5-7B-Instruct --gpu-memory-utilization 0.90 --max-model-len 8192 --trust-remote-code --enable-auto-tool-choice --tool-call-parser hermes`
- **Port Bindings**: `8002:8000` (OpenAI-compatible REST API)
- **Resource Reservation**: GPU Device reservation (`count: all`, `capabilities: [gpu]`)
- **Health Check**: `curl -f http://localhost:8000/health`

### 4. `orchestrator` (RAG Engine & LangGraph State Machine)
- **Image**: Built from `Dockerfile`
- **Port Bindings**: `8000:8000` (FastAPI / Studio Web UI)
- **Dependencies**: Waits for `neo4j` (healthy), `chromadb` (healthy), and `vllm` (healthy/started)
- **Volume Mounts**: `./data/documents:/app/data/documents:ro`, `./data/processed:/app/data/processed`, `./.runtime:/app/.runtime`
