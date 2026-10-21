# Run Script for Flash Phone Companion PWA
# Usage: powershell -ExecutionPolicy Bypass -File .\scripts\run-companion.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$CompanionDir = Join-Path $ProjectRoot "companion"

Set-Location $CompanionDir

# Detect Wi-Fi / LAN IP addresses
$LanIPs = @()
try {
    $LanIPs = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notmatch '^127\.' -and $_.IPAddress -notmatch '^169\.254\.' } |
        Select-Object -ExpandProperty IPAddress
} catch {}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       Starting Flash Phone Companion (Vite PWA)          " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Local Laptop URL:    http://localhost:5173" -ForegroundColor White
if ($LanIPs.Count -gt 0) {
    Write-Host "Redmi Phone URL(s):" -ForegroundColor Yellow
    foreach ($ip in $LanIPs) {
        Write-Host "  -> http://${ip}:5173" -ForegroundColor Green
    }
} else {
    Write-Host "Redmi Phone URL:     Run 'ipconfig' to find your Wi-Fi IPv4" -ForegroundColor Gray
}
Write-Host "Ensure your Redmi phone is connected to the SAME Wi-Fi network." -ForegroundColor Cyan
Write-Host "Open Chrome on your phone, navigate to the URL, and tap 'Install' or 'Add to Home Screen'." -ForegroundColor White
Write-Host "Press Ctrl+C to stop the companion server." -ForegroundColor Yellow
Write-Host "----------------------------------------------------------`n"

npm run dev
