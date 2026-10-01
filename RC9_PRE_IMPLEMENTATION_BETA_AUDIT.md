# NovelForge V2 RC9 — Pre-Implementation Private Beta Audit

Date: 2026-08-02  
Scope: local/private desktop-style beta only  
Decision at audit entry: **NO-GO for unmanaged private-beta distribution**

## Purpose and method

This report is the mandatory operational audit that precedes RC9 implementation. It does not propose a new product architecture. It evaluates the current RC8 application as an author would receive, start, operate, recover, update, and support it.

Evidence was gathered from the current source, architecture and RC8 reports, existing backend/frontend/Playwright tests, the live Windows host, MongoDB configuration, startup and health scripts, provider settings, project lifecycle services, migrations, publication exports, and the frozen Paragraph Editor recovery behavior. Secrets were inspected only as configured/not configured; no credential values were printed or copied.

## Current operational answers

| Author/operator question | Current RC8 answer | Evidence status |
|---|---|---|
| How is NovelForge installed? | Clone/copy the repository, install Python 3.11, Node.js, MongoDB 7+, Python packages, npm packages, and Playwright Chromium. Docker Compose exists but is development-oriented. | Verified in `README.md`, `package.json`, Dockerfiles and `docker-compose.yml`. |
| How is it started? | `npm run dev` starts a reload-enabled FastAPI process and a Next.js development server. MongoDB must already be running. | Verified in `scripts/dev.ts`; live services were stopped while MongoDB was running. |
| How is it stopped or restarted? | Press Ctrl+C in the launcher terminal. There is no author-facing stop, restart, or status workflow. | Verified in `scripts/dev.ts`. |
| What happens when ports are occupied? | The development launcher discovers and forcibly terminates the process using ports 3000/8000. It does not establish that NovelForge owns that process. | Verified in `scripts/dev.ts`; this is unsafe for a commercial beta launcher. |
| What happens when MongoDB is unavailable? | Backend startup fails or readiness fails. The existing health command produces technical output and may display a blank connection error. There is no author-facing recovery path. | Verified by source and `npm run health` with frontend/backend stopped. |
| How is Gemini configured? | Settings provides encrypted API-key storage, key validation, model discovery and a selected-model test. Gemini `gemini-3.1-flash-lite` is currently configured in this installation. | Verified in Settings services/UI and configuration metadata without exposing the key. |
| Can the author verify AI readiness? | Yes, from the advanced provider settings flow. There is no simple first-launch readiness summary connecting configuration, database, storage and AI status. | Verified in Settings UI and `/health/ready`. |
| Where is story data stored? | In the configured local MongoDB database (`novelforge` by default). Publication files use the configured export directory (`./exports` by default). | Verified in backend configuration and current environment. |
| How is a project backed up? | It is not. Publication export protects a finished manuscript, not editable project state. | Verified by service/API/test search. |
| How is a backup restored? | There is no project backup import, validation, preview, restore-as-copy, replacement, or restore verification workflow. Project trash restoration is unrelated. | Verified by project lifecycle and API search. |
| What survives a browser or app crash? | Server-confirmed data survives. The frozen Paragraph Editor also keeps unsaved paragraph recovery data in browser storage. Other project state has no general recovery checkpoint. | Verified in Paragraph Editor save/recovery implementation and lifecycle services. |
| What happens to a running background task after restart? | Narrative-analysis jobs marked running are re-queued at startup. Equivalent recovery is not demonstrated for every write/generation workflow. | Verified in FastAPI lifespan startup code. |
| What happens when Gemini is unavailable? | Existing database-backed content should remain readable; provider operations fail through existing author-facing operation failures. There is no explicit AI-offline readiness mode, and this behavior has not been operationally tested across all primary workspaces. | Source-supported, runtime verification pending. |
| What happens when disk space is exhausted? | There is no disk-space readiness check, backup/export capacity check, or dedicated author guidance. | Verified by configuration, readiness endpoint and health script. |
| What happens when a database write fails? | Paragraph saving does not claim success and retains local recovery content. A comprehensive operational failure test across planning, canon, revision, backup and publication does not exist. | Paragraph behavior verified; broader coverage missing. |
| How are updates applied? | Database migrations run automatically and sequentially during backend startup. There is no pre-upgrade backup, migration journal/lock, explicit failed-upgrade state, or documented rollback procedure. | Verified in `backend/app/core/database.py` and migration modules. |
| Are old projects supported? | Additive/idempotent migrations and compatibility normalization exist, but there is no supported version metadata on projects/backups and no RC9 upgrade fixture matrix for pre-RC6, RC6, RC7 and RC8 data. | Verified in migrations/tests. |
| Can an existing approved manuscript be exported with AI offline? | The export implementation is database/file based and does not call a provider, but an explicit AI-offline acceptance test is absent. | Verified by `publication_service.py`; runtime test pending. |
| How does an author report a bug? | There is no in-app beta feedback flow, diagnostic bundle, or documented support reference workflow. | Verified by UI/API/service/test search. |
| What diagnostic information can be shared safely? | No dedicated sanitized support bundle exists. Normal logs may contain technical provider response content, and one legacy Gemini client places the key in a URL query parameter. | Verified in provider gateway and legacy LLM service source. |

