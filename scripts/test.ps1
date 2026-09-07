$ErrorActionPreference = "Stop"
Push-Location "$PSScriptRoot/../backend"
try {
    uv run pytest
    uv run ruff check .
    uv run mypy app tests
} finally {
    Pop-Location
}

Push-Location "$PSScriptRoot/../frontend"
try {
    npm run lint
    npm run typecheck
    npm run build
} finally {
    Pop-Location
}

