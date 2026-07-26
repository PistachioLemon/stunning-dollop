$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python 3.11 or newer is required. Install it from python.org, then run this again."
}

py -3 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt

if (-not (Test-Path config.yaml)) {
    Copy-Item config.example.yaml config.yaml
}

& .\.venv\Scripts\python.exe run.py --check
Write-Host "Nova PC installed. Double-click Start-Nova-PC.bat." -ForegroundColor Green
