# Develop Story Before/After Context Report

## Method

The source snapshot was `Memory Fantasy Experiment`. Both sides used the same instruction and specialist order:

1. Relationship;
2. Character Journey;
3. Mystery;
4. Arc Architect;
5. Pacing.

The current optimized packet completed a real-provider run on `gemini-3.1-flash-lite`. The broad legacy packet repeatedly failed during real-provider execution after one completed specialist. To measure all five legacy prompts without claiming provider success, the five optimized outputs were replayed unchanged through a clean legacy twin. This isolates packet cost and same-cycle accumulation; output equality is exact by construction.

## Matched prompt comparison

| Specialist | Legacy | Optimized | Reduction |
|---|---:|---:|---:|
| Relationship | 77,022 | 4,620 | 94.00% |
| Character Journey | 78,078 | 5,852 | 92.50% |
| Mystery | 80,106 | 5,849 | 92.70% |
| Arc Architect | 81,536 | 8,542 | 89.52% |
| Pacing | 79,894 | 8,688 | 89.13% |
| **Total** | **396,636** | **33,551** | **91.54%** |

## Tokens by source

| Legacy source | Tokens | Optimized replacement | Tokens |
|---|---:|---|---:|
| Full current Story Bible | 340,190 | Role-specific structured projection | 1,338 |
| Native retrieval | 31,908 | Bounded/deduplicated Native retrieval | 15,339 |
| Chapter memory | 16,220 | Role-bounded chapter/episode evidence | 8,953 |
| Confirmed planning copies | 2,155 | Shared typed authority snapshot, including project/canon/decisions/planning | 2,260 |
| Accumulated cycle outputs | 2,331 | Structured delta handoffs | 2,086 |
| Agent memory | 75 | Workflow-only agent memory | 5 |
| New messages | 750 | Instruction | 750 |
| Project + arc focus | 845 | Workflow metadata | 753 |

The dominant saving is removal of the reconstructed full Story Bible from every role. Native retrieval was not the original main problem and remains deliberately substantial.

## High-confidence duplicate removal

The five optimized packets removed 8,496 estimated tokens of exact/logically repeated items before packing. This is separate from the much larger structural saving from not selecting unrelated Story Bible sections.

## Fallback

The matched benchmark used compact mode for 5/5 calls. No broad fallback occurred. A separate complete-suite test confirmed that genuinely oversized mandatory authority falls back with a recorded reason and the model-safe broad budget.

## Artifacts

- `artifacts/memory-phase-e/baseline-provider-failed-run.json`
- `artifacts/memory-phase-e/baseline-replay-provider-run.json`
- `artifacts/memory-phase-e/optimized-provider-run.json`
- `artifacts/memory-phase-e/optimized-replay-provider-run.json`
- `artifacts/memory-phase-e/phase-e-comparison.json`
