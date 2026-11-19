# NovelForge V2 RC9 — Implementation Report

Date: 2026-08-03  
Supported deployment: local/private desktop-style beta  
Release character: operational hardening; no narrative feature or architecture expansion

## Outcome

RC9 closes the two pre-implementation critical findings: editable projects now have a portable recovery contract, and updates now have a durable, observable migration boundary with an explicit backup-before-update path. It also replaces the development-only operating path with guarded local launchers, unified readiness, privacy-safe diagnostics and a beta feedback path.

No agent, narrative graph, writing pipeline, database authority or Paragraph Editor capability was added or redesigned.

## Delivered corrections

### Author data safety

- Project and all-project backup actions create versioned, checksummed ZIP archives containing Extended JSON NDJSON records from the existing authoritative project-owned collections.
- Backups include project metadata, planning, decisions, characters, world data, relationships, timeline, canon, Story Bible, drafts, paragraphs, versions, revisions, editorial/manuscript state and rebuildable analysis records.
- Provider credentials, global provider configuration and external publication files are excluded.
- Restore follows validate, preview, restore-as-copy and post-restore database-integrity verification. Existing projects are never overwritten.
- A failed restore rolls back only the incomplete copy. Retried or concurrent identical restore requests reuse one operation and one restored project.
- Downloaded archives can be imported after local backup metadata is lost.
- Pre-update backup is available from `Back Up Before Update.cmd`; retained backups are bounded to ten per project.

### Operational readiness and recovery

- The unified readiness endpoint distinguishes database, data-version, backup-storage, export-storage and AI status.
- Existing/manual work remains explicitly available when AI is unconfigured or unavailable.
- A packaged MongoDB outage now returns an author-language blocked result in 5.09 seconds while the frontend remains available, then returns to `offline_ready` after recovery without losing projects.
- API failures carry a correlation/reference ID. Ordinary UI explanations do not expose stack traces, UUIDs or credentials.
- Provider transport no longer places Gemini keys in request URLs and no longer logs raw provider response bodies.

### Install, startup and update

- Root Windows launchers provide Start, Stop, Check, Back Up Before Update and Update actions.
- Docker Compose binds author-facing ports to localhost, keeps MongoDB on its private Docker network, persists project and secret data in named volumes, and uses health-based service ordering.
- Normal startup reuses installed images. A build occurs only on first install or update.
- Startup uses durable migration runs and an expiring migration lease. Failed/abandoned migration state is observable and recoverable.
- Application version `2.0.0-rc9` and schema version `9` are visible through readiness and recorded on projects/backups.

### First run, privacy and support

- First run explains local readiness, AI readiness and the next action without blocking manual project access.
- Settings includes readiness, local storage locations, AI data-flow disclosure, back up all projects, sanitized support bundle export and categorized beta feedback.
- Support bundles include version, readiness, migration and redacted operational outcomes; they exclude story prose, prompts, provider responses, database URLs and credentials.
- Feedback remains local/exportable and diagnostics are opt-in. Story content is never attached.

### Performance and maintenance

- Story Bible persistence uses bounded bulk writes without changing authority or output shape.
- Workspace bootstrap benchmarks now report cold/warm time and working-set memory for 50–1,000 chapters.
- Frontend/runtime dependencies were updated within compatible ranges. Both npm audit scopes report zero known vulnerabilities.
- Google-hosted build fonts were removed, Docker build context was bounded and dependency versions were pinned for reproducible packaging.

## Documentation

- `README.md` is the private-beta entry point.
- `docs/operations/RC9_PRIVATE_BETA_GUIDE.md`
- `docs/operations/RC9_BACKUP_RESTORE.md`
- `docs/operations/RC9_TROUBLESHOOTING.md`
- `docs/operations/RC9_UPGRADE.md`
- `docs/api/rc9-operations-api.md`
- `docs/architecture/rc9-operational-hardening.md`

## Release decision

**PRIVATE BETA — CONDITIONAL GO**

The author-data, failure-recovery, offline-access and privacy promises are demonstrated. Conditions are operational rather than hidden product defects: distribution remains a local Docker Desktop beta, first installation requires internet access and can take several minutes, hosted/multi-tenant use is unsupported, and authors must copy important backup archives off the same computer for protection from complete machine loss.
