param(
    [switch]$Check,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "ERROR: Virtual environment not found at $VenvPython" -ForegroundColor Red
    Write-Host "Run install.ps1 first." -ForegroundColor Yellow
    exit 1
}

$services = @(
    @{ Name = "gateway";   Port = 8000; Module = "agentp_gateway" }
    @{ Name = "auth";      Port = 8001; Module = "agentp_auth" }
    @{ Name = "host";      Port = 8002; Module = "agentp_host" }
    @{ Name = "scheduler"; Port = 8003; Module = "agentp_scheduler" }
    @{ Name = "memory";    Port = 8004; Module = "agentp_memory" }
    @{ Name = "market";    Port = 8005; Module = "agentp_market" }
    @{ Name = "billing";   Port = 8006; Module = "agentp_billing" }
)

function Write-Header($text) {
    Write-Host ""
    Write-Host "=== $text ===" -ForegroundColor Cyan
}

function Test-ServiceHealth($port) {
    try {
        $null = Invoke-RestMethod -Uri "http://localhost:$port/health" -TimeoutSec 3 -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Wait-ServiceReady($name, $port, $maxRetries = 10) {
    for ($i = 1; $i -le $maxRetries; $i++) {
        if (Test-ServiceHealth $port) {
            Write-Host "  [OK] $name (:$port) ready" -ForegroundColor Green
            return $true
        }
        Start-Sleep -Seconds 2
    }
    Write-Host "  [FAIL] $name (:$port) not ready after $maxRetries retries" -ForegroundColor Red
    return $false
}

if ($Check) {
    Write-Header "Checking Service Status"
    foreach ($svc in $services) {
        $healthy = Test-ServiceHealth $svc.Port
        $status = if ($healthy) { "RUNNING" } else { "STOPPED" }
        $color = if ($healthy) { "Green" } else { "Red" }
        Write-Host ("  {0,-12} :{1,-5} {2}" -f $svc.Name, $svc.Port, $status) -ForegroundColor $color
    }
    exit 0
}

Write-Header "OpenHarness Enterprise Dev Environment"
Write-Host "Starting services..." -ForegroundColor Yellow

$processes = @()
# Set DS_API_KEY for Host service (required by SDK send_message)
$env:DS_API_KEY = "sk-3aa4613249a34bc6a54d14f561ca7597"

# Build PYTHONPATH with all service src dirs + agent-orchestrator
$pythonPaths = @(
    (Join-Path $ProjectRoot "services\shared\src"),
    (Join-Path $ProjectRoot "services\gateway\src"),
    (Join-Path $ProjectRoot "services\auth\src"),
    (Join-Path $ProjectRoot "services\host\src"),
    (Join-Path $ProjectRoot "services\scheduler\src"),
    (Join-Path $ProjectRoot "services\memory\src"),
    (Join-Path $ProjectRoot "services\market\src"),
    (Join-Path $ProjectRoot "services\billing\src"),
    (Join-Path $ProjectRoot "agent-orchestrator\src")
)
$env:PYTHONPATH = ($pythonPaths -join [System.IO.Path]::PathSeparator)

foreach ($svc in $services) {
    Write-Host "  Starting $($svc.Name) (:$($svc.Port))..." -ForegroundColor Gray
    $proc = Start-Process -FilePath $VenvPython -ArgumentList "-m", $svc.Module `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Minimized `
        -PassThru
    $processes += @{ Name = $svc.Name; Port = $svc.Port; Process = $proc }
    Start-Sleep -Milliseconds 500
}

# Start Celery worker for async task processing (T5.4)
Write-Host "  Starting celery worker..." -ForegroundColor Gray
$celeryProc = Start-Process -FilePath $VenvPython -ArgumentList "-m", "celery", "-A", "agentp_scheduler.celery_app", "worker", "--loglevel=info", "-c", "agentp_scheduler.celery_app" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Minimized `
    -PassThru
$processes += @{ Name = "celery-worker"; Port = 0; Process = $celeryProc }

Write-Host ""
Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
$allReady = $true
foreach ($svc in $services) {
    if (-not (Wait-ServiceReady $svc.Name $svc.Port)) {
        $allReady = $false
    }
}

Write-Header "Service Status"
Write-Host ("  {0,-12} {1,-6} {2}" -f "Service", "Port", "Status")
Write-Host ("  {0,-12} {1,-6} {2}" -f "-------", "----", "------")
foreach ($svc in $services) {
    $healthy = Test-ServiceHealth $svc.Port
    $status = if ($healthy) { "OK" } else { "FAIL" }
    $color = if ($healthy) { "Green" } else { "Red" }
    Write-Host ("  {0,-12} :{1,-5} {2}" -f $svc.Name, $svc.Port, $status) -ForegroundColor $color
}

if (-not $allReady) {
    Write-Host ""
    Write-Host "Some services failed to start. Check logs above." -ForegroundColor Red
}

Write-Host ""
Write-Host "Gateway: http://localhost:8000" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop all services..." -ForegroundColor Gray

try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Header "Stopping Services"
    foreach ($p in $processes) {
        try {
            Stop-Process -Id $p.Process.Id -Force -ErrorAction SilentlyContinue
            Write-Host "  Stopped $($p.Name)" -ForegroundColor Gray
        } catch {}
    }
    Write-Host "All services stopped." -ForegroundColor Green
}
