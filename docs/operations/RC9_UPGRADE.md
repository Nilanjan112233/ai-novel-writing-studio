# RC9 Update and Migration Safety

## Supported update sequence

1. Start the currently installed NovelForge version.
2. Double-click `Back Up Before Update.cmd` and wait for every named project to
   report completion.
3. Move or copy `NovelForge Update Backups` outside the application folder.
4. Replace application files with the supplied beta release while preserving
   Docker named volumes.
5. Double-click `Update NovelForge.cmd`.
6. Wait for readiness verification, then open several important projects and
   confirm prose, canon, decisions, Story Bible, drafts, and manuscript state.

The update launcher will not proceed if the pre-update backup step fails. It
builds new application images, starts the existing volumes, runs additive
migrations under a durable lease, and waits for both API and author workspace.

## Migration behavior

- Application version and schema level are explicit.
- Each migration step has a durable status record.
- Only one installation process may hold the migration lease; an abandoned lease
  can be recovered after expiration.
- Migrations and legacy normalization are idempotent.
- Ordinary records are extended in place; database architecture and existing API
  contracts are preserved.
- A failed migration prevents readiness and records the failed step. It does not
  claim that the application is ready.

## Rollback

Stop NovelForge. Restore the prior application files/images without removing
named volumes, then start the prior release if its documented schema range is
compatible. If persistent records cannot be opened safely, start a clean current
installation and restore downloaded project archives as copies. Never improvise
a manual database downgrade on author content.

