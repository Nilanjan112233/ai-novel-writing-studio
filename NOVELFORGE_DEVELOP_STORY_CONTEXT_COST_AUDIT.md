# NovelForge Develop Story Context and Cost Audit

**Audit date:** 2026-08-13  
**Method:** runtime call-path trace plus persisted context packets, agent memory, Story Bible sections and execution traces. No new model calls were made.

## Executive finding

Develop Story's principal cost problem is not the number of specialists. It is that most specialists receive the full reconstructed Story Bible and accumulating prior outputs. A real five-specialist cycle grew from 32.6k to 50.8k estimated context tokens within one cycle; the next cycle ranged from 67.2k to 80.0k. The specialist outputs themselves were only about 8k response tokens per cycle.

The workflow can likely reduce prompt tokens 55–75% without fewer specialists by sending role-specific state and compact, provenance-linked handoffs. That estimate must be validated by blind output review.

## Actual specialist call path

```text
Author clicks Develop Story / sends develop request
  -> DevelopmentStateService creates/resumes cycle
  -> orchestration chooses explicit specialist plan
  -> build_persistent_state loads project, current trigger messages,
     canon, decisions, rejected decisions, confirmed planning, Story Bible
  -> for each specialist, sequentially:
       Native safe recall
       sync canon/decisions into agent core memory
       load recent/important/compressed/core agent memory
       reconstruct context including full Story Bible and prior outputs
       trim only if model-window budget exceeded
       call provider
       persist agent output and memory
       refresh structured/live Story Bible state
       next specialist receives the expanded state
```

Implementation evidence: `backend/app/services/narrative_studio.py:902-1075,1230-1250,2145-2172` and `backend/app/services/agent_memory_service.py:11-17,106-285`.

## Real measured project

Project `Real Creative Workflow 2026-08-10` selected five specialists in cycles 2 and 3:

- Relationship Agent;
- Character Journey Agent;
- Mystery Agent;
- Arc Architect Agent;
- Pacing Agent.

### Cycle 2

| Specialist order | Stored context estimate |
|---:|---:|
| 1 | 32,632 |
| 2 | 35,347 |
| 3 | 43,004 |
| 4 | 46,936 |
| 5 | 50,818 |

Actual provider traces: 195,572 prompt tokens, 7,732 response tokens, approximately $0.203304 recorded cost.

### Cycle 3

| Specialist order | Stored context estimate |
|---:|---:|
| 1 | 67,209 |
| 2 | 73,558 |
| 3 | 76,535 |
| 4 | 77,900 |
| 5 | 79,986 |

Actual provider traces: 360,324 prompt tokens, 8,186 response tokens, approximately $0.368510 recorded cost. The five stored packets summed to about 375,188 context tokens.

The cycle-3 prompt total was 84% higher than cycle 2, even though the specialist set remained the same.

## Where duplication comes from

### Full Story Bible for each specialist

The live reconstructed Story Bible was about 164k tokens by a characters/4 estimate. The largest sections were:

- discussion: 62.6k;
- editorial: 45.5k;
- story intelligence: 22.7k;
- workflow: 7.1k;
- interactive: 3.5k;
- approved content and drafting: about 6.1k combined.

A Mystery specialist rarely needs the entire editorial discussion; a Pacing specialist rarely needs every raw relationship discussion. The current packet treats them alike until a very large model budget is exceeded.

### Earlier outputs sent in multiple forms

Prior specialist work can appear as:

- `cycle_outputs`;
- refreshed Story Bible discussion/editorial/workflow sections;
- `agent_outputs` retrievable through Native memory;
- per-agent recent/important memory;
- compressed cycle memory.

These layers are individually defensible but jointly redundant.

### Duplicated authority

Canon and decisions are sent directly and also copied into per-agent core memory. Confirmed planning appears directly and through Story Bible projections. This is a safe orientation mechanism, but prompts need a single compact display with pointers, not multiple copies.

### Repeated instruction and project framing

Every specialist receives the same user instruction and project identity. Some repetition is required across separate provider calls; verbose framing is not.

## Agent memory quality

