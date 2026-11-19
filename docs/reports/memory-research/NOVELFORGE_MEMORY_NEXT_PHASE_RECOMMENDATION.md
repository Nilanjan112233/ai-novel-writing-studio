# NovelForge Memory Next-Phase Recommendation

## Decision

Proceed next to **Phase A: incremental/event-driven indexing**, then measure again. The P0 foundation is correct enough to support further work, but the 500-chapter full-scan latency and refresh cost should be addressed before adding more memory records or retrieval layers.

Recommended order:

1. **Phase A — incremental/event-driven indexing.** Replace query-time full-project refresh with owner-event upserts, checkpoints, explicit completeness/lag telemetry, and rebuild jobs. Preserve the logical identity and eligibility policy established here. Never restore silent limits.
2. **Phase E measurement, then implementation — Develop Story role-specific packets and delta handoffs.** New packet attribution must first capture representative cycles. Then target the Story Bible/current-plan and same-cycle duplication that dominates cost. Keep full authority coverage and non-inferior labelled specialist output.
3. **Phase B — atomic derived memory plus improvement of existing chapter/episode memory.** Generate provenance-linked compact facts from authority owners and improve Chapter Intelligence rather than creating a second authority or generic parallel L2 store.
4. **Phase C — lexical plus real semantic candidate retrieval and story-specific rank fusion.** Add BM25/lexical exact-name support, semantic embeddings, metadata/chronology/authority filters, unresolved-thread and graph signals, then fuse. The current scale misses show this is useful after indexing completeness is solved.
5. **Phase D — progressive fact to episode to evidence expansion.** Implement only after atomic/episode layers and quality labels exist; otherwise progressive stopping can hide required evidence.

Phase E appears second because current Develop Story costs are extreme, but it should begin with attribution/evaluation rather than packet deletion. If engineering capacity requires strict letter order, complete Phase A first and run one newly attributed Develop Story cycle before choosing between E and B.

## Acceptance criteria for Phase A

- unchanged owner event creates zero additional logical records;
- update/delete/supersede events reach the index with measured lag and no authority mutation;
- rebuild produces the same active logical set as incremental indexing;
- no query reports “complete” when a checkpoint or source scan is incomplete;
- 500-chapter labelled Recall@8 is at least 0.8333 with zero safety leakage;
- 500-chapter P95 materially improves from the current 111.33 ms complete-scan baseline;
- backup/restore and Tencent-disabled operation remain functional.

## Criteria before Phase B/C/D/E is accepted

- zero candidate, rejected, future, superseded-current, and POV-knowledge leakage on the permanent corpus;
- no loss of labelled authority facts versus this baseline;
- logical duplicates remain zero;
- every memory item retains owner/version/provenance/evidence;
- derived memory is rebuildable and never authoritatively writable;
- Develop Story target: at least 50% prompt reduction on matched specialist tasks with non-inferior labelled quality;
- progressive retrieval must expand evidence when compact memory is insufficient or conflicting.

## Explicitly do not implement next

- Tencent authority or required Tencent writing dependency;
- generic L1/L2 stores divorced from NovelForge owners;
- a second Story Bible or graph database;
- inferred permanent author preferences;
- destructive V1 cleanup or wholesale migration;
- semantic consolidation without reversible provenance;
- a hard row/token cap that silently presents partial retrieval as complete.

Tencent should remain optional/experimental. Its fallback and Native-primary safe-writing boundary pass. The evidence does not justify making it required or optimizing it before Native indexing and packet costs.

## Stop condition honored

This pass stops at P0 correctness, replay, attribution, baselines, tests, and reports. No Native Memory V2 phase has begun.

