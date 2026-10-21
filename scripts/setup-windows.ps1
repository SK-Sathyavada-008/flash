# Windows Setup Script for Flash Desktop Agent
# Usage: powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Flash Windows Desktop Agent - Setup Environment        " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$AgentDir = Join-Path $ProjectRoot "agent"
$VenvDir = Join-Path $AgentDir "venv"
$RequirementsFile = Join-Path $AgentDir "requirements.txt"

# 1. Check Python installation
Write-Host "`n[1/4] Checking Python..." -ForegroundColor Yellow
$PythonCmd = Get-Command py -ErrorAction SilentlyContinue
if ($PythonCmd) {
    $PythonExe = "py"
    $PythonArgs = @("-3.13")
} else {
    $PythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $PythonCmd) {
        Write-Error "Python is not found in PATH. Please install Python 3.11+."
        exit 1
    }
    $PythonExe = "python"
    $PythonArgs = @()
}

Write-Host "Using Python launcher: $PythonExe $PythonArgs" -ForegroundColor Green

# 2. Create or verify virtual environment
Write-Host "`n[2/4] Setting up virtual environment at $VenvDir..." -ForegroundColor Yellow
if (-not (Test-Path (Join-Path $VenvDir "Scripts\python.exe"))) {
    & $PythonExe $PythonArgs -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create virtual environment."
        exit 1
    }
    Write-Host "Virtual environment created." -ForegroundColor Green
} else {
    Write-Host "Virtual environment already exists." -ForegroundColor Green
}

# 3. Upgrade pip and install dependencies
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
Write-Host "`n[3/4] Installing dependencies from $RequirementsFile..." -ForegroundColor Yellow
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r $RequirementsFile
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install dependencies."
    exit 1
}

# 4. Verify installation by running test suite
Write-Host "`n[4/4] Verifying setup with test suite..." -ForegroundColor Yellow
$VenvPytest = Join-Path $VenvDir "Scripts\pytest.exe"
& $VenvPytest $AgentDir\tests -v
if ($LASTEXITCODE -eq 0) {
    Write-Host "`nAll tests passed successfully!" -ForegroundColor Green
    Write-Host "`nSetup complete! You can start the agent with: .\scripts\run-agent.ps1" -ForegroundColor Cyan
} else {
    Write-Warning "Setup completed, but some tests reported issues."
}
