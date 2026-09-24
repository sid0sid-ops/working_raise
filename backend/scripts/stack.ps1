param(
    [Parameter(Position=0, Mandatory=$false)]
    [ValidateSet("start", "stop", "restart", "status", "logs", "audit", "build", "ps", "test-rust")]
    [string]$Action = "status",

    [Parameter(Position=1, Mandatory=$false)]
    [string]$Service = ""
)

$ComposeFile = Join-Path (Split-Path $PSScriptRoot -Parent) "docker-compose.yml"
if (-not (Test-Path $ComposeFile)) {
    $ComposeFile = Join-Path $PSScriptRoot "docker-compose.yml"
}

function Show-Header {
    Write-Host ""
    Write-Host "=======================================================" -ForegroundColor Cyan
    Write-Host "   RAISE Studio Unified Container Stack Orchestrator   " -ForegroundColor Yellow
    Write-Host "=======================================================" -ForegroundColor Cyan
    Write-Host ""
}

if ($Action -eq "start") {
    Show-Header
    Write-Host "[+] Starting RAISE Production Stack via Compose..." -ForegroundColor Green
    docker compose -f $ComposeFile up -d --remove-orphans
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "[OK] Stack started successfully. Container status:" -ForegroundColor Green
        docker compose -f $ComposeFile ps
    } else {
        Write-Host ""
        Write-Host "[ERROR] Failed to start some services. Check: .\stack.ps1 logs" -ForegroundColor Red
    }
}
elseif ($Action -eq "stop") {
    Show-Header
    Write-Host "[*] Gracefully stopping all RAISE services..." -ForegroundColor Yellow
    docker compose -f $ComposeFile down
    Write-Host ""
    Write-Host "[OK] All services halted." -ForegroundColor Green
}
elseif ($Action -eq "restart") {
    Show-Header
    if ($Service -ne "") {
        Write-Host "[*] Restarting service: $Service..." -ForegroundColor Yellow
        docker compose -f $ComposeFile restart $Service
    } else {
        Write-Host "[*] Restarting entire stack..." -ForegroundColor Yellow
        docker compose -f $ComposeFile down
        docker compose -f $ComposeFile up -d
    }
}
elseif ($Action -eq "status") {
    Show-Header
    Write-Host "1. Container Status & Ports:" -ForegroundColor Cyan
    docker compose -f $ComposeFile ps
    Write-Host ""
    Write-Host "2. Unified Bridge Network (raise-network):" -ForegroundColor Cyan
    docker network inspect raise-network -f "{{range .Containers}} - {{.Name}} ({{.IPv4Address}}){{println}}{{end}}"
    Write-Host ""
    Write-Host "3. Resource Footprint:" -ForegroundColor Cyan
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}
elseif ($Action -eq "ps") {
    docker compose -f $ComposeFile ps
}
elseif ($Action -eq "logs") {
    if ($Service -ne "") {
        Write-Host "[*] Streaming logs for service: $Service (Ctrl+C to stop)..." -ForegroundColor Yellow
        docker compose -f $ComposeFile logs -f $Service
    } else {
        Write-Host "[*] Streaming logs for all services (Ctrl+C to stop)..." -ForegroundColor Yellow
        docker compose -f $ComposeFile logs -f --tail 100
    }
}
elseif ($Action -eq "build") {
    Show-Header
    Write-Host "[*] Rebuilding backend and local images without cache..." -ForegroundColor Yellow
    docker compose -f $ComposeFile build --pull --no-cache
    Write-Host ""
    Write-Host "[OK] Build complete." -ForegroundColor Green
}
elseif ($Action -eq "audit") {
    Show-Header
    Write-Host "[*] Running Docker Scout Security Policy Audit on raise-backend:latest..." -ForegroundColor Cyan
    docker scout quickview raise-backend:latest
}
elseif ($Action -eq "test-rust") {
    Show-Header
    Write-Host "[*] Testing native Rust acceleration engine inside Docker container..." -ForegroundColor Cyan
    docker compose -f $ComposeFile exec backend python -c "import raise_engine; print('[OK] Rust engine active:', raise_engine.clean_text('Test-\ning  engine')); print('[OK] Claim fingerprint:', raise_engine.claim_fingerprint('Claim test', 'doc1', 1))"
    Write-Host ""
}