## What is already dependable and must be preserved

- The Narrative Analysis Engine, shared narrative graph, Story Bible authority, Canon Governance, provider gateway, Workspace Bootstrap, and current agent roster are coherent and frozen.
- RC8’s operation-failure banner, request identity, atomic idempotency, Writer’s Room author-control invariant, chronology enforcement, reference reconciliation, and semantic-finding deduplication are established product promises.
- Provider credentials are encrypted at rest and redacted from public Settings responses.
- Project trash/restore and guarded purge provide recoverable deletion in the UI.
- The Paragraph Editor correctly distinguishes pending, saved, offline and failed save states and retains local paragraph recovery data. RC9 must not duplicate or redesign this behavior.
- Publication export creates deterministic downloadable formats and checksums for approved manuscripts.
- Narrative-analysis jobs have startup recovery.
- Dedicated Playwright database handling and exact project cleanup already exist.

## Critical findings

### C1 — Editable projects have no backup and restore contract

**Problem:** NovelForge has no backup format or restore workflow for the editable project, including plans, drafts, versions, decisions, canon, Story Bible, timelines, relationships, analyses and approvals.

**Evidence:** No project backup service, API, UI or test exists. Project lifecycle restore only reverses trash. Publication export contains manuscript output rather than authoritative project state.

**Why it matters:** Local MongoDB is a single point of failure. A disk failure, accidental database removal, corrupt update, or machine replacement can destroy months of author work. A private beta cannot ask authors to trust long-form work without a recoverable copy.

**Required bounded correction:** Add an application-owned, versioned, checksummed project backup; validation and preview; safe restore-as-copy; explicit conflict handling; post-restore integrity verification; clear distinction from publication export; retention and destination documentation.

**Estimated effort:** Large.  
**Expected user impact:** Essential data-safety promise.

### C2 — Upgrades mutate the live database without a recoverable upgrade boundary

**Problem:** Migrations run automatically during startup but lack a durable migration journal/lock, backup gate, recovery instructions and explicit failed-upgrade state.

**Evidence:** `Database.connect()` establishes the client and runs every migration sequentially. Individual migrations use markers and mostly idempotent operations, but the chain is not transactional and project records do not declare their originating schema/app version.

**Why it matters:** A crash or incompatible change during an update can leave the author unsure whether the application and project data are safe. Restarting blindly may compound the problem.

**Required bounded correction:** Add release/schema metadata, migration execution records, compatibility checks, failure reporting and a documented backup-before-update/rollback path. Do not redesign MongoDB or existing migrations.

**Estimated effort:** Medium to large.  
**Expected user impact:** Prevents upgrade-related trust loss and data damage.

## High findings

### H1 — There is no supported author-grade install/start/stop package

**Problem:** The primary launcher is a development orchestrator with hot reload, prerequisite knowledge and terminal output.

**Evidence:** `npm run dev` starts uvicorn with `--reload`, assumes MongoDB is already available and forcibly terminates any process on its preferred ports. Docker Compose bind-mounts backend source and defaults to mock AI.

**Why it matters:** A first-time private-beta author cannot safely distinguish a healthy launch from a developer setup failure. Killing unrelated processes is unacceptable behavior for a commercial launcher.

**Required bounded correction:** Define one supported private-beta deployment, provide non-destructive start/stop/status scripts, startup readiness checks, a clean-install checklist and safe failure messages. Keep developer commands available separately.

**Estimated effort:** Medium.  
**Expected user impact:** High; directly determines whether the product can be used at all.

### H2 — First launch has no unified readiness and recovery experience

**Problem:** Database, migrations, writable storage and provider readiness are separate technical concerns, not one understandable status.

**Evidence:** `/health/ready` only pings MongoDB. `scripts/health-check.ts` checks Mongo/backend/frontend but not migrations, storage, backups or provider configuration. Settings exposes detailed provider controls but no guided first-launch state.

**Why it matters:** Authors cannot tell whether they are ready to write, ready only for offline work, or blocked—and they do not know the next corrective action.

**Required bounded correction:** Extend existing Settings/readiness patterns with author-language states for database, storage, migrations, AI configuration and AI test status. Existing content must remain accessible when only AI is unavailable.

