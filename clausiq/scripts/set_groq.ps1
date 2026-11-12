# Set the Groq API key by writing it into the project .env file.
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot ".env"

$key = Read-Host "Paste your Groq API key (starts with gsk_)"
if (-not $key.StartsWith("gsk_")) {
    Write-Host "That doesn't look like a Groq key. Aborting." -ForegroundColor Yellow
    exit 1
}

$content = "GROQ_API_KEY=$key`nGROQ_MODEL=llama-3.3-70b-versatile`n"
Set-Content -LiteralPath $envPath -Value $content -Encoding utf8
Write-Host "Key saved to $envPath" -ForegroundColor Green
Write-Host "Restart the server (python run.py) to pick it up."
