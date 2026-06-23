<#
  add-to-startup.ps1 — make Knossos start automatically when you log in.

  Creates a shortcut to start-knossos.bat in your user Startup folder. Runs at login,
  no admin required, and is easy to undo (just delete the shortcut, or pass -Remove).

  Run on the SERVER machine (Machine B):
    .\scripts\add-to-startup.ps1
    .\scripts\add-to-startup.ps1 -Remove
#>
[CmdletBinding()]
param(
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$bat = Join-Path $root "start-knossos.bat"
$startup = [Environment]::GetFolderPath('Startup')
$lnk = Join-Path $startup "knossos.lnk"

if ($Remove) {
    if (Test-Path $lnk) {
        Remove-Item $lnk -Force
        Write-Host "[startup] removed: $lnk"
    } else {
        Write-Host "[startup] nothing to remove (no shortcut found)."
    }
    return
}

if (-not (Test-Path $bat)) {
    throw "start-knossos.bat not found at $bat"
}

$shell = New-Object -ComObject WScript.Shell
$sc = $shell.CreateShortcut($lnk)
$sc.TargetPath = $bat
$sc.WorkingDirectory = $root
$sc.WindowStyle = 7          # minimized
$sc.Description = "Knossos MCP server autostart"
$sc.Save()

if (Test-Path $lnk) {
    Write-Host "[startup] created: $lnk"
    Write-Host "[startup] Knossos will start at your next login. Undo with: -Remove"
} else {
    throw "Failed to create shortcut."
}
