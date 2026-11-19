# NovelForge V2 RC9 — Privacy and Supportability Report

## Accurate deployment boundary

NovelForge RC9 is a local/private desktop-style beta. Frontend and API ports bind to localhost; MongoDB is reachable only on the Docker Compose network. RC9 does not provide or claim hosted multi-tenant authentication, authorization, tenant isolation, rate limiting or internet-facing API hardening.

## Data custody

- Story/project data is stored in the local MongoDB named volume.
- Encryption material, backup archives, support bundles and publication exports are stored in the documented application data locations/volumes.
- Project backups contain project-scoped creative state but exclude provider credentials and global provider configuration.
- When an author requests AI generation, NovelForge sends the bounded story context needed for that operation to the configured provider. It does not claim that story content never leaves the computer.
- Existing/manual content access does not require an AI call.

## Credential controls

Provider keys remain encrypted at rest and are masked in public Settings responses. Gemini requests use the `x-goog-api-key` header instead of a key-bearing URL. Source scanning found no credential-like source match after the correction. Raw Gemini/Groq response bodies are no longer logged by the audited provider paths.

## Support bundles

The author explicitly creates and downloads a bundle. Included material is limited to application/schema version, supported deployment, readiness, migration status, provider/model names without secrets, redacted operation outcomes and backup metadata.

Excluded material includes story prose, prompts, provider responses, API keys/tokens, encryption keys and database URLs. A regression test inserted a credential-shaped canary and a unique story sentence into operational records; neither appeared anywhere in the ZIP.

## Feedback

Beta feedback is categorized (`startup`, `ai`, `backup_restore`, `workflow`, `performance`, `other`) and stored locally. Diagnostic attachment is opt-in. The API ignores requests to include story content and confirms `story_content_attached: false`. No hidden analytics or behavioral telemetry was introduced.

## Support workflow

1. Note the author-facing reference ID.
2. Open Settings → NovelForge readiness and retry/check the named dependency.
3. If unresolved, create a Support Bundle.
4. Review the privacy statement before sharing the downloaded file through the beta support channel.

The in-app flow does not silently transmit the bundle or feedback externally.

## Privacy limitations

The author controls the configured AI provider account and is responsible for that provider's retention/usage terms. Backups contain the novel and therefore require the same care as the manuscript. Copying an archive to cloud storage is an author action governed by that storage provider. RC9 has not received an external privacy/legal certification.
