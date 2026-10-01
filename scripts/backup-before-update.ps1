param(
    [string]$Destination = (Join-Path (Get-Location) 'NovelForge Update Backups')
)
$ErrorActionPreference = 'Stop'
$resolvedDestination = [System.IO.Path]::GetFullPath($Destination)
New-Item -ItemType Directory -Force -Path $resolvedDestination | Out-Null

Write-Host "Creating pre-update project backups in $resolvedDestination"
$headers = @{}
if ($env:NOVELFORGE_LOCAL_ACCESS_TOKEN) {
    $headers['X-NovelForge-Token'] = $env:NOVELFORGE_LOCAL_ACCESS_TOKEN
}

$page = 1
$created = 0
do {
    $library = Invoke-RestMethod -Uri "http://localhost:8000/api/project-library?status=all&page=$page&page_size=100" -Headers $headers -TimeoutSec 30
    foreach ($project in $library.items) {
        if ($project.status -eq 'trashed') { continue }
        $backup = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/projects/$($project.id)/backups" -Headers $headers -ContentType 'application/json' -Body '{"reason":"before application update"}' -TimeoutSec 600
        $safeTitle = ($project.title -replace '[^a-zA-Z0-9._-]', '-').Trim('-')
        if (-not $safeTitle) { $safeTitle = 'project' }
        $output = Join-Path $resolvedDestination "$safeTitle-$($backup.backup_id.Substring(0,8)).novelforge-backup"
        Invoke-WebRequest -Uri "http://localhost:8000/api/backups/$($backup.backup_id)/download" -Headers $headers -OutFile $output -TimeoutSec 600
        $created++
        Write-Host "Backed up: $($project.title)"
    }
    $page++
} while ($library.has_next)

if ($created -eq 0) {
    Write-Host 'No active or archived projects required backup.'
} else {
    Write-Host "Verified and downloaded $created project backup(s). Do not update until these files are stored safely."
}

