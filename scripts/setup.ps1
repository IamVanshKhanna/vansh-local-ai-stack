<#
.SYNOPSIS
    One-command setup for vansh-local-ai-stack (Scenario B)
.DESCRIPTION
    Installs Ollama, pulls models, creates venv, installs deps, configures
    environment, and optionally registers scheduled tasks. Idempotent -
    safe to re-run anytime.
.EXAMPLE
    .\scripts\setup.ps1
    .\scripts\setup.ps1 -ScheduleTasks
    .\scripts\setup.ps1 -SkipOllama
#>

param(
    [switch]$ScheduleTasks,
    [switch]$SkipOllama,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DataRoot = "$env:USERPROFILE\.local-ai-stack"

function Write-Step {
    param([string]$Message)
    Write-Host "`n>> $Message" -ForegroundColor Cyan
}

function Write-OK {
    param([string]$Message)
    Write-Host "  [OK] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "  [!] $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Message)
    Write-Host "  [X] $Message" -ForegroundColor Red
}

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

# ────────────────────────────────────────────
# 1. Prerequisites
# ────────────────────────────────────────────
Write-Step "Checking prerequisites"

$pythonOk = Test-Command "python"
if (-not $pythonOk) {
    Write-Fail "Python 3.10+ not found. Install from https://python.org"
    exit 1
}
Write-OK "Python found"

$pythonVersion = python --version 2>&1
Write-OK $pythonVersion

if (-not (Test-Command "winget")) {
    Write-Warn "winget not found - some features may require manual install"
} else {
    Write-OK "winget available"
}

# ────────────────────────────────────────────
# 2. Ollama installation
# ────────────────────────────────────────────
if (-not $SkipOllama) {
    Write-Step "Ollama"

    $ollamaOk = Test-Command "ollama"
    if (-not $ollamaOk) {
        Write-Warn "Ollama not installed. Installing via winget..."
        try {
            winget install --silent --accept-package-agreements Ollama.Ollama 2>&1 | Out-Null
            Write-OK "Ollama installed"
        } catch {
            Write-Fail "Failed to install Ollama. Install manually from https://ollama.com"
            exit 1
        }
    } else {
        Write-OK "Ollama already installed"
    }

    # Ensure Ollama service is running
    $ollamaRunning = $false
    try {
        $null = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3
        $ollamaRunning = $true
    } catch {}

    if (-not $ollamaRunning) {
        Write-Warn "Starting Ollama service..."
        try {
            Start-Process -WindowStyle Hidden -FilePath "ollama" -ArgumentList "serve"
            Start-Sleep -Seconds 3
        } catch {
            Write-Warn "Could not start Ollama automatically. Start it manually from Start Menu"
        }
    }

    # Set keep-alive=0 for zero-idle resource usage
    $env:OLLAMA_KEEP_ALIVE = "0"
    try {
        [System.Environment]::SetEnvironmentVariable("OLLAMA_KEEP_ALIVE", "0", "User")
        Write-OK "OLLAMA_KEEP_ALIVE=0 set (models unload when idle)"
    } catch {
        Write-Warn "Could not set persistent OLLAMA_KEEP_ALIVE"
    }

    # Pull models
    $models = @("llama3.2", "deepseek-coder-v2:lite", "nomic-embed-text")
    foreach ($model in $models) {
        Write-Host "  Pulling $model..." -NoNewline
        try {
            $result = ollama pull $model 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host " done" -ForegroundColor Green
            } else {
                Write-Host " failed ($result)" -ForegroundColor Red
            }
        } catch {
            Write-Host " error ($_)" -ForegroundColor Red
        }
    }
} else {
    Write-OK "Skipped Ollama (--SkipOllama)"
}

# ────────────────────────────────────────────
# 3. Python virtual environment
# ────────────────────────────────────────────
Write-Step "Python virtual environment"

$venvPath = "$DataRoot\venv"
if (-not (Test-Path "$venvPath\Scripts\python.exe")) {
    Write-Host "  Creating venv at $venvPath..."
    python -m venv $venvPath
    Write-OK "Virtual environment created"
} else {
    Write-OK "Virtual environment already exists"
}

