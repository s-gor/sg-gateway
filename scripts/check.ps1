$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (Test-Path '.venv') {
    $Python = '.\.venv\Scripts\python.exe'
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $Python = 'py'
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $Python = 'python'
} else {
    throw 'Python was not found. Install Python or run scripts\test.ps1 first.'
}

Write-Host 'Checking Python syntax...'
& $Python -B -c "from pathlib import Path; files=list(Path('app').rglob('*.py'))+list(Path('engines').rglob('*.py'))+list(Path('tests').rglob('*.py'))+list(Path('hostd').rglob('*.py')); [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in files]; print(f'syntax ok: {len(files)} files')"

Write-Host 'Checking release manifest...'
& $Python -B -c "import json, pathlib; manifest=json.loads(pathlib.Path('release-manifest.json').read_text(encoding='utf-8')); version=pathlib.Path('VERSION').read_text(encoding='utf-8').strip(); assert manifest['version']==version; assert manifest['images']['panel']; assert manifest['images']['xray']; print('manifest ok')"

if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host 'Checking Docker Compose config...'
    docker compose config | Out-Null
} else {
    Write-Host 'Docker not found, skipping compose check.'
}

if (Test-Path '.venv') {
    Write-Host 'Running tests...'
    & $Python -m pytest
} else {
    Write-Host 'Virtual environment not found, skipping pytest. Run scripts\test.ps1 for full tests.'
}

Write-Host 'SG-Gateway checks completed.'