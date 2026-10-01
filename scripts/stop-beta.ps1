$ErrorActionPreference = 'Stop'
Write-Host 'Stopping NovelForge while preserving projects, credentials, backups, and exports...'
docker compose stop
if ($LASTEXITCODE -ne 0) { throw 'NovelForge could not be stopped cleanly. Check Docker Desktop. No data volumes were removed.' }
Write-Host 'NovelForge stopped. Your data remains in Docker volumes.'