# Activate and install
$pip = "$venvPath\Scripts\pip.exe"
& $pip install --upgrade pip 2>&1 | Out-Null
Set-Location $ProjectRoot
& $pip install -e . 2>&1 | Out-Null
Write-OK "Python dependencies installed"

# ────────────────────────────────────────────
# 4. Environment configuration
# ────────────────────────────────────────────
Write-Step "Environment configuration"

# Copy .env.example → .env if not exists
$envFile = "$ProjectRoot\.env"
$envExample = "$ProjectRoot\config\.env.example"
if (-not (Test-Path $envFile)) {
    Copy-Item $envExample $envFile
    Write-OK ".env created from .env.example"
} else {
    Write-OK ".env already exists"
}

# Create data directories
$dirs = @("logs", "reports", "catalogs", "backups")
foreach ($dir in $dirs) {
    $path = "$DataRoot\$dir"
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Write-OK "Created $path"
    }
}
Write-OK "Data directories ready"

# ────────────────────────────────────────────
# 5. Scheduled tasks (optional)
# ────────────────────────────────────────────
if ($ScheduleTasks) {
    Write-Step "Scheduled tasks"

    $tasksDir = "$ProjectRoot\config\tasks"

    # Check admin — schtasks /create often needs it
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Warn "Task registration may require Administrator privileges"
        Write-Host "  Re-run: Start-Process powershell -Verb RunAs -Args '-File ""$PSCommandPath"" -ScheduleTasks'"
    }

    if (Test-Path $tasksDir) {
        $taskFiles = Get-ChildItem "$tasksDir\*.xml" -ErrorAction SilentlyContinue
        if ($taskFiles) {
            foreach ($taskFile in $taskFiles) {
                $taskName = "vansh-local-ai-stack\$($taskFile.BaseName)"
                try {
                    # Resolve env vars in XML (e.g. %USERDOMAIN%\%USERNAME%)
                    $xmlContent = Get-Content -LiteralPath $taskFile.FullName -Raw
                    $xmlContent = [System.Environment]::ExpandEnvironmentVariables($xmlContent)
                    $tempXml = [System.IO.Path]::GetTempFileName() + ".xml"
                    Set-Content -LiteralPath $tempXml -Value $xmlContent -Encoding UTF8
                    # Unregister if exists (ignore error if not)
                    schtasks /delete /tn $taskName /f 2>&1 | Out-Null
                    schtasks /create /xml $tempXml /tn $taskName /f 2>&1 | Out-Null
                    Remove-Item -LiteralPath $tempXml -Force -ErrorAction SilentlyContinue
                    if ($LASTEXITCODE -eq 0) {
                        Write-OK "Registered task: $taskName"
                    } else {
                        Write-Warn "Could not register task $taskName (try as Admin)"
                    }
                } catch {
                    Write-Warn "Could not register task $taskName (run as Admin?)"
                }
            }
        } else {
            Write-Warn "No task XML files found in $tasksDir"
        }
    } else {
        Write-Warn "Tasks directory not found: $tasksDir"
    }
} else {
    Write-OK "Scheduled tasks skipped (use -ScheduleTasks to enable)"
}

# ────────────────────────────────────────────
# 6. Verify
# ────────────────────────────────────────────
Write-Step "Verification"

$vls = "$venvPath\Scripts\vls.exe"
if (Test-Path $vls) {
    & $vls doctor
} else {
    Write-Warn "vls not found in venv - trying global install"
    try {
        vls doctor
    } catch {
        Write-Fail "vls CLI not available. Try: pip install -e ."
    }
}

Write-Host "`n" -NoNewline
Write-Host "======================================" -ForegroundColor Gray
Write-Host "  Setup complete" -ForegroundColor Green
Write-Host "  Next: run 'vls doctor' anytime" -ForegroundColor Cyan
Write-Host "  Docs: .\SETUP.md" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Gray
