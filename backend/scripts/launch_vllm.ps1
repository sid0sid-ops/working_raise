# ==============================================================================
# RAISE vLLM Dynamic GPU Deployment Launcher (PowerShell / Windows / WSL2)
# Dynamically queries GPU device properties and VRAM allocation
# ==============================================================================

$GpuInfo = "CUDA Accelerated GPU"
try {
    $smi = nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits 2>$null
    if ($smi) {
        $parts = $smi -split ','
        $GpuName = $parts[0].Trim()
        $GpuMem = [math]::Round([int]$parts[1].Trim() / 1024, 1)
        $GpuInfo = "$GpuName (${GpuMem}GB VRAM)"
    }
} catch {}

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " 🚀 Launching vLLM Engine for Qwen 2.5 14B Instruct (GPTQ Int4)" -ForegroundColor Green
Write-Host " GPU Target: $GpuInfo | Memory Budget: 55%" -ForegroundColor Yellow
Write-Host " PagedAttention: ENABLED | Automatic Prefix Caching: ENABLED" -ForegroundColor Yellow
Write-Host "======================================================================" -ForegroundColor Cyan

python -m vllm.entrypoints.openai.api_server `
    --model Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4 `
    --host 0.0.0.0 `
    --port 8000 `
    --quantization gptq `
    --max-model-len 8192 `
    --gpu-memory-utilization 0.55 `
    --enable-prefix-caching `
    --trust-remote-code `
    --tensor-parallel-size 1
