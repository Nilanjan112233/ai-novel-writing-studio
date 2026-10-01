# Memory Provider Operational Resource Report

## Tencent local sample

The official standalone gateway ran successfully on local Node `v22.14.0`; the checked deployment documentation states Node `>=22.16.0`, so the local runtime is below the documented requirement and should be upgraded before relying on the service. One observed gateway process used approximately 433,729,536 bytes working set and 470,085,632 bytes private memory. The local data directory contained a 4,096-byte `vectors.db`, 32,768-byte shared-memory file, and 135,992-byte WAL at inspection time.

These are one local sample, not a normalized production benchmark. They include gateway/runtime overhead and must not be generalized to Tencent service deployment.

## Native operational profile

Native uses NovelForge’s existing MongoDB collections and in-process deterministic indexing/retrieval. It adds no service startup, port, or external memory dependency for authors.

## Privacy and recovery

Standalone Tencent stores derived memory locally in its configured data directory. Service deployment has additional infrastructure and data-location implications. NovelForge does not make unsupported privacy claims; the deployment choice must be disclosed separately. Tencent memory remains rebuildable/optional derived data and is not a prerequisite for backup restore or project operation.
