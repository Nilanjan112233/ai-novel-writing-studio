# NovelForge Phase D Story Studio Study

## Current architecture

Story Studio does not currently use the Develop Story/Discovery Phase C packet as its primary grounding path. The assistant builds a prompt from:

- project framing;
- current writing state;
- confirmed Story Studio planning;
- Narrative Analysis snapshot, matched findings, and nodes;
- bounded chapter context only for explicitly requested chapters;
- application/navigation context.

This distinction matters: implementing Phase D inside Native retrieval would not automatically change Story Studio.

## Labelled questions

The 10-question Story Studio subset produced:

| Minimum evidence | Questions | Share |
|---|---:|---:|
| Fact | 4 | 40% |
| Episode | 5 | 50% |
| Raw | 1 | 10% |

Fact suffices for current injury state, character-specific knowledge, confirmed Elias decisions, and an open promise. Episode depth is needed for why Mara distrusts Ivo, why Northglass matters, Chapter 20 changes, old-clue relevance, and whether a historical clue was established. Raw evidence is needed to explain the exact chronology contradiction.

## Product interpretation

Progressive evidence is conceptually useful for:

- direct answer from current facts;
- “Based on Chapter 8 and confirmed planning” provenance;
- optional “Show why” expansion;
- contradiction and revision explanations;
- historical chapter comparisons.

It is not useful as an automatic prose-loading mechanism for every question.

## Recommendation

Do not change Story Studio in the first Phase D implementation. Its current Narrative Analysis grounding should be audited separately against the same corpus. If later integrated, expose author-friendly provenance and optional evidence, not L1/L2/L3 terminology or retrieval tools.

Machine evidence: Story Studio cases in `artifacts/memory-phase-d/sufficiency-results.json`.
