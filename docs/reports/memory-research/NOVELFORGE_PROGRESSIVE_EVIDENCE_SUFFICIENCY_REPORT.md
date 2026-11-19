# NovelForge Progressive Evidence Sufficiency Report

## Method

Each case declares required facts and observable markers. The shadow evaluator accumulates Level 1 facts, Level 2 episodes, and Level 3 raw evidence, then verifies the first level containing every requirement. It does not ask a model whether it has enough context.

## Corpus result

| Minimum sufficient level | Cases | Share |
|---|---:|---:|
| Fact | 15 | 35.71% |
| Episode | 19 | 45.24% |
| Raw evidence | 8 | 19.05% |
| Total | 42 | 100% |

Correct labelled evidence was present at the declared minimum level in 42/42 cases. This is evidence-packet correctness, not generated-answer quality.

## Consumer findings

| Consumer group | Fact | Episode | Raw | Interpretation |
|---|---:|---:|---:|---|
| Story Studio | 4 | 5 | 1 | current-state/decision questions are compact; why/history usually needs episodes |
| Five Develop Story roles | 4 | 5 | 1 | progression work is mainly episodic; Pacing prose analysis needs raw text |
| Structured writing | 2 | 2 | 4 | exact wording, tone, and emotional consistency often require prose |
| Conflict/revision | 3 | 4 | 1 | conflicts need both current fact and state-transition context |
| Long range | 2 | 3 | 1 | atomics recover objects/promises; origin and foreshadowing need deeper evidence |

## Conflict behavior

For the real Elias contradiction, Level 1 returns confirmed planning: five years. Level 2 adds the derived Chapter 2 “two years” episode as a labelled conflict. Level 3 is needed only when explaining the exact approved-prose source. The derived value never receives equal authority.

Equivalent tests cover ownership transitions, relationship evolution, healed injury state, knowledge scope, rejected ideas, and revision lineage. Facts state the current valid result; episodes explain transitions; raw evidence supports exact wording or version adjudication.

## What facts cannot do

Facts alone cannot reliably explain cause, progression, emotional origin, clue evolution, or paragraph-level tone. In the matched Develop Story workflow, fact-only passed 0/5 role-depth checks even though hard authority terms were present. Therefore Phase D must not equate smaller context with sufficient context.

## Trigger recommendation

Use deterministic task/role rules plus conflict/confidence rules:

- current state, owner, decision, open/closed state: fact;
- why, how, changed, evolved, progression, causal planning: episode;
- exactly, quote, wording, tone, subtlety, dialogue callback, revision comparison: raw;
- conflict, low confidence, multiple valid historical states: automatically include the resolving episode and authority label;
- model-requested evidence: optional bounded escape hatch only after deterministic routing fails, not the normal path.

Machine evidence: `artifacts/memory-phase-d/sufficiency-results.json`.
