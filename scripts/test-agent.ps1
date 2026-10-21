# Test Script for Flash Desktop Agent Endpoints & Actions
# Usage: powershell -ExecutionPolicy Bypass -File .\scripts\test-agent.ps1

$BaseUrl = "http://127.0.0.1:8765"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Flash Agent Live Action & API Verification Suite       " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Health Endpoint
Write-Host "`n[1/8] Testing /health endpoint..." -ForegroundColor Yellow
$maxRetries = 3
$connected = $false
for ($i = 1; $i -le $maxRetries; $i++) {
    try {
        $health = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get -TimeoutSec 5
        Write-Host "  Health Status: $($health.status) | App: $($health.app) | Version: $($health.version)" -ForegroundColor Green
        $connected = $true
        break
    } catch {
        if ($i -lt $maxRetries) {
            Start-Sleep -Seconds 2
        }
    }
}
if (-not $connected) {
    Write-Error "  Failed to reach $BaseUrl/health. Is the agent running? Start it with .\scripts\run-agent.ps1"
    exit 1
}

# 2. Action 7: get_agent_status
Write-Host "`n[2/8] Testing Action: get_agent_status..." -ForegroundColor Yellow
$body = @{ action = "get_agent_status"; parameters = @{} } | ConvertTo-Json
$status = Invoke-RestMethod -Uri "$BaseUrl/api/v1/actions/execute" -Method Post -Body $body -ContentType "application/json"
Write-Host "  Success: $($status.success) | Message: $($status.message)" -ForegroundColor Green
Write-Host "  Registered Actions ($($status.data.action_count)): $($status.data.available_actions -join ', ')" -ForegroundColor Gray

# 3. Action 3: create_text_file
Write-Host "`n[3/8] Testing Action: create_text_file..." -ForegroundColor Yellow
$body = @{
    action = "create_text_file"
    parameters = @{
        filename = "documents/test_script_note.txt"
        content = "Flash desktop automation verified.`nTimestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        overwrite = $true
    }
} | ConvertTo-Json
$fileRes = Invoke-RestMethod -Uri "$BaseUrl/api/v1/actions/execute" -Method Post -Body $body -ContentType "application/json"
Write-Host "  Success: $($fileRes.success) | Message: $($fileRes.message)" -ForegroundColor Green
Write-Host "  File saved at: $($fileRes.output_path)" -ForegroundColor Gray

# 4. Action 4: create_grocery_list
Write-Host "`n[4/8] Testing Action: create_grocery_list..." -ForegroundColor Yellow
$body = @{
    action = "create_grocery_list"
    parameters = @{
        title = "Flash DMV Break Snacks"
        items = @("Coffee beans", "Sugar cubes", "Oat milk", "Glazed donuts")
        filename = "lists/dmv_snacks.md"
    }
} | ConvertTo-Json
$grocRes = Invoke-RestMethod -Uri "$BaseUrl/api/v1/actions/execute" -Method Post -Body $body -ContentType "application/json"
Write-Host "  Success: $($grocRes.success) | Message: $($grocRes.message)" -ForegroundColor Green
Write-Host "  Grocery list saved at: $($grocRes.output_path)" -ForegroundColor Gray

# 5. Action 5: create_spreadsheet
Write-Host "`n[5/8] Testing Action: create_spreadsheet..." -ForegroundColor Yellow
$body = @{
    action = "create_spreadsheet"
    parameters = @{
        headers = @("License Number", "Applicant", "Fee Paid", "Status")
        rows = @(
            @("DMV-1001", "Judy Hopps", 45.0, "Approved"),
            @("DMV-1002", "Nick Wilde", 55.0, "Approved"),
            @("DMV-1003", "Chief Bogo", 90.0, "Pending")
        )
        filename = "spreadsheets/dmv_licenses.xlsx"
        sheet_name = "Licenses"
        include_total_row = $true
    }
} | ConvertTo-Json -Depth 5
$sheetRes = Invoke-RestMethod -Uri "$BaseUrl/api/v1/actions/execute" -Method Post -Body $body -ContentType "application/json"
Write-Host "  Success: $($sheetRes.success) | Message: $($sheetRes.message)" -ForegroundColor Green
Write-Host "  Spreadsheet saved at: $($sheetRes.output_path)" -ForegroundColor Gray