**Estimated effort:** Medium.  
**Expected user impact:** High onboarding and support reduction.

### H3 — Support diagnostics are absent and current logging is not safe enough to share

**Problem:** There is no sanitized support bundle, stable support reference or privacy-preserving diagnostic export.

**Evidence:** Provider status/error body fragments are logged. The legacy Gemini client constructs a request URL containing `?key=...`, which can be emitted by HTTP client logs. Operation failures expose useful author text but not a durable support reference.

**Why it matters:** Authors either cannot provide enough evidence for support or may accidentally share credentials/story content. Operators cannot efficiently trace a failure across UI, API, provider, validation and persistence.

**Required bounded correction:** Remove credentials from URLs, sanitize provider logging, carry correlation references to the UI, and produce an explicit diagnostic bundle containing versions, readiness, migration state and redacted operation outcomes—never story content or API keys by default.

**Estimated effort:** Medium.  
**Expected user impact:** High trust, privacy and supportability improvement.

### H4 — Restore cannot be validated, previewed or made non-destructive

**Problem:** Because project restore does not exist, there is also no contract for corrupt files, duplicate IDs, partial archives, newer schemas or name conflicts.

**Evidence:** No corresponding service/API/UI/tests were found.

**Why it matters:** A backup feature without safe restore semantics gives false confidence. Restore is the proof that a backup is useful.

**Required bounded correction:** Validate before writing, show project/version/count preview, restore as a new project by default, roll back partial inserts on failure, preserve the original, and run database integrity checks after restore.

**Estimated effort:** Included with C1.  
**Expected user impact:** Essential recovery assurance.

### H5 — Recovery is not defined consistently across operations

**Problem:** Analysis jobs recover on startup and paragraphs have local recovery, but provider generation, canon approval, revision, chapter assembly and export do not share an explicit crash/restart contract.

**Evidence:** Startup only calls narrative-analysis job recovery. Existing tests cover RC8 request safety and visible failures, not process interruption during each long-running operation.

**Why it matters:** After a crash, an author may not know whether an operation completed, failed, or duplicated, even if idempotency protects some requests.

**Required bounded correction:** Document operation state boundaries, expose incomplete/recoverable state, retain request/correlation identity, and add restart/retry tests using current stores and idempotency mechanisms.

**Estimated effort:** Medium.  
**Expected user impact:** High confidence during real writing sessions.

### H6 — Version and schema compatibility are implicit

**Problem:** There is no single application version/schema compatibility model visible in readiness, projects, backups or support diagnostics.

**Evidence:** Root packages report `1.0.0`; the product is called NovelForge V2 RC8. Migrations store independent phase markers, while project records do not carry a schema version.

**Why it matters:** Support cannot reliably answer which release created a backup or whether it is safe to open. Upgrade defects are harder to reproduce.

**Required bounded correction:** Add non-breaking app/schema metadata and compatibility checks at backup/restore and readiness boundaries; preserve all current documents and APIs.

**Estimated effort:** Small to medium.  
**Expected user impact:** High operational clarity.

### H7 — AI-offline behavior is implicit rather than a tested product mode

**Problem:** Reads and local export appear provider-independent, but the UI does not clearly distinguish “your work is available” from “AI is temporarily unavailable.”

**Evidence:** Existing provider failure handling is operation-specific; no end-to-end test opens, edits, saves and exports an existing project while Gemini is unavailable.

**Why it matters:** A provider outage should not make an author fear the project is broken or data is inaccessible.

**Required bounded correction:** Add a visible, non-blocking AI status; preserve non-AI workflows; provide retry/setup actions; and test existing-work access and export with provider failure.

**Estimated effort:** Medium.  
**Expected user impact:** High resilience and trust.

### H8 — The Docker path is not a beta distribution contract

**Problem:** Compose currently enables mock AI, mounts source into the backend container, lacks readiness dependencies, backup storage and update/rollback guidance.

**Evidence:** Verified in `docker-compose.yml` and Dockerfiles; backend container Python version also differs from the locally validated version.

**Why it matters:** Calling this a release package would misrepresent a development environment as a supported product install.

**Required bounded correction:** Harden the existing Compose path or explicitly exclude it and document another supported path. Do not claim an installer that was not tested.

**Estimated effort:** Medium.  
**Expected user impact:** High for onboarding and reproducibility.

## Medium findings

### M1 — Provider setup is capable but too technical for first run

The UI supports validation, discovery and testing, but begins with a multi-provider configuration grid. A novice needs a short Gemini path: enter key, validate, select recommended model, run a safe test, understand that the key is encrypted locally, and continue. **Effort:** Small to medium. **Impact:** High for first-use success.

