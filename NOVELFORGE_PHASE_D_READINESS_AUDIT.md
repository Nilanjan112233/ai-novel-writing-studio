# NovelForge Phase D Readiness Audit

Date: 2026-08-14  
Scope: read-only shadow study; no production Phase D implementation

## Decision

**NOT READY FOR A GENERAL PRODUCTION PHASE D ROLLOUT. READY FOR A BOUNDED DEVELOP STORY QUALITY-VALIDATION PILOT.**

The token opportunity is strong, but the final quality gate is not yet proven. A labelled 42-task corpus found 35.71% fact-only tasks, 45.24% episode-required tasks, and 19.05% raw-evidence-required tasks. The matched Develop Story shadow projection reduced evidence from 13,810 to 3,890 tokens (71.83%) and preserved every labelled authority requirement, but no new provider calls were made, so non-inferior generated specialist and prose quality cannot honestly be claimed.

## Verified current paths

| Consumer | Evidence path today | Phase D relevance |
|---|---|---|
| Story Studio | writing state + confirmed planning + Narrative Analysis findings/nodes; requested chapter context only when explicitly named | selective benefit for why, contradiction, history, and comparison questions; not a direct Phase C consumer today |
| Discovery Writing | Context Engine authority/structured state + Phase C top-8 Native retrieval, P0 filtered as of the prior chapter and POV | no material need; current evidence is already 316 tokens with Recall/MRR 1.0/1.0 |
| Structured drafting agents | writing Story Bible projection + recent chapter memory + authority; Native recall is performed in the shared agent setup but is not serialized into the drafting-specific packet | requires a separate writing-quality study before any progressive integration |
| Develop Story specialists | authority snapshot + role projection + Native retrieval + compact recent episodes + handoffs + workflow memory | highest-value target; current evidence is 13,810 tokens across five specialists |

Current Phase C remains unchanged: P0 filtering is applied before ranking; Phase C generates bounded lexical candidates; weighted lexical/hash/metadata ranking follows; logical/version/content deduplication precedes top-k packing. Phase A readiness and the complete Phase B fallback remain the safety boundary.

## Experiment design

- Reused existing Phase B atomics, compact episodes, evidence pointers, approved prose, and Phase C artifacts.
- Read approved prose and exact pointer latency from project `6a788192066c6d634556c254` without writes.
- Evaluated 42 labelled tasks by required evidence markers, not model self-assessment.
- Reprojected the stored matched five-specialist context in shadow only.
- Reused measured Phase C 10/25/50/100/250/500 scale results and added read-only pointer lookup timings.
- Made zero provider calls and zero Mongo writes.

Machine evidence is under `artifacts/memory-phase-d/`. The runner is `scripts/run_memory_phase_d_readiness.py`.

## Main findings

1. Literal fact-first sequential retrieval is the wrong default. In this corpus, 64.29% of tasks need at least episode depth and 19.05% need raw evidence. A deterministic role/task router can fetch the appropriate level directly and avoid an extra model round trip.
2. Develop Story is the clear opportunity. Selective role episodes plus compact facts project 9,920 fewer evidence tokens and 44.43% fewer total prompt tokens.
3. Episodes are essential, not optional compression. Fact-only failed the labelled role-depth requirement for all five matched specialists.
4. Raw evidence is a minority overall (19.05%) but concentrated in wording, tone, revision, contradiction, and prose-continuity work. It should be bounded and exact-pointer based.
5. Discovery should remain unchanged. Adding orchestration around a 316-token, perfect-recall packet has no measured benefit.
6. Story Studio should not be refactored merely to share a retrieval architecture. Its current grounding path is different; evidence expansion could later support “show why,” but that needs a separate design.

## Safety and scope result

Production behavior changed: **no**. Authority mutations: **zero**. Provider calls: **zero**. Tencent use: **none**. The source project still had 2 drafts, 2 Chapter Intelligence records, 87 atomics, 149 memory-index rows, and 2 context packets after the audit.

The diagnostic runner compiled successfully, regenerated all seven JSON artifacts, and the final consistency check verified all ten reports, 42 labelled cases, the 13,810-token Phase C baseline, 5/5 authority coverage, and the zero-write/zero-provider manifest. Full backend/frontend suites were not rerun because no production or test code was changed.

## Required next gate

Before production implementation, run one matched real-provider Develop Story comparison with the exact Phase C packet, fact-only packet, and deterministic progressive packet; then run a small writing sample for callback, tone, and contradiction tasks. Require non-inferior specialist usefulness, cross-agent coherence, continuity, and prose specificity. If that gate passes, implement Develop Story only first, behind the current Phase C/Phase B-safe fallback. Discovery should remain unchanged.
