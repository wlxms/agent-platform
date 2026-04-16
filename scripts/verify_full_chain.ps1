param()

$ErrorActionPreference = "Stop"
$Gateway = "http://localhost:8000"
$ApiKey = "oh-admin-key"

function Write-Step($num, $desc) {
    Write-Host ("`n[{0}] {1}" -f $num, $desc) -ForegroundColor Cyan
}

function Write-Pass($msg) {
    Write-Host "  PASS: $msg" -ForegroundColor Green
}

function Write-Fail($msg) {
    Write-Host "  FAIL: $msg" -ForegroundColor Red
}

function Test-Endpoint($method, $url, $body, $headers) {
    try {
        if ($body) {
            $resp = Invoke-RestMethod -Method $method -Uri $url -ContentType "application/json" -Body ($body | ConvertTo-Json -Depth 5) -Headers $headers -TimeoutSec 30
        } else {
            $resp = Invoke-RestMethod -Method $method -Uri $url -Headers $headers -TimeoutSec 30
        }
        return @{ Success = $true; Data = $resp }
    } catch {
        return @{ Success = $false; Error = $_.Exception.Message }
    }
}

# Check gateway health
Write-Host "=== OpenHarness Enterprise Full Chain Verification ===" -ForegroundColor Cyan
$health = Test-Endpoint "GET" "$Gateway/health" $null $null
if (-not $health.Success) { Write-Fail "Gateway not reachable at $Gateway"; exit 1 }
Write-Pass "Gateway healthy"

# Step 1: Login
Write-Step 1 "Login with API Key"
$login = Test-Endpoint "POST" "$Gateway/api/v1/auth/login" @{ api_key = $ApiKey } $null
if (-not $login.Success) { Write-Fail "Login failed: $($login.Error)"; exit 1 }
$token = $login.Data.data.token
Write-Pass "Got JWT token"

# Step 2: Get user info
Write-Step 2 "Get current user info"
$me = Test-Endpoint "GET" "$Gateway/api/v1/auth/me" $null @{ Authorization = "Bearer $token" }
if (-not $me.Success) { Write-Fail "Me failed: $($me.Error)"; exit 1 }
Write-Pass "User: $($me.Data.data.role) @ $($me.Data.data.org_id)"

# Step 3: List agents
Write-Step 3 "List agents"
$agents = Test-Endpoint "GET" "$Gateway/api/v1/agents" $null @{ Authorization = "Bearer $token" }
if (-not $agents.Success) { Write-Fail "List agents failed: $($agents.Error)"; exit 1 }
Write-Pass "Agents: $($agents.Data.total) total"

# Step 4: Create agent
Write-Step 4 "Create agent"
$agentName = "verify-test-$(Get-Random)"
$create = Test-Endpoint "POST" "$Gateway/api/v1/agents" @{ name = $agentName } @{ Authorization = "Bearer $token" }
if (-not $create.Success) { Write-Fail "Create failed: $($create.Error)"; exit 1 }
$agentId = $create.Data.data.id
$agentStatus = $create.Data.data.status
Write-Pass "Created: $agentName (status=$agentStatus, id=$agentId)"

# Step 5: Get agent
Write-Step 5 "Get agent detail"
$detail = Test-Endpoint "GET" "$Gateway/api/v1/agents/$agentId" $null @{ Authorization = "Bearer $token" }
if (-not $detail.Success) { Write-Fail "Get agent failed: $($detail.Error)"; exit 1 }
Write-Pass "Agent: $($detail.Data.data.name)"

# Step 6: Unauthorized test
Write-Step 6 "Test unauthorized (no token)"
try {
    $null = Invoke-WebRequest -Method GET -Uri "$Gateway/api/v1/agents" -TimeoutSec 10 -ErrorAction Stop
    Write-Fail "Should have returned 401"
    exit 1
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    if ($code -eq 401) {
        Write-Pass "Correctly returned 401"
    } else {
        Write-Fail "Expected 401, got $code"
        exit 1
    }
}

Write-Host "`n=== All checks passed! ===" -ForegroundColor Green
