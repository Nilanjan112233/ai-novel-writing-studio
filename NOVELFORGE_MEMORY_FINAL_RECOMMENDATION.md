# NovelForge Memory Final Recommendation

**Audit date:** 2026-08-13  
**Final decision:** **NATIVE + SELECTED TENCENT-INSPIRED CONCEPTS**

Do not adopt a Native + Tencent writing hybrid now. Keep Tencent optional/experimental while improving NovelForge Native around its existing authority model.

## Why

NovelForge already has what generic memory systems lack: explicit canon, author decisions, confirmed planning, approved prose, chronology, character knowledge, candidate governance and immutable revision lineage. Replacing or paralleling that with a generic memory authority would reduce correctness.

Native retrieval, however, is not adequate as implemented. It has a confirmed duplicate-index defect, inconsistent authority filtering, no explicit chronology or character-knowledge boundary, hash-bucket rather than real semantic embeddings, no BM25/RRF, weak semantic deduplication, fixed record caps, and no progressive evidence expansion. Develop Story also sends extraordinary amounts of duplicated context.

Tencent contributes good ideas—layers, provenance drill-down, recall budgets, hybrid retrieval and context offload—but the current local deployment has 458 L0 rows, zero L1/L2 records and embedding disabled. Its measured L0/Hybrid paths were slower and larger than Native without better labelled recall.

## Ranked bottlenecks

| Priority | Problem | Classification | Evidence / impact |
|---|---|---|---|
| P0 | Derived/future/stale information can conflict with authority; no chronology/knowledge hard filter | Correctness/authority risk | Real chronology and POV conflicts passed continuity checks |
| P0 | Duplicate logical chapter-intelligence embedding | Confirmed defect | Two near-identical hits consumed ~3.5k tokens in one packet |
| P1 | Retrieval ranks textual resemblance more than story usefulness | Continuity quality | Hash-vector cosine + overlap; no learned semantics/BM25/graph/temporal validity |
| P1 | Chapter intelligence is repetitive and can preserve extraction errors | Continuity quality | Dominated 73.5% retrieved section in real packet |
| P2 | Full Story Bible and prior outputs sent to every Develop specialist | Token/cost waste | 360k prompt tokens across five real calls in cycle 3 |
| P2 | Cross-layer duplicates and no per-source budgets | Token/cost waste | 30–39% directly removable from real 5.4k packet |
| P3 | Full-project refresh on recall and brute-force 2,000 cap | Latency/scale | O(project sources) reads/writes per recall; silent corpus truncation risk |
| P4 | Tencent adds gateway/process/store without current L1/L2 benefit | Operational complexity | L0-only live state; current Hybrid larger and slower |
| P5 | Story Bible cold rebuild grows roughly linearly | Future scale | ~5.1s Bible stage at synthetic 500 chapters |

## Answers to the 22 required questions

### 1. What exactly is NovelForge Native memory today?

A governed set of MongoDB authority owners plus derived Story Bible/Narrative Analysis/chapter-intelligence projections, a materialized `memory_embeddings` retrieval index, recent/working context, compressed cycle summaries and per-agent memory. It is not a single vector database.

### 2. What information actually influences future chapters?

Active canon, approved/resolved decisions, confirmed planning, active structured characters/relationships/world/timeline/threads/mysteries/knowledge/artifacts, approved prose evidence, chapter intelligence, continuity reports, Native retrieved hits, recent/cycle context and—in structured writing—bounded Story Bible/Narrative Intelligence and agent memory.

### 3. What is stored but rarely/never used?

Raw Story Studio/Narrative Assistant history is not replayed into Native writer prompts; Workspace Companion and provider traces are product/operational state; shared narrative context is indirect; Tencent L0 is excluded from safe writer primary; general Native hits are assembled but not passed to the final structured Scene Writer prompt.

### 4. Where is context duplicated?

Across prose, extraction, chapter intelligence, Story Bible, Narrative Analysis, continuity reports, owner records and memory embeddings; and across agent outputs, agent memory, Story Bible discussion/editorial/workflow sections and cycle handoffs.

### 5. Where are tokens wasted?

Duplicate chapter intelligence, near-identical continuity reports, owner facts repeated as Native hits, verbose derived summaries, full Story Bible delivery to every specialist, repeated prior outputs, retries/range correction and broad Story Studio analysis packets.

### 6. What important information can be missed?

Rare long-horizon facts, paraphrased facts, current versus historical ownership/state, POV-specific knowledge, superseded planning, and cross-domain obligations. Fixed top-k/caps and text-heavy ranking exacerbate misses.

### 7. How does the architecture behave at 100+ chapters?

Storage remains viable, but refresh/query work grows, the 2,000-active-embedding and 1,000/source caps become dangerous, Story Bible cold rebuild grows, and temporal/knowledge conflicts multiply. A bounded packet can hide declining recall quality.

### 8. Does NovelForge implement Tencent L0/L1/L2/L3 equivalents?

L0 yes, distributed; L1 partially through structured owner records but not compact retrieval atoms; L2 redundantly through chapter intelligence/timeline/threads/analysis/Bible; L3 partially through project tone/story vision, with no governed author preference profile.

