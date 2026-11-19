# NovelForge Phase D Discovery Study

## Current result

The real Phase C Discovery replay already reports:

- retrieved evidence: 316 tokens;
- Recall@8: 1.0;
- MRR: 1.0;
- retrieval latency: 27.209 ms;
- candidate/rejected/future/POV leakage: zero.

Discovery invokes the Context Engine with `as_of_chapter = target - 1`, the current POV character, safe-writing eligibility, no conversation history, and top-8 Phase C retrieval. Its provider packet then contains the P0-labelled context.

## Finding

Progressive retrieval has no material measured opportunity here. Even eliminating half the 316 evidence tokens would save only 158 tokens while adding routing, expansion state, and failure modes. Discovery's problem is not evidence volume.

## Recommendation

**Leave Discovery unchanged.**

Do not add fact/episode/raw staging for architectural symmetry. If future long-project telemetry shows Discovery packets growing materially, rerun this audit against those real packets. Until then, Phase C's compact retrieval is the simpler and safer design.

No Discovery provider call was made in this audit. Evidence source: `artifacts/memory-phase-c/discovery-phase-c-final.json`.
