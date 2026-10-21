# Run Script for Flash Desktop Agent
# Usage:
#   Local only:  powershell -ExecutionPolicy Bypass -File .\scripts\run-agent.ps1
#   LAN / Phone: powershell -ExecutionPolicy Bypass -File .\scripts\run-agent.ps1 -Lan

param(
    [switch]$Lan,
    [string]$BindHost = "",
    [int]$Port = 8765
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$AgentDir = Join-Path $ProjectRoot "agent"
$VenvPython = Join-Path $AgentDir "venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Virtual environment not found. Running setup script first..." -ForegroundColor Yellow
    & (Join-Path $ScriptDir "setup-windows.ps1")
}

# Determine host binding
if ($Lan -or ($BindHost -eq "0.0.0.0")) {
    $EffectiveHost = "0.0.0.0"
} elseif ($BindHost -ne "") {
    $EffectiveHost = $BindHost
} else {
    # Default to 0.0.0.0 so phone on same Wi-Fi can connect easily while auth protects endpoints
    $EffectiveHost = "0.0.0.0"
}

# Detect Wi-Fi / LAN IP addresses
$LanIPs = @()
try {
    $LanIPs = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notmatch '^127\.' -and $_.IPAddress -notmatch '^169\.254\.' } |
        Select-Object -ExpandProperty IPAddress
} catch {}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "      Starting Flash Windows Desktop Agent (Local & LAN)   " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Local Host:        http://127.0.0.1:$Port" -ForegroundColor White
if ($LanIPs.Count -gt 0) {
    Write-Host "Wi-Fi LAN IP(s):   $($LanIPs -join ', ')" -ForegroundColor Yellow
    foreach ($ip in $LanIPs) {
        Write-Host "Phone Companion:   http://$($ip):$Port  (or ws://$($ip):$Port/ws/v1/companion)" -ForegroundColor Green
    }
} else {
    Write-Host "Wi-Fi LAN IP:      Check 'ipconfig' if connecting from phone" -ForegroundColor Gray
}
Write-Host "Health Check:      http://127.0.0.1:$Port/health" -ForegroundColor White
Write-Host "API Swagger Docs:  http://127.0.0.1:$Port/docs" -ForegroundColor White
Write-Host "Pairing Code API:  http://127.0.0.1:$Port/api/v1/auth/pair-code" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to terminate the agent." -ForegroundColor Yellow
Write-Host "----------------------------------------------------------`n"

# Run uvicorn server with auto-reload from the agent directory
Set-Location $AgentDir
& $VenvPython -m uvicorn app.main:app --host $EffectiveHost --port $Port --reload