Agent memory is bounded by tier and has provenance/version fields. In the real project, specialists had recent and important documents totaling roughly 825–1,153 tokens each. Compaction archives older recent memories into a summary with source IDs. This is useful short-term workflow memory.

Problems:

- tier names L1/L2/L3 do not create story-aware atomic/episode/profile memory;
- important/recent summaries can repeat `agent_outputs` and Story Bible content;
- accepted versus rejected recommendation status is not the primary retrieval key;
- current compaction is summary concatenation, not a structured delta ledger;
- specialists have no on-demand evidence tool in place of preloaded context.

## What each specialist actually needs

| Specialist | Mandatory shared context | Role-specific context | Usually not needed initially |
|---|---|---|---|
| Relationship | authority snapshot, active arc/chapter, author instruction | involved characters, relationship history/deltas, knowledge boundaries, relevant scenes | full editorial/workflow history |
| Character Journey | same | character states, goals, arc beats, decisions, relevant episodes | unrelated world/plot discussion |
| Mystery | same | mystery truth/clues/red herrings, knowledge, chronology, open obligations | all character/editorial prose |
| Arc Architect | same | arc goals, chapter/scene plans, plot/mystery/character deltas | detailed paragraph/editorial history |
| Pacing | same | episode durations, scene/chapter beats, escalation, word/length targets | full factual registries unless linked |
| Cross-domain synthesizer | same | compact outputs from every specialist plus conflicts | raw full outputs unless evidence requested |

## Proposed compact handoff

Each specialist output should yield a derived workflow handoff:

```text
specialist / cycle / output version
claims and recommendations
affected owner IDs / chapter / arc
constraints preserved
conflicts or unresolved questions
accepted / rejected / pending status
evidence pointers
token estimate
```

Later agents receive the handoff, not the full earlier prose. They can request the referenced output or source evidence when necessary. Story state changes remain proposals until existing authority workflows confirm them.

## Do agents need persistent workflow memory?

Yes, for:

- accepted/rejected recommendations;
- previously attempted approach and why it failed;
- dependencies and unresolved conflicts;
- author criticism scoped to that workflow;
- model/provider validation failures that affect retries.

No, for:

- unselected story alternatives as facts;
- all raw provider responses;
- permanent author style inference from one critique;
- copies of canon/decisions already provided in the shared authority snapshot.

## Token-reduction estimate

A role-specific normal packet of 10k–25k tokens across five specialists would total 50k–125k tokens before occasional evidence expansion. Compared with 195.6k and 360.3k observed prompt tokens, this suggests 36–86% mathematical headroom. Allowing cross-domain synthesis, evidence expansion and serialization overhead, the responsible implementation target is:

> **55–75% fewer Develop Story prompt tokens with non-inferior specialist quality and no authority/continuity regression.**

Do not reduce agent count solely to meet this target.

## Cost governance

The operation-level cost view should aggregate:

- all specialist calls;
- retries/fallbacks;
- post-processing/extraction;
- validation;
- revision/humanization/editorial calls;
- cache hits/misses;
- context tokens by source section.

Current execution traces allow reconstruction, but user-operation metadata does not consistently expose every auxiliary call.

## Recommended next-pass sequence

1. Build a read-only context attribution/replay harness from stored packets and traces.
2. Define role manifests listing mandatory owner types and optional evidence tools.
3. Construct compact shared authority snapshot and per-agent delta handoffs in shadow mode.
4. Compare current versus compact prompts on stored cycles with the same models only after offline checks pass.
5. Blind-review specialist quality, conflict coverage and cross-agent coherence.
6. Enable for one project behind a reversible feature flag only if acceptance criteria pass.

## Acceptance criteria

- at least 50% prompt-token reduction on both measured five-agent cycles;
- no decrease in labelled requirement/constraint coverage;
- no candidate/rejected suggestion promoted to story fact;
- all cross-agent recommendations retain source/output pointers;
- later agents correctly detect seeded conflicts at least as often as current packets;
- blind expert/author rating non-inferior for usefulness, specificity and cross-domain coherence;
- retries and total operation cost fully visible.

