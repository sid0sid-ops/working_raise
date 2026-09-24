import os
import urllib.request
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=['Health & System'])

@router.get('/', response_class=JSONResponse)
async def root():
    return {
        'status': 'online',
        'service': 'RAISE Backend API',
        'version': '2.5.0',
        'docs_url': '/docs',
        'openapi_url': '/openapi.json',
        'health_check': '/health',
    }

@router.get('/api/health', response_class=JSONResponse)
@router.get('/health', response_class=JSONResponse)
async def health_check(request: Request):
    app = request.app
    dev_operator = getattr(app.state, 'dev_operator', None)
    if dev_operator is None:
        try:
            import app as master_app_mod
            dev_operator = getattr(master_app_mod, 'dev_operator', None)
        except Exception:
            pass
    if dev_operator is None:
        try:
            from src.features.system.service import DeveloperOperator
            dev_operator = DeveloperOperator()
        except Exception:
            dev_operator = None

    if dev_operator:
        try:
            checkup = dev_operator.run_full_checkup()
            dbs = checkup.get("databases", {})
            pg_ready = dbs.get("postgresql", {}).get("status") == "PASS" or dbs.get("postgresql", {}).get("connected") is True
            rd_ready = dbs.get("redis", {}).get("status") == "PASS" or dbs.get("redis", {}).get("connected") is True
            neo4j_ready = dbs.get("neo4j", {}).get("status") == "PASS" or dbs.get("neo4j", {}).get("connected") is True
            chroma_ready = dbs.get("chromadb", {}).get("status") == "PASS" or dbs.get("chromadb", {}).get("connected") is True
            vllm_ready = checkup.get("inference", {}).get("vllm", {}).get("status") == "PASS" or checkup.get("inference", {}).get("vllm", {}).get("online") is True
        except Exception as e:
            pg_ready = rd_ready = neo4j_ready = chroma_ready = vllm_ready = False
    else:
        rag_engine = getattr(app.state, 'rag_engine', None)
        postgres_mgr = getattr(app.state, 'postgres_manager', None)
        redis_cache = getattr(app.state, 'redis_cache', None)

        vllm_ready = False
        try:
            if rag_engine and hasattr(rag_engine, 'vllm_client') and rag_engine.vllm_client:
                vllm_ready = True
            else:
                vllm_url = os.getenv('VLLM_BASE_URL', 'http://localhost:8002/v1')
                health_url = vllm_url.replace('/v1', '') + '/health'
                req = urllib.request.Request(health_url, headers={'User-Agent': 'RAISE-HealthCheck'})
                with urllib.request.urlopen(req, timeout=0.6) as resp:
                    vllm_ready = (resp.status == 200)
        except Exception:
            vllm_ready = False

        chroma_ready = False
        try:
            chroma_ready = bool(rag_engine and rag_engine.vector_engine and rag_engine.vector_engine.collection is not None)
        except Exception:
            chroma_ready = False

        neo4j_ready = bool(rag_engine and rag_engine.neo4j_db and rag_engine.neo4j_db.connected)
        pg_ready = bool(postgres_mgr and (postgres_mgr.is_connected or getattr(postgres_mgr, '_memory_chat', None) is not None))
        rd_ready = bool(redis_cache and (redis_cache.is_connected or getattr(redis_cache, '_memory_cache', None) is not None))

    # Determine composite health status
    all_essential = pg_ready and rd_ready and neo4j_ready and chroma_ready
    composite_status = "healthy" if all_essential else ("degraded" if (neo4j_ready or chroma_ready) else "unhealthy")

    # LAN & Network coordinates
    lan_ip = "127.0.0.1"
    try:
        from src.api.context import get_lan_ip
        lan_ip = get_lan_ip()
    except Exception:
        pass
    port = int(os.getenv("PORT", "8000"))

    # Hardware Telemetry - dynamically detected with zero hardcoding
    from src.infrastructure.hardware import get_ram_info, get_gpu_info, get_llm_telemetry
    ram_info = get_ram_info()
    gpu_info = get_gpu_info()
    llm_info = get_llm_telemetry()

    return {
        'status': composite_status,
        'service': 'RAISE Master Agentic GraphRAG API',
        'message': 'Backend is running',
        'version': '2.5.0',
        'api_version': '2.5.0',
        'network': {
            'lan_ipv4': lan_ip,
            'port': port,
            'mac_accessible_url': f"http://{lan_ip}:{port}",
        },
        'postgres': pg_ready,
        'redis': rd_ready,
        'neo4j': neo4j_ready,
        'vllm': vllm_ready,
        'chroma': chroma_ready,
        'subsystems': {
            'postgres': pg_ready,
            'redis': rd_ready,
            'neo4j': neo4j_ready,
            'vllm': vllm_ready,
            'chroma': chroma_ready,
            'chromadb': chroma_ready,
            'llm': {
                'active_backend': llm_info.get('active_backend'),
                'fallback_chain': llm_info.get('fallback_chain'),
                'ready': vllm_ready or bool(os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY")),
            },
            'hardware': {
                'gpu': gpu_info.get('primary_device_name', 'N/A'),
                'gpu_vram_gb': gpu_info.get('primary_vram_gb'),
                'cuda_available': gpu_info.get('cuda_available', False),
                'device_count': gpu_info.get('device_count', 0),
                'ram_total_gb': ram_info.get('total_gb'),
                'ram_available_gb': ram_info.get('available_gb'),
                'ram_percent_used': ram_info.get('percent_used'),
            }
        }
    }

