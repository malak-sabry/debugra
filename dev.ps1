# Debugra — Windows dev helper (PowerShell)
# Usage: .\dev.ps1 [orchestrator|dashboard|lms|shop|all]
param(
    [ValidateSet("orchestrator","dashboard","lms","shop","all","test","lint")]
    [string]$Target = "all"
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$VenvPy = "$Root\.venv\Scripts\python.exe"

function Require-Venv {
    if (-not (Test-Path $VenvPy)) {
        Write-Error ".venv not found. Run: uv sync --all-packages"
        exit 1
    }
}

function Start-Orchestrator {
    Require-Venv
    Write-Host "[orchestrator] starting on :8000" -ForegroundColor Cyan
    Push-Location "$Root\apps\orchestrator"
    & $VenvPy -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
    Pop-Location
}

function Start-Dashboard {
    Write-Host "[dashboard] starting on :3000" -ForegroundColor Cyan
    Push-Location "$Root"
    pnpm --filter dashboard dev
    Pop-Location
}

function Start-LMS {
    Write-Host "[lms] starting frontend on :3001, backend on :8001" -ForegroundColor Green
    Push-Location "$Root\suts\lms\frontend"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "pnpm dev"
    Pop-Location
    Require-Venv
    Push-Location "$Root\suts\lms\backend"
    & $VenvPy -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
    Pop-Location
}

function Start-Shop {
    Write-Host "[shop] starting frontend on :3002, backend on :8002" -ForegroundColor Yellow
    Push-Location "$Root\suts\shop\frontend"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "pnpm dev"
    Pop-Location
    Require-Venv
    Push-Location "$Root\suts\shop\backend"
    & $VenvPy -m uvicorn main:app --reload --host 0.0.0.0 --port 8002
    Pop-Location
}

switch ($Target) {
    "orchestrator" { Start-Orchestrator }
    "dashboard"    { Start-Dashboard }
    "lms"          { Start-LMS }
    "shop"         { Start-Shop }
    "test" {
        Require-Venv
        Write-Host "[test] running pytest..." -ForegroundColor Magenta
        & $VenvPy -m pytest apps/orchestrator/tests apps/agent-runner/tests -v
        Write-Host "[test] running tsc..." -ForegroundColor Magenta
        pnpm --filter dashboard exec tsc --noEmit
        pnpm --filter lms-frontend exec tsc --noEmit
        pnpm --filter shop-frontend exec tsc --noEmit
    }
    "lint" {
        Require-Venv
        & $VenvPy -m ruff check apps/orchestrator apps/agent-runner packages/schemas suts
        pnpm --recursive lint
    }
    "all" {
        Write-Host "[all] Starting dashboard + orchestrator..." -ForegroundColor White
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root'; pnpm --filter dashboard dev"
        Start-Orchestrator
    }
}
