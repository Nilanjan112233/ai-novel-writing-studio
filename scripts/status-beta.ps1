$ErrorActionPreference = 'Continue'
Write-Host 'NovelForge Private Beta status'
docker compose ps
try {
    $readiness = Invoke-RestMethod -Uri 'http://localhost:8000/api/operations/readiness' -TimeoutSec 5
    Write-Host ("Application: {0} ({1})" -f $readiness.status, $readiness.app_version)
    Write-Host $readiness.summary
    foreach ($entry in $readiness.checks.PSObject.Properties) {
        Write-Host (" - {0}: {1} - {2}" -f $entry.Name, $entry.Value.status, $entry.Value.explanation)
    }
} catch {
    Write-Warning 'NovelForge is not reachable. Run Start NovelForge.cmd. Existing Docker data has not been changed.'
    exit 1
}
