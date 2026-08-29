# NovelForge V2

NovelForge is a local-first Narrative Intelligence Platform for planning, writing, governing, analyzing, revising, and publishing long-form fiction.

The Paragraph Editor is feature-frozen. New product work builds on the shared Narrative Analysis Engine, which supplies Story Health, Canon Intelligence, Timeline Intelligence, Character Intelligence, Plot Threads, the Story Bible, the Knowledge Graph, critique, completeness, the Project Assistant, and the Workspace Companion.

## Product workflow

1. Create a project and define Story Vision.
2. Develop characters, world rules, relationships, chronology, and arcs.
3. Resolve guided completeness blockers until the project reaches Draft Ready.
4. Plan each scene, generate a protected Version A, review its goal, trouble,
   stakes, continuity, and next-scene handoff, then explore Version B/C or
   structured revision passes without replacing approved prose.
5. Compare, revise, and explicitly approve the selected scene version.
6. Review narrative evidence, editorial findings, canon proposals, and timeline warnings.
7. Assemble, validate, and approve a governed manuscript.
8. Run Publication Preflight and export Markdown, text, HTML, DOCX, EPUB, PDF, or a complete provenance package.

Project milestones are Concept Complete, World Ready, Draft Ready, Revision Ready, and Publication Ready. Every gate has explicit evidence and a direct destination.

## Architecture

- `backend/`: FastAPI, Motor/MongoDB, provider gateway, orchestration, governance, and the shared Narrative Analysis Engine.
- `frontend/`: Next.js 15 desktop application, Zustand state, author-facing intelligence workspaces, Project Assistant, and Workspace Companion.
- `e2e/`: Playwright workflows covering the product from project creation through story governance and publication.
- `docs/`: architecture and operating documentation.

Narrative subsystems consume one persisted analysis graph. Canon approval and structured user knowledge flow through the Story Bible and trigger downstream projections; AI output cannot silently change approved canon.

## Private-beta installation and startup

The supported author path on Windows requires Docker Desktop. Extract the beta
folder, start Docker Desktop, then double-click `Start NovelForge.cmd`. The
launcher checks Docker, starts the database and application in dependency order,
runs additive migrations, waits for readiness, and opens
`http://localhost:3000`. No Node.js, Python, MongoDB, or terminal knowledge is
required for this path.

- `Start NovelForge.cmd` — start or resume the local application.
- `Check NovelForge.cmd` — explain readiness problems in plain language.
- `Stop NovelForge.cmd` — stop services without deleting projects or backups.
- `Back Up Before Update.cmd` — download one verified editable-project archive per project.
- `Update NovelForge.cmd` — require pre-update backups, rebuild, migrate, and verify readiness.

Docker ports bind to `127.0.0.1`; this is a controlled local/private beta, not a
hosted multi-user service. Never use `docker compose down --volumes` unless you
explicitly intend to erase the local database and credential-key volume.

Developers may instead install Python 3.11, Node.js, MongoDB 7+, run
`py -3.11 -m pip install -r backend/requirements.txt`, `npm install`, and
`npm run dev`. The development launcher does not terminate processes occupying
its ports.

## Configuration

Copy `backend/.env.example` to `backend/.env`.

Important settings:

- `MONGODB_URL`, `DATABASE_NAME`
- `USE_MOCK_LLM` — keep `false` for real-provider validation
- `CORS_ORIGINS`, `TRUSTED_HOSTS`
- `LOCAL_ACCESS_TOKEN` — optional protection for a shared desktop
- `SETTINGS_KEY_FILE` or `SETTINGS_ENCRYPTION_KEY`
- `PUBLICATION_EXPORT_DIRECTORY`

If `LOCAL_ACCESS_TOKEN` is set, expose the same local-only value to the frontend as `NEXT_PUBLIC_NOVELFORGE_LOCAL_TOKEN`. This is a desktop boundary, not multi-user cloud authentication.

Provider credentials are entered in Settings, encrypted at rest, and redacted from normal API responses. The current validated Google path is Gemini 3.1 Flash Lite when configured through Google AI Studio.

On first launch, the home page reports project storage, data compatibility,
backup storage, publication storage, and AI availability separately. Existing
projects, manual editing, review, backup, and valid publication exports remain
available when Gemini is offline.

## Backup, privacy, and support

Project Settings contains **Project backup and recovery**. A project backup
contains editable planning, prose lineage, decisions, canon, Story Bible,
editorial/manuscript state, and rebuildable intelligence state. It does not
contain provider credentials. Restore always validates first and creates a
separate verified project copy; the original is never overwritten.

Global Settings provides **Back up all projects**, a privacy summary, sanitized
diagnostic bundles, and local private-beta feedback. Relevant bounded story
context leaves the machine only when the author starts an AI action; it is sent
to the configured provider. Diagnostic bundles omit prose, prompts, provider
responses, Story Bible content, notes, database connection strings, and secrets.

## Project lifecycle

- Archive hides a paused or completed project from Active without deleting it.
- Trash is recoverable.
- Permanent deletion is available only from Trash and requires typing the exact project title.
- Duplication can copy setup only or governed story content. Operational runs, provider traces, cached analysis, and notifications are not copied.

The legacy `DELETE /api/projects/{id}` endpoint remains for backward API compatibility; the product UI uses the recoverable Trash workflow.

## Testing

```powershell
npm run test:backend
npm run test:frontend
npm run build
npm run test:e2e
```

The release gate also includes a real Gemini inference check, project-database integrity audit, 500-chapter cold/cached benchmark, console review, desktop viewport coverage at 1366×768 through 2560×1440, accessibility checks, and publication artifact validation.

## Documentation

Start with:

- `docs/operations/RC9_PRIVATE_BETA_GUIDE.md`
- `docs/operations/RC9_BACKUP_RESTORE.md`
- `docs/operations/RC9_TROUBLESHOOTING.md`
- `docs/operations/RC9_UPGRADE.md`
- `docs/architecture/rc9-operational-hardening.md`
- `docs/api/rc9-operations-api.md`

- `RC7_IMPLEMENTATION_REPORT.md`
- `RC7_UX_AND_AMATEUR_AUTHOR_REPORT.md`
- `RC7_TEST_RESULTS.md`
- `RC7_KNOWN_LIMITATIONS.md`
- `RC7_PRODUCT_AUDIT_AND_IMPLEMENTATION_REPORT.md`
- `docs/architecture/rc7-writing-experience.md`
- `docs/workflows/rc7-writing-flow.md`
- `docs/api/rc7-writing-api.md`
- `POST_RC5_HARDENING_IMPLEMENTATION_PLAN.md`
- `RC5_COMPLETION_REPORT.md`
- `RC5_ARCHITECTURE_NOTES.md`
- `NOVELFORGE_COMPREHENSIVE_PRODUCT_AUDIT.md`

Phase and release reports remain at the repository root for historical traceability; new implementation documentation belongs in `docs/`.
