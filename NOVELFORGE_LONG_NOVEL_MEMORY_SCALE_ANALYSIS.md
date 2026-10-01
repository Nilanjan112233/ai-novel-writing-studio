# NovelForge Long-Novel Memory Scale Analysis

**Audit date:** 2026-08-13  
**Scope:** 10/25/50/100/250/500 chapters, using current code complexity, live records, persisted synthetic benchmark artifacts and read-only calculations. No paid chapters were generated.

## Executive finding

MongoDB storage growth itself is manageable through 500 chapters. The critical scaling problems are retrieval refresh cost, a silent 2,000-active-embedding recall ceiling, derived duplication, chronology/knowledge conflicts, and Story Bible reconstruction/context growth. UI bootstrap caches and bounded first-page queries perform acceptably after warm-up, but they do not prove memory recall quality.

## Current complexity

### Storage

Approved drafts, intelligence, extraction, timeline/history, versions, findings and embeddings grow approximately linearly with chapters and revisions. Segmented Story Bible sections avoid a single giant document, but rebuilding the projection still reads and serializes many growing sources.

### Native retrieval

Every normal recall can call `index_project_memory`, which scans up to 1,000 records for each source specification and writes/refreshes embeddings. Retrieval then loads at most 2,000 active embeddings into application memory and brute-force scores them (`memory_retrieval_service.py:259-370`).

Consequences:

- query latency and database traffic grow with the project even when no source changed;
- after 2,000 active embeddings, an unordered capped read can omit valid memory silently;
- a source with over 1,000 records is incompletely refreshed;
- the duplicate chapter-intelligence defect can consume roughly two slots per chapter;
- ranking and chronology quality, not disk capacity, become the limiting factors.

### Story Bible and analysis

Current synthetic launch artifacts show Story Bible reconstruction dominates cold workspace bootstrap:

| Chapters | RC9 cold bootstrap | Story Bible stage | Warm median |
|---:|---:|---:|---:|
| 50 | 1,137 ms | artifact-dependent | not repeated here |
| 100 | 2,414 ms | 2,044 ms | 15 ms |
| 250 | 2,942 ms | artifact-dependent | not repeated here |
| 500 | 5,688 ms | 5,098 ms | 43 ms |
| 1,000 reference | 11,670 ms | 10,557 ms | 72 ms |

The earlier RC8 artifact similarly measured 500 chapters at 3,688 ms cold/24 ms warm. These are synthetic operational benchmarks, not provider-context or retrieval-quality benchmarks.

## Scale projection

| Chapters | Expected current behavior | Main continuity/memory risk | Operational risk |
|---:|---|---|---|
| 10 | Native scan and packets usually small; duplicates already visible | Derived summary can dominate and contradict authority | Low latency, unnecessary token waste |
| 25 | More chapter intelligence, candidates, timeline and versions | Similar facts begin crowding top-k; old candidate/stale leakage | Repeated index refresh and Story Bible growth |
| 50 | Existing tests cover some chapter intelligence health | Relationship/mystery progression needs chronology-aware retrieval | Keyword-only Tencent benchmark lost hits; Native still brute-force |
| 100 | Cold bootstrap around 2.4s in RC9 synthetic artifact | Top-k textual similarity misses rare long-horizon facts | Hundreds/thousands of derived records scanned per query |
| 250 | Story/character/mystery histories have many valid states | No `as_of_chapter` boundary can return future or superseded state | Near/over 2,000 active embeddings depending on source density |
| 500 | Mongo remains viable; warm UI cache remains fast | Contradiction, knowledge and stale-memory risk becomes P0/P1 | 2,000 cap likely truncates corpus; 1,000/source refresh caps; cold Bible ~5.7s |

## Indicative growth by category

For each approved chapter, Discovery can create:

- one draft plus versions;
- one extraction with many candidates;
- one active chapter-intelligence record plus older inactive versions;
- multiple owner projections for characters, relationships, mysteries, threads, timeline, knowledge and artifacts;
- Narrative Analysis nodes/edges/findings/history;
- one or more continuity reports;
- memory embedding documents for chapter intelligence and other changing sources.

The two-chapter real project already had 29 + 24 extraction candidates, 17 mysteries, 8 plot threads, 8 characters and 11 memory embeddings. Most were candidates, demonstrating that derived/possible state can grow much faster than chapters.

## Context growth

The ContextEngine total cap prevents unlimited Discovery packets, but its behavior under pressure is not quality-aware:

1. retrieve eight hits without a token budget;
2. build all working memory;
3. remove lowest-ranked retrieved hits until under cap;
4. remove active context if still over;
5. never trim working memory.

At long scale, the packet may remain bounded while relevant recall degrades. A constant prompt size is not evidence of constant continuity quality.

Develop Story is worse because full Story Bible delivery scales with workflow/discussion/editorial history and model windows are large enough to defer trimming. The observed two-cycle growth occurred in a much smaller-than-500-chapter project.

## Chronology and character knowledge

At 100+ chapters, one fact commonly has several historically valid states:

- artifact ownership changes;
- injuries heal;
- relationships progress;
- mysteries move from hidden to suspected to revealed;
- characters learn different information at different times;
- revised chapters supersede earlier evidence.

Current Native retrieval does not filter by `valid_from`, `valid_to`, current chapter, point of view, or character knowledge. Recency boosts cannot replace temporal validity. V2 needs bitemporal-like story validity (story chapter/scene) plus record/version validity.

## Tencent scale implication

The local Tencent store is L0-only with embedding disabled. In a prior synthetic 25/50/100-record measurement, mean latency was roughly 459/485/481 ms and hits per query fell from five to two at 50/100. It is not a solution to Native long-scale behavior in the current deployment.

Tencent's layered/progressive concepts remain relevant, but NovelForge should implement them over its story-specific owners and chronology.

## V2 scale model

At all sizes:

- event-driven incremental indexing, not full refresh per query;
- no fixed global 2,000-document recall ceiling;
- logical identity and version invalidation;
- compact facts/episodes stored once with multiple evidence pointers;
- metadata narrowing before lexical/semantic search;
- as-of chapter and character-knowledge filters;
- raw prose fetched only by evidence pointer;
- per-consumer budgets independent of total corpus size.

Expected query work should depend mainly on the narrowed candidate set, not total project documents.

## Scale acceptance matrix

Build labelled synthetic corpora at 10/25/50/100/250/500 chapters with seeded:

- exact names and rare artifacts;
- paraphrased facts;
- ownership and relationship changes;
- future-chapter traps;
- rejected candidates;
- revised/superseded prose;
- POV-specific character knowledge;
- dormant and unresolved mysteries;
- duplicate summaries.

Measure:

| Metric | Required behavior |
|---|---|
| Authority leakage | 0 candidate/rejected/stale/future hits in safe-writing packet |
| Logical duplicates | 0 duplicate logical items after selection |
| Important recall | Non-inferior recall@k and MRR across all scales |
| Chronology | Correct as-of state and ownership in every labelled transition |
| Character knowledge | No information revealed to a POV character before learned |
| Latency | P50/P95 reported separately for incremental index and query; no step-function at 2,000 |
| Packet size | Bounded by consumer policy, not corpus size |
| Context value | Labelled relevant tokens / total tokens does not degrade with chapters |
| Rebuild | Deterministic logical result from same authority snapshot |
| Backup/restore | Authority intact; derived memory rebuildable |

## Conclusion

NovelForge can store a 500-chapter novel, but current Native recall cannot be trusted to retrieve the best temporally valid information at that scale. The first scale fix is not a new database: it is incremental indexing, removal of hard caps, story-time metadata, deduplication and progressive evidence retrieval.

