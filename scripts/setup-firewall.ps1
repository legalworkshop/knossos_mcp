<#
  setup-firewall.ps1 — restrict the Knossos port to the client machine only.

  Knossos binds to 0.0.0.0, so without a firewall rule ANY device on the LAN that
  knows the token could connect. This script creates an inbound rule that allows the
  Knossos TCP port ONLY from the client machine's IP, and nothing else.

  Run in an ELEVATED (Administrator) PowerShell on the SERVER machine (Machine B).

  Examples:
    .\scripts\setup-firewall.ps1 -ClientIp 192.168.1.20
    .\scripts\setup-firewall.ps1 -ClientIp 192.168.1.20 -Port 8765
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, HelpMessage = "IPv4 of the client machine (Machine A) allowed to connect.")]
    [string]$ClientIp,

    [Parameter(HelpMessage = "TCP port Knossos listens on (must match KNOSSOS_PORT).")]
    [int]$Port = 8765,

    [string]$RuleName = "Knossos MCP (client only)"
)

$ErrorActionPreference = "Stop"

# Validate the IP.
[System.Net.IPAddress]$parsed = $null
if (-not [System.Net.IPAddress]::TryParse($ClientIp, [ref]$parsed)) {
    throw "ClientIp '$ClientIp' is not a valid IP address."
}

# Remove any previous rule with the same name (idempotent re-runs).
$existing = Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "[firewall] removing existing rule '$RuleName'..."
    $existing | Remove-NetFirewallRule
}

Write-Host "[firewall] allowing TCP $Port inbound from $ClientIp only..."
New-NetFirewallRule `
    -DisplayName $RuleName `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort $Port `
    -RemoteAddress $ClientIp | Out-Null

Write-Host "[firewall] done. Rule '$RuleName' active."
Write-Host "[firewall] Verify from the client with: Test-NetConnection <SERVER_IP> -Port $Port"
Write-Host "[firewall] NEVER port-forward this port on your router. Knossos is LAN-only."
