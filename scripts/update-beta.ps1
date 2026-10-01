$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'backup-before-update.ps1')
docker compose build --pull
if ($LASTEXITCODE -ne 0) { throw 'The updated application image could not be built. Existing containers and data remain available.' }
docker compose up -d
if ($LASTEXITCODE -ne 0) { throw 'The updated application did not start. Data volumes remain preserved; restore the previous application files and run Start NovelForge.cmd.' }
$ready = $false
for ($attempt = 1; $attempt -le 60; $attempt++) {
    try {
        $result = Invoke-RestMethod -Uri 'http://localhost:8000/health/ready' -TimeoutSec 3
        Invoke-WebRequest -Uri 'http://localhost:3000' -UseBasicParsing -TimeoutSec 3 | Out-Null
        if ($result.status -eq 'ready') { $ready = $true; break }
    } catch {
        Start-Sleep -Seconds 2
    }
}
if (-not $ready) {
    throw 'The update did not become ready within two minutes. Existing data volumes and downloaded pre-update backups were preserved.'
}
Write-Host 'NovelForge updated successfully. Your pre-update backups remain in NovelForge Update Backups.'
