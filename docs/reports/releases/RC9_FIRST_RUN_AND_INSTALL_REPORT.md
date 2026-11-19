# NovelForge V2 RC9 — First Run and Install Report

## Supported path

RC9 supports a local/private Windows beta using Docker Desktop. It is not a hosted service and does not claim multi-tenant security.

1. Install and start Docker Desktop.
2. Run `Start NovelForge.cmd` from the project folder.
3. On first use, NovelForge builds its local containers, creates persistent named volumes, runs additive migrations and waits for healthy services.
4. The browser opens at `http://127.0.0.1:3000` after readiness succeeds.
5. First Run shows database, storage and AI readiness separately. The author may create/open manual projects even before AI is configured.
6. Settings → AI Connections validates the key and chosen model. Settings → NovelForge readiness shows the current operating state.

`Stop NovelForge.cmd` stops services without deleting volumes. `Check NovelForge.cmd` reports service and readiness status. Normal launches reuse installed images; `Update NovelForge.cmd` deliberately performs backup-before-update, image rebuild, health wait and readiness verification.

## Live acceptance evidence

- A clean Docker volume started with project count 0, schema version 9 and `offline_ready` because AI was not configured inside that isolated package.
- First screen visibly explained: “Welcome — let’s get NovelForge ready,” kept Projects accessible, and identified AI setup as separate.
- The author created “The Lanterns Below” through the visible UI and reached the guided dashboard.
- Stop completed in 29.5 seconds. A subsequent packaged start completed in 63.7 seconds and retained all created projects.
- The first clean source build took 545.1 seconds on this Windows host; later backend-only rebuild used cache and completed in about 20 seconds.
- All five PowerShell launcher files parse with zero syntax errors; Docker Compose configuration validates.
- A live configured-Gemini check in the normal installation validated `gemini-3.1-flash-lite` in 7.8 seconds.

## Failure guidance

- Occupied ports cause a safe startup error; the launcher no longer terminates unrelated processes.
- Missing images trigger a one-time build with an explanation; normal start does not rebuild.
- Database outage produces a blocked readiness explanation and keeps the static frontend available.
- AI setup/outage produces `offline_ready`; existing/manual project work remains accessible.
- Backup/export folder failures report the affected operation and state that existing work is unchanged.
- Every API response carries a support reference for correlation.

## Upgrade and uninstall

The documented update path creates backups before persistent-record migration, then waits for migration and application readiness. Migration runs and lock ownership are durable and expired ownership can be recovered. Rollback instructions preserve volumes and use a compatible application image.

Uninstall instructions distinguish containers/images from named data volumes. Project databases and backup volumes are never removed incidentally; deleting them requires a separate explicit author decision.

## Assessment

The path is suitable for a technically assisted private beta, but it is not a consumer-native installer. Docker Desktop, adequate disk space and internet access for the first image build remain explicit conditions.