### M2 — No backup destination, capacity, retention or age visibility

There is no default protected backup location, disk-space probe, last-successful-backup status, backup rotation, or stale-backup warning. **Effort:** Medium. **Impact:** High after C1 is implemented.

### M3 — Publication export can be mistaken for project backup

Export is a manuscript delivery feature and omits editable planning/analysis state. The distinction is not currently needed in UI because backup is absent, but RC9 must label both unambiguously. **Effort:** Small. **Impact:** Medium trust improvement.

### M4 — No privacy/data-flow explanation at the point of provider use

The product does not clearly state which story context leaves the machine, which provider receives it, what remains local, and how to remove stored credentials. **Effort:** Small to medium. **Impact:** High informed-consent improvement.

### M5 — No private-beta feedback loop

There is no local feedback record with optional diagnostics and explicit story-content consent. **Effort:** Medium. **Impact:** Medium; necessary to learn safely during beta.

### M6 — Long-session memory and staged-readiness claims are incomplete

RC8 measured large-project latency but did not record process working-set memory. There is no multi-day restart/recovery test or repeatable leak benchmark. **Effort:** Medium. **Impact:** Medium operational confidence.

### M7 — Runtime/dependency warnings remain noisy

RC8 reported 66 Pydantic/LangGraph warnings and a roughly 373 kB first-load bundle. They are not launch blockers, but warning noise can conceal real upgrade problems. **Effort:** Medium. **Impact:** Low to medium engineering confidence.

### M8 — The normal database contains substantial legacy/test clutter

The current default database contains 2,657 projects. Dedicated E2E isolation prevents new Playwright pollution, but legacy clutter complicates human beta evaluation and performance interpretation. Cleanup must be deliberate and exact; no bulk deletion is authorized. **Effort:** Operational. **Impact:** Medium test confidence.

### M9 — The legacy permanent-delete API remains easy to misuse outside the UI

The current UI uses trash and guarded purge, while the compatibility DELETE endpoint permanently purges. Removing it would break compatibility, so RC9 should document/deprecate and ensure ordinary UI never calls it. **Effort:** Small. **Impact:** Medium API safety.

### M10 — Health output is technical and incomplete

The CLI health check can show an empty error after a refused connection and does not explain author impact or recovery. **Effort:** Small. **Impact:** Medium support reduction.

## Low findings

- Installation and architecture references still emphasize earlier RC phases and development commands rather than a beta operator lifecycle.
- The default encryption-key and export locations are not surfaced clearly in the application.
- The Docker backend runtime and the documented local Python runtime are not aligned.
- There is no explicit uninstall/data-retention guide.
- There is no single “copy support reference” control on failures.

## Existing test coverage versus RC9 needs

Current tests prove many narrative and RC8 invariants, phase migration idempotency, trash restoration, paragraph version restoration, provider settings controls, publication export, reload persistence and exact E2E cleanup. They do **not** yet prove:

- backup completeness, checksum validation, corruption rejection and restore integrity;
- restore-as-copy conflict safety and rollback after partial failure;
- first-launch and clean-install readiness;
- database unavailable/read-only/disk-full author behavior;
- app restart during long operations;
- migration failure recovery and old-project version fixtures;
- AI-offline access/edit/save/export;
- diagnostic bundle redaction;
- API-key absence from URLs/logs/bundles;
- multi-hour/multi-day memory stability;
- update/rollback/uninstall procedures.

## Implementation boundary for RC9

RC9 should extend current operational seams only:

1. Add versioned backup/restore and integrity verification around existing project-owned collections.
2. Add application/schema metadata and migration outcome records around the existing migration runner.
3. Expand current readiness/Settings surfaces into a beginner-friendly first-run and operational status experience.
4. Add correlation references, redacted diagnostics and privacy guidance around existing error/provider layers.
5. Harden the existing local/Docker startup path and document one supported private-beta lifecycle.
6. Add local beta feedback with explicit diagnostic/story-content consent.
7. Validate restart, offline, upgrade and long-session behavior without changing narrative architecture.

It must not add an agent, analysis graph, writing pipeline, database authority, or Paragraph Editor capability.

## Pre-implementation gate decision

**NO-GO for unmanaged private-beta distribution in the current RC8 operational form.**

The narrative product is sufficiently mature to harden in place. The blockers are operational rather than architectural: lack of recoverable backups, unsafe/implicit update behavior, developer-only startup, absent first-run readiness, and insufficiently safe support diagnostics. These are bounded corrections. If the Critical and High items above are implemented and demonstrated through real restore, restart, provider-offline and clean-start tests, NovelForge can credibly progress to a managed private beta without redesigning its frozen narrative systems.
