param(
    [string]$LlamaCppDirectory = "$PSScriptRoot\..\llama.cpp",
    [string]$ModelPath = "$PSScriptRoot\..\models\nova-assistant.gguf"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..").Path
$server = Join-Path $LlamaCppDirectory "llama-server.exe"
if (-not (Test-Path $server)) { throw "llama-server.exe not found at $server" }
if (-not (Test-Path $ModelPath)) { throw "GGUF model not found at $ModelPath" }

Write-Host "Starting Nova's local GGUF server on 127.0.0.1:8080"
& $server -m $ModelPath --host 127.0.0.1 --port 8080 -c 4096
