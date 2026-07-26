$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sandboxData = Join-Path $projectRoot "sandbox-data"

if (Test-Path $sandboxData) {
    Remove-Item -LiteralPath $sandboxData -Recurse -Force
}

New-Item -ItemType Directory -Path $sandboxData -Force | Out-Null
Write-Host "Nova Protected Sandbox reset. No production data was touched." -ForegroundColor Green
