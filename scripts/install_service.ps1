# Install Knossos as a Windows service via NSSM (optional, starts on boot).
# Requires nssm (https://nssm.cc) on PATH. Run this in an elevated (Administrator) shell.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"
$svc = "KnossosMCP"

if (-not (Test-Path $py)) {
    throw "venv not found. Run scripts\run.ps1 once first to create it and install deps."
}
if (-not (Get-Command nssm -ErrorAction SilentlyContinue)) {
    throw "nssm not found on PATH. Install from https://nssm.cc and retry."
}

New-Item -ItemType Directory -Force (Join-Path $root "logs") | Out-Null

nssm install $svc $py "-m" "knossos.server"
nssm set $svc AppDirectory $root
nssm set $svc AppStdout (Join-Path $root "logs\knossos.out.log")
nssm set $svc AppStderr (Join-Path $root "logs\knossos.err.log")
nssm set $svc Start SERVICE_AUTO_START

Write-Host "Installed service '$svc'."
Write-Host "Start:   nssm start $svc"
Write-Host "Stop:    nssm stop $svc"
Write-Host "Remove:  nssm remove $svc confirm"
