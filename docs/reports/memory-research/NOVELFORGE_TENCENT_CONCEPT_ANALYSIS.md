# NovelForge Tencent Concept Analysis

**Audit date:** 2026-08-13  
**Decision context:** compare NovelForge's current Native architecture with the TencentDB Agent Memory implementation actually integrated locally and with current official architecture descriptions.

## Bottom line

Tencent's useful contribution is architectural inspiration: layered derivation, progressive disclosure, provenance drill-down, hybrid retrieval and explicit recall budgets. Tencent should not become NovelForge's story authority or writing-primary retrieval source. The currently deployed gateway demonstrates only L0 raw conversation keyword search; it does not currently demonstrate L1/L2/L3 value.

## Sources and version caveat

- Current official repository: [TencentCloud/TencentDB-Agent-Memory](https://github.com/TencentCloud/TencentDB-Agent-Memory).
- Current official README describes L0 Conversation -> L1 Atom -> L2 Scenario -> L3 Core/Persona, with BM25 + vector + RRF fallback and item/character/timeout budgets.
- Current official configuration documents keyword, embedding and hybrid/RRF strategies plus `maxResults`, per-memory and total recall character budgets.
- The official repository is evolving quickly and, at audit time, its default branch/product positioning had moved toward a broader team Memory Hub. This audit therefore separates concepts from claims about the local adapter.

## What is actually integrated locally

NovelForge's adapter calls `/capture` and `/recall`, then falls back to `/search/conversations` if structured recall is empty. Captured content is project-scoped. Tencent hits are explicitly marked derived and safe writing forces Native primary (`backend/app/services/memory_provider.py:160-304,487-522`).

Live gateway state:

| Layer / service | Observed state |
|---|---|
| Gateway | Healthy, version 0.1.0 |
| L0 conversation rows | 458 |
| L1 records | 0 |
| L2 scene-block files | 0 |
| Embedding service | Disabled |
| Recall mode | Local keyword/FTS conversation fallback |

Consequently, current Tencent benchmark results measure L0 retrieval, not the advertised layered pipeline.

## L0/L1/L2/L3 equivalence matrix

| Tencent concept | NovelForge equivalent | Classification | Assessment |
|---|---|---|---|
| L0 raw conversation/evidence | Story Studio jobs/messages, orchestration timeline, approved prose, agent outputs, provider traces | Already implemented, distributed | NovelForge keeps better domain boundaries, but lacks one uniform evidence pointer contract |
| L1 atomic memory | Confirmed owner records, candidate projections, timeline/knowledge/artifact/mystery records | Partially implemented and sometimes redundant | Structured records are superior to generic atoms when authoritative; compact retrieval atoms are missing |
| L2 scenario/episode | Chapter intelligence, timeline, plot threads, Narrative Analysis, Story Bible sections | Implemented but overlapping | No new scenario authority is needed; chapter intelligence should become a cleaner derived episode view |
| L3 profile/persona | Project tone/story vision, explicit instructions, agent core canon/decisions | Partial; author preference profile missing | Add governed explicit project preferences; author-global only opt-in |
| Short-term offload | Agent compaction and `compressed_memories` | Partial | Current summaries are crude and do not provide Tencent-style drill-down navigation |
| Progressive recall | Context trim-after-overflow | Missing in meaningful form | NovelForge assembles broadly first rather than stopping when compact facts suffice |
| Hybrid lexical/semantic | Hash-vector cosine + token overlap; Tencent hybrid merge | Weak/partial | Native has neither BM25 nor learned embeddings; current merge is score-sort plus exact hash dedup, not RRF |
| Recall budgets | top-k and total context caps | Partial | Per-source, evidence-expansion, authority and diversity budgets are missing |
| Provenance drill-down | Source IDs, chapter evidence, version lineage | Partial and domain-rich | Strong foundations; inconsistent across derived layers |

## Concept-by-concept assessment

### L0 raw memory

1. **Problem solved:** exact evidence and recovery when summaries lose detail.
2. **Already solved?** Yes, through approved prose, raw interactions and immutable traces.
3. **Better or worse?** NovelForge is better for story authority and revision lineage; worse at uniform drill-down references.
4. **Would copying help?** A new raw store would not.
5. **Adaptation:** standardize evidence pointers to existing records.
6. **Risks:** rejected ideas and stale outputs leak if raw history is treated as recall-ready truth.
7. **Cost:** low-to-medium for pointer normalization; high and wasteful for duplicating raw storage.

### L1 atomic memory

1. **Problem solved:** retrieve one precise fact without a long summary.
2. **Already solved?** Confirmed structured records often already are atomic; retrieval does not expose them compactly enough.
3. **Better or worse?** NovelForge has richer domain semantics but poorer compact selection/deduplication.
4. **Would copying help?** Yes as a **derived retrieval projection**.
5. **Adaptation:** materialize atomic assertions from authoritative owner versions, each with authority, valid chapter range and evidence pointers.
6. **Risks:** a second story authority, extraction errors, over-fragmentation and contradiction.
7. **Cost:** medium; most work is governance/invalidation, not text extraction.

### L2 scenarios/episodes

1. **Problem solved:** restore a chapter, scene, relationship progression or arc without raw evidence.
2. **Already solved?** Chapter intelligence, timeline, plot threads and analysis partly solve it.
3. **Better or worse?** NovelForge has story-specific signals but duplicates them and produces bloated episodes.
4. **Would copying help?** Not as a new layer/collection with authority semantics.
5. **Adaptation:** redesign chapter intelligence as the canonical **derived episode view**, plus computed cross-chapter episode views where useful.
6. **Risks:** more summary layers, stale episodes, chronology flattening.
7. **Cost:** medium; high if cross-arc consolidation is generated eagerly.

### L3 persona/preferences

1. **Problem solved:** restore durable user style and working preferences.
2. **Already solved?** Project tone, story vision and individual instructions exist; no governed author preference memory exists.
3. **Better or worse?** NovelForge is safer because it does not silently infer permanent preferences, but it makes authors repeat some preferences.
4. **Would copying help?** Selected profile ideas would.
5. **Adaptation:** explicit project preferences first; inferred suggestions require repeated evidence, confidence, scope, review and expiry. Global preferences are opt-in.
6. **Risks:** freezing one experiment into a permanent style, privacy, flattening deliberate variation.
7. **Cost:** medium product/governance work; low retrieval cost.

### Memory extraction and consolidation

- Tencent solves raw-log growth by asynchronous extraction and conflict/dedup passes.
- NovelForge already extracts on approval and has owner-specific structured models.
- Generic extraction should not replace these models. The useful adaptation is an asynchronous derived-memory builder triggered only after authoritative state changes.
- Consolidation should merge equivalent derived assertions but retain every evidence pointer and owner version.

### Deduplication

- Tencent's configuration supports extraction dedup/conflict checks.
- Native currently deduplicates exact normalized content, not semantic equivalence.
- NovelForge needs logical identity first, then field-aware/semantic equivalence, choosing the highest-authority/newest valid record while preserving alternate evidence.
- Current Hybrid exact hash dedup does not collapse semantically overlapping Native/Tencent results.

### Keyword, semantic and hybrid retrieval

- Tencent's documented hybrid mode uses keyword + embedding with RRF.
- Local Tencent has embedding disabled, so its observed path is keyword-only.
- Native's 64-dimensional SHA256 token buckets are deterministic similarity features, not semantic embeddings. Token overlap is not BM25.
- NovelForge should adopt hybrid fusion, but add authority, chronology, graph proximity, narrative importance, character knowledge and unresolved-thread signals after candidate generation.

### Recall budgets

- Tencent exposes result, per-memory, total-character and timeout limits.
- NovelForge has top-k and total packet caps but no source-specific or evidence-expansion budgets.
- This is directly useful and low conceptual risk if authority coverage is mandatory.

### Short-term workflow memory and context offload

- Tencent offloads verbose logs and keeps a compact symbolic navigation layer with drill-down.
- NovelForge per-agent compaction keeps bounded summaries and source provenance IDs, but `compressed_memories` mostly records counts/titles.
- Develop Story would benefit from compact state/delta handoffs with source pointers. Mermaid syntax itself is not important; the hierarchy and drill-down contract are.

### Provenance

- Tencent emphasizes lossless drill-down.
- NovelForge has stronger underlying evidence—approved versions, canon IDs, decision versions, owner rows—but derived layers do not expose it uniformly.
- Adapt the provenance discipline, not the external authority model.

## Measured Native vs current Tencent

Existing persisted benchmark results were rechecked against the current adapter and gateway state:

| Mode | Matched recall | Mean precision | Mean latency | Mean context |
|---|---:|---:|---:|---:|
| Native | 8/8 | 0.90 | 84.1 ms | 4,198 tokens |
| Tencent L0 fallback | 8/8 | 0.90 | 413.1 ms | 9,331 tokens |
| Current Hybrid | 8/8 | 0.90 | 413.1 ms | 13,529 tokens |

Matched writer prompts were 5,249 Native, 10,056 Tencent and 15,131 Hybrid tokens, with recorded costs of approximately $0.007248, $0.011561 and $0.016427. These results do not condemn Tencent's full layered architecture; they show that the **current local L0 fallback is not an efficiency improvement**.

At synthetic 25/50/100 records, Tencent L0 latency stayed around 459–485 ms and matching hits dropped from five to two at 50/100, while Native returned five. Again, this is keyword-only local behavior.

## Outcome assessment

| Candidate outcome | Evidence-based verdict |
|---|---|
| A — Native already sufficient | No; ranking, duplication, chronology and budgets are weak |
| B — Native adopts selected Tencent ideas | **Yes; recommended** |
| C — Tencent useful only for Story Studio/workflow memory | Possible experimental niche, not yet quality-proven |
| D — Tencent secondary retrieval source | Not justified by current L0 measurements |
| E — Hybrid justified | No; current Hybrid adds cost without recall gain |
| F — Tencent eventually removed | Reasonable if layered L1/L2 experiments still fail acceptance gates |

## Recommendation

Keep Tencent optional and experimental. Do not promote it to default, do not use it as story authority, and do not build V2 around its schemas. Re-run a narrow Story Studio/workflow experiment only after the gateway actually produces compact L1/L2 records with provenance, rejection/supersession controls and a measurable quality-or-cost gain.

