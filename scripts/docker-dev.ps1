$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build panel