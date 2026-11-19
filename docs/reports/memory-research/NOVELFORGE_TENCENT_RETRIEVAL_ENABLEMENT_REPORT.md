# NovelForge TencentDB Retrieval Enablement Report

## Outcome

Tencent retrieval is now operational in the local standalone deployment. The previous zero-recall result was a deployment/adapter problem, not evidence that capture was sufficient:

- The installed Tencent package requires Node `>=22.16.0`; the system Node was `22.14.0` and did not expose FTS5. An isolated Node `v22.16.0` runtime exposes `node:sqlite` FTS5 and is used by the test launcher.
- The gateway accepts the documented standalone `keyword` recall strategy. `fts` was not a valid strategy for this package and silently selected the wrong path.
- SQLite/BM25 keyword search is enabled; embeddings remain intentionally disabled in this local test because no Tencent LLM/embedding service is configured.
- NovelForge calls `/recall` first and, when L1 recall is empty, uses the documented `/search/conversations` L0 fallback. The adapter now preserves each scored message boundary and provenance instead of treating the whole search response as one hit.

## Official references inspected

- [TencentDB Agent Memory repository](https://github.com/TencentCloud/TencentDB-Agent-Memory)
- [Standalone deployment guide](https://github.com/TencentCloud/TencentDB-Agent-Memory/blob/feat/server_team/README.deployment.md)
- [TencentDB Agent Memory product/API documentation](https://cloud.tencent.com/document/product/1813/132103)

## Boundary

This deployment currently proves L0 conversation capture/search, not Tencent L1/L2/L3 semantic extraction. Tencent remains derived retrieval telemetry. NovelForge MongoDB remains authoritative for canon, decisions, planning, structured domains, Story Bible, Narrative Intelligence, approved prose, revisions, and manuscript state.

