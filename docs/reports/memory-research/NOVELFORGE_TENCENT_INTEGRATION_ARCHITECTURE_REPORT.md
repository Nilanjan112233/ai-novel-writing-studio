# NovelForge TencentDB Agent Memory Integration Architecture

## Decision boundary

TencentDB Agent Memory is integrated as an optional derived-memory provider. MongoDB-backed NovelForge systems remain authoritative for canon, decisions, confirmed planning, structured story domains, Story Bible, Narrative Intelligence, approved prose, revisions, manuscript state, chronology, and recovery.

The boundary is implemented in `backend/app/services/memory_provider.py`:

- `NativeNovelForgeMemoryProvider` wraps the existing native retrieval path.
- `TencentAgentMemoryProvider` is a small HTTP adapter for the official Tencent gateway capture/recall contract.
- `MemoryProviderService` selects `native`, `tencent`, or `benchmark` modes, records telemetry, and performs safe fallback.
- `safe_for_writing=True` always keeps Native as the writing primary, even when Tencent is configured experimentally. Tencent can be observed, but it cannot inject unverified context into prose generation.

The application dual-captures relevant Story Studio, development, and approved-chapter events in benchmark/Tencent modes. Capture records are clipped and tagged with source type/source ID. Provider telemetry is stored in `memory_provider_events` and matched comparisons in `memory_provider_comparisons`; both are explicitly non-authoritative.

Settings are exposed only under Developer Mode through `/api/settings/memory`. The normal default is `native`. The UI labels Tencent experimental and states that it cannot change story authority. Product APIs expose provider status, recall, comparisons, and events for developer validation only.

## Official Tencent findings

The official repository documents a local standalone deployment and a service deployment. Standalone uses local SQLite/files and is appropriate for controlled local experiments; the service mode adds TCVDB/COS/Redis and is not needed for this first integration. Tencent describes L0 raw conversation, L1 atomic memories, L2 scene blocks, and L3 persona/profile layers. NovelForge maps those concepts only to derived observations and workflow memory; it does not map canon or decisions into authority.

Sources: [official repository](https://github.com/TencentCloud/TencentDB-Agent-Memory), [standalone/service deployment guide](https://github.com/TencentCloud/TencentDB-Agent-Memory/blob/feat/server_team/README.deployment.md), [official custom-agent integration guide](https://cloud.tencent.com/document/product/1813/132103).

## Safety properties verified

- provider failure is best-effort for capture and falls back to Native for recall;
- provider events have `authoritative: false`;
- Native remains the writing primary during Tencent experiments;
- no Tencent collection is used by Canon, Decision History, Story Bible, Narrative Intelligence, or approval logic;
- the project remains usable with the gateway stopped;
- existing Native memory is neither migrated nor deleted.

## Current limitation

The official local gateway was reachable and accepted captures, but its health reported `embeddingService: false`, and recall returned no memories. Therefore this adapter proves the boundary and failure behavior, not production-grade Tencent retrieval quality. A follow-up must configure a supported retrieval/indexing path before any default-mode decision.
