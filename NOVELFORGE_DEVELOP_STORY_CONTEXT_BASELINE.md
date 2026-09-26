# NovelForge Develop Story Context Baseline

## Scope

Develop Story was measured only. Specialist packet contents and role routing were not redesigned. The one P0 change labels its Native recall consumer as `develop_story_specialist`; Tencent remains observational and Native remains the safe-writing primary.

The harness replays stored context records for project `6a78d47d4f0c63bfcbcbc17f`:

| Cycle | Stored packets | Total estimated prompt tokens | Median | First five specialist tokens |
| ---: | ---: | ---: | ---: | --- |
| 2 | 5 | 208,737 | 43,004 | 32,632; 35,347; 43,004; 46,936; 50,818 |
| 3 | 20 | 2,271,465 | 114,482 | 67,209; 73,558; 76,535; 77,900; 79,986 |

Cycle 3 contains the five planning specialists followed by editorial/revision/governance work, so its 20-packet total must not be described as a five-specialist-only cost. Across all 25 stored packets the estimate is 2,480,202 tokens.

## What can be attributed historically

The old context record stores full-context token estimate and a compact packet projection, not the exact final role-specific prompt. It confirms 2,633–3,367 retrieved-memory tokens for cycle-2 specialists and 2,908–3,294 for the first five cycle-3 specialists, but cannot faithfully allocate the unrecorded remainder by Story Bible section. That gap is reported rather than reconstructed from assumptions.

Future context packets now store:

- tokens for every full context source;
- tokens for each final role-specific prompt source;
- actual serialized prompt token estimate;
- flags for Story Bible/confirmed-planning, Story Bible/chapter-memory, and prior-agent-output overlap.

This instrumentation does not change prompt content.

## Baseline conclusion

Native retrieved memory is not the main cause of the 32k–80k first-five specialist packets; it is about 2.9k–3.4k tokens in the captured examples. The dominant unallocated material is the broad Story Bible/current plan, chapter memory, planning projections, and growing same-cycle context. Later cycle-3 packets rise above 100k, confirming accumulation beyond retrieval alone.

The later target of at least 50% prompt reduction remains plausible but unproven. It must be assessed on newly attributed packets with specialist quality labels. This pass deliberately does not remove Story Bible sections, build delta handoffs, or change specialist packets.

