# NovelForge Memory P0 Implementation Report

## Outcome

This pass makes Native memory measurable and establishes the P0 correctness boundary without adding Native Memory V2. Approved prose, active canon, approved decisions, confirmed planning, and current approved structured state remain the owners of story truth. Memory embeddings, Chapter Intelligence, candidates, agent output, Narrative Analysis, and Tencent remain derived observations.

The implementation adds:

- a provider-free replay and attribution harness;
- deterministic logical identity for owner-versioned indexed records;
- query-time and packet-time logical deduplication;
- one central safe-writing eligibility policy;
- chapter/scene, branch, status, and POV-knowledge eligibility inputs;
- explicit Discovery POV contract fields;
- P0 continuity findings with category, severity, and evidence;
- removal of the silent 2,000-hit and 1,000-record refresh caps;
- future Develop Story prompt-attribution fields, without redesigning its packets.

No schema migration, authority migration, provider-setting change, Tencent optimization, new graph, BM25, atomic store, episodic store, or destructive cleanup was performed.

## Runtime changes

`memory_retrieval_policy.py` owns logical identity, authority labelling, and consumer eligibility. `memory_retrieval_service.py` materializes domain IDs consistently and keeps physical IDs as evidence. `context_engine.py` applies the same policy to direct Mongo context, not only embedding hits. Discovery uses `as_of_chapter = target chapter - 1`, supplies its POV character, and excludes raw conversation history from the safe writer packet.

Chapter Intelligence indexing now uses `intelligence_id` as its logical source on both direct and refresh paths. Re-indexing an unchanged logical source/version updates the one materialization. A bounded historical version remains materialized when it has an explicit `valid_to_chapter` or `valid_to_scene`; the policy chooses it only inside that interval.

The continuity validator now emits `continuity_findings` for:

- POV/person shift;
- duration-based chronology conflict;
- high-confidence direct canon/decision/confirmed-planning reversal;
- confirmed kinship/relationship conflict;
- impossible current artifact ownership;
- POV character knowledge leakage.

Explicitly requested evolution is exempted when the writing contract declares the change. These checks are deliberately high-confidence and do not attempt broad semantic contradiction inference.

## Measured result

On the real Memory Fantasy Chapter 2 packet, the correct pre-Chapter-2 boundary reduced the replayed packet from 5,428 to 3,884 estimated tokens (28.4%). The one duplicate logical Chapter Intelligence hit and its 1,344 duplicate retrieval tokens were removed. Labelled important-term Recall@k and MRR remained 1.0.

The 10–500 chapter synthetic corpus has zero post-fix candidate/rejected, future-chapter, and POV-knowledge leakage. At 500 chapters, Recall@8 improves from 0.0 under the incomplete 2,000-row legacy scan to 0.8333, but P95 rises from 40.35 ms to 111.33 ms. Correctness was chosen over silently incomplete results.

## Verification

- P0/provider boundary: 14 passed.
- Focused memory/context/continuity set: 39 passed.
- Complete backend: 190 passed, 7 skipped, 0 failed in 7m43s. The first 120-second attempt timed out and was not counted.
- Complete frontend: 87 passed across 23 files.
- Next.js 15.5.22 production build: passed.
- Browser workflow: not required for these backend-only retrieval and validation changes; no frontend surface changed. The frontend test suite and production rendering build cover the shared API/schema boundary.
- Paid provider calls made by replay/scale diagnostics: zero.

Machine-readable evidence is under `artifacts/memory-p0/`.

## Known boundary

This is a correctness foundation, not a relevance redesign. Native still uses a deterministic hash-vector/full-scan ranker. The new policy prevents unsafe evidence from entering safe-writing retrieval; it does not make retrieval genuinely semantic, consolidate near-duplicates, or create atomic/episode memory.

