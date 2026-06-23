# Knossos MCP — start script (Machine B).
# Creates the venv (first run), installs the package, then launches the server.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".venv")) {
    Write-Host "[knossos] creating virtualenv (.venv)..."
    python -m venv .venv
}

$py = Join-Path $root ".venv\Scripts\python.exe"
& $py -m pip install --quiet --upgrade pip
& $py -m pip install --quiet -e .

if (-not (Test-Path ".env")) {
    Write-Warning "No .env found. Copy .env.example to .env and set KNOSSOS_TOKEN + KNOSSOS_ALLOWED_DIRS."
    exit 1
}

& $py -m knossos.server