### 9. Which Tencent ideas are genuinely useful?

Progressive compact-to-evidence retrieval, atomic derived assertions, episode navigation, provenance drill-down, explicit recall budgets, lexical + semantic fusion, conflict/dedup passes and compact workflow handoffs.

### 10. Which Tencent ideas duplicate existing systems?

A separate raw story store, generic scenario authority, persona as canon, a parallel story graph, and external ownership of story facts would duplicate or weaken NovelForge owners.

### 11. Should atomic memory be added?

Yes, as a rebuildable retrieval projection with owner version, story-time validity and evidence pointers. Never as a second authority.

### 12. Should episodic/scenario memory be added?

Improve chapter intelligence into the canonical derived episode view and compute cross-chapter progression views. Do not create another authoritative episode database.

### 13. Should author preference memory be added?

Yes: explicit project scope first, operation scope by default, author-global opt-in, inferred suggestions inactive until reviewed and supported by repeated evidence.

### 14. Should progressive retrieval be added?

Yes. Compact facts/open obligations first, episode expansion second, bounded prose evidence last.

### 15. Should explicit retrieval budgets be added?

Yes: total, per-source, compact/episode/raw evidence, recent/old memory, diversity and mandatory authority coverage. Pilot ranges are in the V2 proposal.

### 16. Should Native use lexical + semantic + story-specific ranking?

Yes. Use BM25 + real embeddings + graph candidates, fuse ranks, then enforce authority, chronology, character knowledge, narrative importance and unresolved-thread priority.

### 17. Can Develop Story context be significantly reduced?

Yes. The measured target is at least 50%, with 55–75% plausible by role-specific packets and compact handoffs while retaining all specialists.

### 18. Should Tencent remain experimental?

Yes, narrowly. Do not promote until L1/L2 are actually populated and it beats Native on rejection safety, important recall, latency/context cost or Story Studio quality. Remove later if it cannot meet those gates.

### 19. What should Native Memory V2 look like?

Existing authority owners -> versioned derivation ledger -> compact assertions/improved episodes/preferences -> hard authority/chronology filters -> BM25/semantic/graph candidate generation -> story-specific fusion/dedup/token packing -> progressive evidence delivery to consumer-specific packets.

### 20. What should be implemented first?

Fix logical identity/duplicate embeddings and add a read-only replay/attribution harness; then authority/chronology filters and incremental indexing; then compact assertions/episodes and hybrid ranking; then progressive packets; then Develop Story role manifests and handoffs; preferences later.

### 21. What should explicitly not be implemented?

No new authority database, no automatic candidate promotion, no raw Tencent writer primary, no generic Tencent schema copied into canon, no permanent one-shot preference inference, no second Story Bible/graph/timeline, no wholesale deletion of V1 before shadow/canary proof, and no whole-manuscript prompts.

### 22. What measurable acceptance criteria should implementation use?

- zero candidate/rejected/stale/future-chapter leakage;
- zero duplicate logical hits;
- valid provenance/owner version on every derived item;
- correct chronology and character knowledge at 10/25/50/100/250/500 chapters;
- important recall@k/MRR non-inferior to current Native;
- real contradiction/POV case detected;
- at least 25% Discovery packet reduction on the measured case;
- at least 50% Develop Story prompt reduction with blind quality non-inferiority;
- bounded P95 retrieval without the 2,000-record ceiling;
- deterministic rebuild and reversible migration;
- complete operation-level provider-cost accounting.

## Prioritized next Codex pass

### Phase 1 — P0 diagnostic and correctness foundation

1. Build a non-mutating replay/packet-attribution harness using stored packets and labelled corpora.
2. Fix chapter-intelligence logical identity so one source version yields one active embedding.
3. Audit every indexed source with a single eligibility policy: authority, active version, candidate/rejected/stale and as-of chapter.
4. Add tests for the real Elias chronology, POV shift, relationship extraction error and rejected-idea scenario.

### Phase 2 — incremental Native retrieval core

5. Replace query-time full refresh with event-driven incremental indexing plus repair/backfill command.
6. Remove global 2,000 and per-source 1,000 silent recall ceilings.
7. Add story-time validity and character-knowledge metadata.
8. Add logical/semantic dedup and per-source/token budgets.

### Phase 3 — compact derived memory and ranking

9. Add rebuildable atomic projections from existing owners.
10. Refactor chapter intelligence into compact episode plus evidence pointers.
11. Add BM25, real embeddings and graph candidates with rank fusion and story-specific re-ranking.
12. Implement progressive fact -> episode -> prose expansion.

### Phase 4 — Develop Story cost

13. Define specialist role manifests.
14. Add shared authority snapshot and compact delta handoffs.
15. Shadow replay the measured cycles and run blind non-inferiority evaluation.

### Phase 5 — product and optional experiments

16. Add explicit project preference governance and opt-in global preferences.
17. Expose plain-language “What NovelForge remembers” and provenance/correction routes if author testing supports them.
18. Re-test Tencent only after genuine L1/L2 enablement; otherwise plan removal of experimental complexity.

## Stop point

This audit deliberately stops before implementation. The next pass should begin with the replay/acceptance harness and P0 correctness fixes, not with a broad V2 schema rollout.

