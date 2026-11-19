$ErrorActionPreference = 'Stop'

Write-Host 'NovelForge Private Beta - Starting safely'
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Error 'Docker Desktop is not running. Start Docker Desktop, wait until it is ready, then run this command again. Your NovelForge data has not been changed.'
}

docker compose up -d --no-build
if ($LASTEXITCODE -ne 0) {
    Write-Host 'NovelForge is not installed yet. Building the private beta once; this can take several minutes.'
    docker compose build
    if ($LASTEXITCODE -ne 0) {
        throw 'NovelForge could not be installed. Existing Docker volumes were preserved. Check your internet connection and available disk space, then retry.'
    }

    docker compose up -d --no-build
    if ($LASTEXITCODE -ne 0) {
        throw 'NovelForge was installed but could not start. Existing Docker volumes were preserved. Run scripts/windows/check-novelforge.cmd for details.'
    }
}

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
    docker compose ps
    throw 'NovelForge did not become ready within two minutes. Your data volumes remain intact. Review docker compose logs and retry.'
}

Write-Host 'NovelForge is ready at http://localhost:3000'
Start-Process 'http://localhost:3000'