# 6. Action 6: open_file
Write-Host "`n[6/8] Testing Action: open_file..." -ForegroundColor Yellow
$body = @{
    action = "open_file"
    parameters = @{ filepath = "documents/test_script_note.txt" }
} | ConvertTo-Json
$openRes = Invoke-RestMethod -Uri "$BaseUrl/api/v1/actions/execute" -Method Post -Body $body -ContentType "application/json"
Write-Host "  Success: $($openRes.success) | Message: $($openRes.message)" -ForegroundColor Green

# 7. Action 1: open_url
Write-Host "`n[7/8] Testing Action: open_url..." -ForegroundColor Yellow
$body = @{
    action = "open_url"
    parameters = @{ url = "https://www.python.org" }
} | ConvertTo-Json
$urlRes = Invoke-RestMethod -Uri "$BaseUrl/api/v1/actions/execute" -Method Post -Body $body -ContentType "application/json"
Write-Host "  Success: $($urlRes.success) | Message: $($urlRes.message)" -ForegroundColor Green

# 8. Action 2: type_text
Write-Host "`n[8/11] Testing Action: type_text..." -ForegroundColor Yellow
$body = @{
    action = "type_text"
    parameters = @{
        text = "Hello from Flash live test!"
        interval_ms = 5
        press_return = $false
    }
} | ConvertTo-Json
$typeRes = Invoke-RestMethod -Uri "$BaseUrl/api/v1/actions/execute" -Method Post -Body $body -ContentType "application/json"
Write-Host "  Success: $($typeRes.success) | Message: $($typeRes.message)" -ForegroundColor Green

# 9. Milestone 2: AI Status Endpoint
Write-Host "`n[9/11] Testing AI Status Endpoint (/api/v1/ai/status)..." -ForegroundColor Yellow
try {
    $aiStatus = Invoke-RestMethod -Uri "$BaseUrl/api/v1/ai/status" -Method Get -TimeoutSec 15
    Write-Host "  Ollama Installed: $($aiStatus.is_installed) | Running: $($aiStatus.is_running) | Model: $($aiStatus.configured_model)" -ForegroundColor Green
    Write-Host "  Model Available: $($aiStatus.is_model_available) | Available Models: $($aiStatus.available_models -join ', ')" -ForegroundColor Gray
} catch {
    Write-Host "  AI status check error: $_" -ForegroundColor Red
}

# 10. Milestone 2: AI Task Interpretation
Write-Host "`n[10/11] Testing AI Prompt Interpretation (/api/v1/ai/interpret)..." -ForegroundColor Yellow
$interpretBody = @{
    prompt = "Make a grocery list with coffee beans, oat milk and bananas"
} | ConvertTo-Json
try {
    $planRes = Invoke-RestMethod -Uri "$BaseUrl/api/v1/ai/interpret" -Method Post -Body $interpretBody -ContentType "application/json" -TimeoutSec 150
    Write-Host "  Intent: $($planRes.intent)" -ForegroundColor Green
    Write-Host "  Flash Explanation: $($planRes.user_facing_explanation)" -ForegroundColor Cyan
    Write-Host "  Planned Action(s): $($planRes.actions.action_name -join ', ')" -ForegroundColor Gray
} catch {
    Write-Host "  (Ollama prompt interpretation skipped or timed out: $_)" -ForegroundColor DarkYellow
}

# 11. Milestone 2: AI Orchestrated Task Execution
Write-Host "`n[11/11] Testing AI Orchestrated Execution (/api/v1/ai/execute)..." -ForegroundColor Yellow
$execBody = @{
    prompt = "Create a document summarizing these notes and save it."
    confirmed = $true
} | ConvertTo-Json
try {
    $taskRes = Invoke-RestMethod -Uri "$BaseUrl/api/v1/ai/execute" -Method Post -Body $execBody -ContentType "application/json" -TimeoutSec 150
    Write-Host "  Task ID: $($taskRes.task_id) | Status: $($taskRes.status) | Success: $($taskRes.success)" -ForegroundColor Green
    Write-Host "  Explanation: $($taskRes.explanation)" -ForegroundColor Cyan
} catch {
    Write-Host "  (Ollama task execution skipped or timed out: $_)" -ForegroundColor DarkYellow
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "   All Flash Milestone 1 & 2 Tests Completed!             " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

