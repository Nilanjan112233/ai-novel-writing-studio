# NovelForge V2 RC9 — Known Limitations

These limitations are explicit release boundaries, not deferred hidden blockers.

## Deployment

- RC9 supports local/private Windows beta use through Docker Desktop only.
- It is not approved for hosted, public-internet or multi-tenant deployment. Authentication, authorization and tenant isolation were intentionally not added.
- There is no signed native installer, automatic updater or code-signed executable. First source install requires Docker Desktop, internet access and substantial disk space.
- The measured first clean build took 545.1 seconds. A normal cached start took 63.7 seconds on the test host.
- The frontend Docker image is approximately 1.42 GB; backend is approximately 473 MB.

## Backup and disaster recovery

- Automatic timer-based whole-project backups are not provided. Authors use explicit project/all-project backup and the mandatory backup-before-update launcher.
- Retention is ten available archives per project. Authors must download/copy archives to another device or trusted storage to survive complete machine/disk loss.
- Restore is deliberately restore-as-copy. In-place destructive replacement is unsupported.
- A real full-disk condition and abrupt hardware power loss were not induced; safe write-probe, destination failure, database outage and restart behaviors were tested instead.

## Performance

- Cold bootstrap is still dominated by Story Bible projection for very large projects: 5.69 seconds at 500 chapters and 11.67 seconds at 1,000 in the synthetic benchmark.
- Warm bootstrap remains fast (42.83 ms at 500; 71.90 ms at 1,000), but the first open of an unusually large project is visibly slower.
- The benchmark is synthetic and should not be treated as a promise for all hardware or prose sizes.

## AI

- AI generation requires a working author-supplied provider credential and remains subject to provider availability, latency, quotas and policy.
- Existing/manual work is available without AI; generation and provider-backed review are not.
- Relevant bounded story context is sent to the configured AI provider when the author requests an AI operation.
- Real-provider regression reduces risk but cannot eliminate future provider-format variability.

## Maintenance and support

- Backend tests emit 66 known deprecation warnings from Pydantic v2 compatibility and LangGraph serializer defaults. They do not affect the validated runtime, but must be removed before the underlying major versions are upgraded.
- Beta feedback and support bundles are saved locally; NovelForge does not automatically transmit them to a support service.
- The private beta still needs an operator-maintained support channel and clear response expectations.

## UX

- Companion and dashboard may occasionally recommend different valid adjacent planning actions.
- Operational Settings is information-dense on the smallest supported desktop layout.
- The product is desktop-only; mobile use is neither designed nor tested.

## Release boundary

These limitations support **PRIVATE BETA — CONDITIONAL GO**, not public commercial/SaaS release. The conditions are: Docker-assisted onboarding, backup orientation, local-only deployment and acknowledged external-provider dependency.
