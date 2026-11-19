# Narrative Critique Architecture

## Purpose

Narrative Critique turns existing Story Intelligence evidence into an author-controlled improvement loop. It does not replace Story Health and does not independently build project context.

## Finding contract

Each critique contains:

- severity, explanation, evidence, and confidence;
- affected chapters, scenes, and story elements;
- one suggested improvement;
- the subsystem responsible for helping the author resolve it;
- stable identity and lifecycle status in the shared finding store.

## Detection coverage

The combined Narrative Analysis and critique projection covers plot holes, contradictions, pacing, motivation drift, dialogue inconsistency, missing emotional payoff, unresolved mysteries, weak foreshadowing, dangling plot threads, world/canon/timeline inconsistencies, repetitive scenes, redundant exposition, structural weaknesses, weak hooks and endings, and missing conflict escalation.

Some detections are deterministic projections, while AI reviewer observations can contribute additional evidence. AI evidence never replaces authoritative canon or the author's decision.

## Responsibility routing

| Finding | Owner |
|---|---|
| Canon or world consistency | Canon Intelligence |
| Chronology or travel | Timeline Intelligence |
| Motivation or character behavior | Character Intelligence |
| Dialogue voice | Dialogue Coach |
| Mystery, payoff, or dangling thread | Plot Thread Intelligence |
| Pacing, repetition, hook, ending, escalation | Story Health / Developmental Editor |

## Improvement lifecycle

```text
Evidence -> shared finding -> Story Health impact -> suggested improvement
                                                -> author reviews
                                                -> author edits or defers
                                                -> incremental reanalysis
                                                -> finding resolves or remains open
```

Findings are never applied automatically. Their status may be open, acknowledged, deferred, or resolved. Resolution follows changed evidence, not a hidden AI rewrite.

## API and UI

- `GET /api/projects/{project_id}/narrative-critique`
- `POST /api/projects/{project_id}/narrative-critique/refresh`
- `NarrativeCritiquePanel` presents evidence, confidence, affected locations, routing, and the proposed improvement.

