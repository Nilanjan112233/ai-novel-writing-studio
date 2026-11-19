# NovelForge Phase D Final Recommendation

## Decision

**DO NOT IMPLEMENT GENERAL PRODUCTION PHASE D YET.**

Proceed next with a **bounded, matched quality-validation pilot for Develop Story only**. If it passes, implement deterministic role-aware episode selection behind the current Phase C/Phase B-safe fallback. Leave Discovery unchanged. Defer Story Studio and writing integration until their own quality gates pass.

## Why

The token gate is decisively met in shadow: Develop Story evidence falls 71.83%, from 13,810 to 3,890 tokens, and total prompts project 44.43% smaller. Authority coverage remains 5/5, and all five specialists receive their labelled required episode depth. However, no provider outputs were generated after ablation, so non-inferior specialist usefulness, cross-agent coherence, and prose quality remain unproven.

## Answers to the final questions

1. **Facts alone:** 15/42 tasks, 35.71% of the labelled corpus.
2. **Episodes:** 19/42, 45.24%.
3. **Raw evidence:** 8/42, 19.05%.
4. **Largest beneficiary:** Develop Story. Story Studio may later benefit selectively; long-range writing benefits when callbacks need origin/context.
5. **Should not use it now:** Discovery Writing; also normal Story Studio and production writing until separate gates pass.
6. **Develop Story tokens removable:** 9,920 evidence tokens in the shadow, 71.83% of evidence and 44.43% of total prompts.
7. **Quality when episodes are omitted:** labelled sufficiency decreases materially; fact-only failed 5/5 matched specialist role-depth checks and 6/8 writing tasks.
8. **Raw evidence value:** yes for wording, tone, subtle foreshadowing, dialogue callbacks, and revision/contradiction adjudication; it is unnecessary for 80.95% of the corpus.
9. **Additional retrieval frequency:** literal fact-first would expand beyond facts for 64.29% of tasks and to raw for 19.05%. Deterministic routing should avoid a separate model turn in normal operation.
10. **Provider cost:** projected lower if no extra call; about $0.003968 saved and $0.008835 total versus the observed $0.012803, assuming unchanged output. Not yet verified by a billed matched run.
11. **Latency:** deterministic pointer expansion adds about 1.531 ms to 500-chapter cold P50 and a conservative 2.529 ms to P95; not material. Model-requested extra turns would be material.
12. **Trigger:** deterministic role/task rules plus confidence/conflict rules are sufficient for the initial design. A bounded model-request escape hatch may come later; tool-driven retrieval is not justified as the default.
13. **Fallback:** current complete Phase C packet; if Phase C is incomplete, current Phase B/P0-safe authority-first fallback.
14. **Long-novel behavior:** likely improved context stability because evidence depth and average selected tokens stay task-dependent rather than chapter-count-dependent. Across 10-500 scales the fixed corpus retained 100% labelled evidence and Phase C Recall@8 1.0, but model quality was not tested.
15. **Implement Phase D?** Conditionally, yes for Develop Story after the matched provider quality gate; no general production rollout now.

## Pilot acceptance gates

- same five roles, project, instruction, provider, and model;
- current Phase C vs fact-only vs deterministic progressive packets;
- at least 25-30% evidence reduction;
- non-inferior labelled role requirements and blind usefulness;
- non-inferior cross-agent coherence;
- zero authority, chronology, candidate, rejected, future, and knowledge regressions;
- no meaningful retry/fallback increase;
- total provider cost lower after outputs and any expansion calls;
- interrupted jobs resume with the same deterministic evidence manifest.

If the pilot fails, keep Phase C unchanged. Do not add agent retrieval tools, a new memory store, Tencent dependency, or generic progressive machinery to chase token savings.
