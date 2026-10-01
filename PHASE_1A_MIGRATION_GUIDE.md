# NovelForge Narrative Studio V2 - Phase 1A Migration Guide

Migration date: 2026-06-13

The Phase 1A migration is idempotent and also runs during backend startup.
Running the standalone script first is recommended because it produces a clear
migration result before application traffic resumes.

## Prerequisites

1. Back up the NovelForge MongoDB database.
2. Stop background cycle execution.
3. Install backend dependencies:

```powershell
cd backend
py -3.11 -m pip install -r requirements.txt
```

4. Configure a stable Fernet key in the deployment secret manager:

```powershell
py -3.11 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
$env:SETTINGS_ENCRYPTION_KEY="<generated-key>"
```

Use the same key for every process and every future deployment. Local
development can use the generated key file fallback, but production should
always provide `SETTINGS_ENCRYPTION_KEY`.

## Run The Migration

From the backend directory:

```powershell
py -3.11 scripts\run_phase_1a_migration.py
```

The script:

- Removes duplicate Story Bible records before installing the unique index.
- Encrypts existing plaintext provider credentials.
- Adds `source_version` and `active` to legacy memory embeddings.
- Retains the current memory source and one inactive predecessor.
- Installs all Phase 1A indexes.
- Records migration state in the existing settings collection.

It adds only:

- `orchestration_plans`
- `orchestration_tasks`

## Expected Verification

A repeat run should be safe and should resemble:

```json
{
  "story_bibles_deleted": 0,
  "provider_secrets_migrated": 0,
  "memory": {
    "normalized": 0,
    "deleted": 0,
    "skipped": true
  },
  "indexes_installed": true
}
```

Start the application, then verify:

```powershell
npm run health
npm run test:backend
npm run test:frontend
npm run build
npm run test:e2e
```

Operational checks:

- `GET /api/settings/ai` returns `configured: true` for configured providers.
- No API response contains the stored key.
- `/api/projects/{project_id}/orchestration/latest` returns a persisted plan.
- Every plan has 12 task records with an execution or skip reason.
- A no-op cycle selects no agents and reports `NO_CHANGE_TERMINATION`.
- Execution traces report the configured provider request limit.

## Deployment Order

1. Back up MongoDB.
2. Install the new backend dependencies.
3. Provide `SETTINGS_ENCRYPTION_KEY`.
4. Run the standalone migration.
5. Deploy backend and frontend together.
6. Run health, API, and no-op orchestration checks.
7. Monitor failed plans, limiter waits, retry counts, and budget stop reasons.

## Rollback Plan

1. Stop new orchestration cycles.
2. Retain the encryption key and the database backup.
3. Restore the pre-migration database backup if the previous application
   version must be restored.
4. Redeploy the previous backend and frontend together.

Do not discard the encryption key while encrypted settings remain in MongoDB.
The previous plaintext-only application cannot consume encrypted provider
credentials. Avoid manually converting credentials back to plaintext; restore
the secured backup or re-enter provider keys after rollback instead.

The two orchestration collections and their indexes are additive. They can
remain during an application rollback because the older application does not
read them.
