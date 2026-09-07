$ErrorActionPreference = "Stop"
Push-Location "$PSScriptRoot/../backend"
try {
    uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
} finally {
    Pop-Location
}

