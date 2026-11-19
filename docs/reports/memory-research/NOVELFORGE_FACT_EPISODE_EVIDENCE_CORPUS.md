# NovelForge Fact / Episode / Evidence Corpus

## Corpus purpose

This permanent audit corpus distinguishes retrieval relevance from evidence sufficiency. It contains 42 provider-free tasks based on the Memory Fantasy project and the established long-scale fixtures.

## Coverage

- 10 Story Studio questions;
- 10 Develop Story specialist tasks;
- 8 structured-writing/continuity tasks;
- 8 conflict, chronology, knowledge, rejection, and revision cases;
- 6 long-range callback cases.

The corpus includes current ownership, historical ownership, Elias chronology, Mara/Ivo relationship state and origin, injury/healing, mystery evolution, rejected-villain brainstorming, character-specific knowledge, current revision selection, Chapter 1 callbacks, forgotten artifacts, exact dialogue, tone comparison, and subtle foreshadowing.

## Labelling contract

Each case records:

- consumer and task;
- minimum evidence level;
- fact, episode, and raw evidence references;
- markers required for a correct supported response;
- token count at each stage;
- sufficiency result at every stage.

Fact cases must be complete at Level 1. Episode cases must fail Level 1 and pass Level 2. Raw cases must fail through Level 2 and pass Level 3. The runner asserts these conditions.

## Important limitation

The 35.71/45.24/19.05 distribution describes this deliberately varied readiness corpus. It is not telemetry-derived production traffic frequency. Product rollout decisions should collect real anonymous task-class counts locally before treating the percentages as forecast usage.

## Artifacts

- Definitions and evidence catalog: `artifacts/memory-phase-d/labelled-corpus.json`
- Evaluated results: `artifacts/memory-phase-d/sufficiency-results.json`
- Reproducible runner: `scripts/run_memory_phase_d_readiness.py`

No new memory store or schema was created. The corpus is diagnostic data only.
