# NovelForge Memory Duplication and Token Audit

**Audit date:** 2026-08-13  
**Scope:** read-only packet, Story Bible and execution-trace analysis. Costs are trace-recorded estimates, not invoices.

## Executive finding

Native NovelForge wastes context in two different ways:

1. The next-chapter path repeats the same fact across owner records, continuity reports and chapter intelligence, including a confirmed duplicate index defect.
2. Develop Story repeatedly sends the full Story Bible and growing prior-agent outputs to every specialist.

The first is a 30–39% direct-removal opportunity in the inspected real packet. The second appears to offer roughly 55–75% prompt reduction in the inspected five-agent cycles, subject to quality-preserving replay tests.

## Real Chapter 2 duplication

Project: `Memory Fantasy Experiment`; packet: 5,428 tokens.

### Confirmed duplicate categories

| Duplication | Estimated removable tokens | Evidence |
|---|---:|---|
| Same logical Chapter 1 intelligence indexed twice | ~1,416 | Two hits, Jaccard 0.916; one indexed by `intelligence_id`, one later by Mongo `_id` |
| Two near-identical PASS continuity reports | ~175 | 352 combined tokens; 92.8% similar |
| Project repeated in active and Native memory | ~118 | Project hit overlaps active project context |
| Character/world/thread re-expression | ~187 | Native hits overlap structured working records |
| **Conservative directly removable** | **~1,600–2,100** | **30–39% of the packet** |

Replacing the 3,526 tokens of duplicated/repetitive chapter-intelligence prose with provenance-linked atomic and episodic records could reduce about 2,500–3,300 tokens (46–61%) in this packet, but that larger range is a design estimate requiring retrieval-quality validation.

## Why chapter intelligence is large

The same events recur under chapter summary, important events, mysteries introduced, unresolved questions, future obligations, character developments and extraction candidates. These fields serve product views, but concatenating or serializing them as one retrieval document converts useful structure into verbose repetition. The ranking algorithm then gives chapter intelligence a type boost, so it can crowd out smaller authoritative facts.

## Cross-system duplication map

| Fact or event | Common representations | Risk |
|---|---|---|
| Approved chapter event | Prose, discovery extraction, chapter intelligence, Story Bible approved content, Narrative Analysis node/finding, memory embedding | Repeated tokens and conflicting paraphrases |
| Character state | Character Bible, chapter intelligence, agent output, Story Bible character section, analysis graph | Stale state can outrank owner record |
| Mystery/thread | Mystery registry, plot thread, chapter intelligence, unanswered question, Story Bible, analysis finding | Same open loop presented multiple times |
| Chronology | Timeline entry, prose, chapter intelligence, analysis graph, Story Bible | No single `as_of_chapter` filter in Native recall |
| Confirmed planning | Owner collection, Story Bible, agent core memory, full planning prompt | Redundant copies of authority |
| Specialist recommendation | Agent output, agent recent memory, Story Bible discussion/editorial/workflow sections, later cycle outputs | Develop Story packets expand every cycle |
| Recent prose | Direct adjacent excerpt, approved-content Story Bible section, chapter intelligence, Native hit | Evidence and summary both injected without a need gate |

## Develop Story measured cost

Project: `Real Creative Workflow 2026-08-10`; five specialists: Relationship, Character Journey, Mystery, Arc Architect and Pacing.

| Cycle | Context packet estimates by specialist | Prompt tokens across 5 calls | Response tokens | Recorded cost |
|---|---|---:|---:|---:|
| 2 | 32,632; 35,347; 43,004; 46,936; 50,818 | 195,572 | 7,732 | $0.203304 |
| 3 | 67,209; 73,558; 76,535; 77,900; 79,986 | 360,324 | 8,186 | $0.368510 |

Cycle 3 sent about 375,188 estimated context tokens before prompt serialization. The same author instruction was repeated five times, and later agents received refreshed Story Bible content containing earlier agents' outputs in addition to cycle-output handoffs.

### Story Bible sections driving the packet

Approximate current sizes for the real project, estimated as characters / 4:

| Section | Tokens |
|---|---:|
| Discussion | 62,610 |
| Editorial | 45,484 |
| Story intelligence | 22,690 |
| Workflow | 7,103 |
| Interactive | 3,468 |
| Approved story content | 3,049 |
| Drafting | 3,058 |
| Arc development | 2,304 |
| Characters | 2,048 |
| Remaining structured sections | ~12,000 |
| **Approximate reconstructed total** | **~164,000** |

Most planning specialists receive this reconstructed object even when a large section is unrelated to the specialist's role.

## Chapter generation and extraction cost

For real Chapter 2:

| Call | Prompt | Response | Trace total | Recorded cost | Note |
|---|---:|---:|---:|---:|---|
| Discovery Writer | 5,949 | 204 | 6,153 | $0.006153 | Produced only 153 words |
| Range Editor | 475 | 2,046 | 2,521 | $0.002521 | Expanded to 1,534 words |
| Extraction, failed Gemini | 2,259 | 0 | 2,259 | $0.000904 | Fallback required |
| Extraction, successful OpenRouter | 2,259 | 1,022 | 3,281 | $0.003281 | Successful structured result |

The recorded trace total for writer + range edit + successful extraction is 11,955 tokens and $0.011955; including the failed extraction attempt gives 14,214 accounted prompt/response tokens and about $0.012859. Draft-level generation metadata did not fully expose the range-edit and extraction cost, so product cost reporting is incomplete.

Chapter 1 showed a similar extraction retry: the writer used 5,618 prompt/response tokens, while Gemini extraction failed after a 3,510-token prompt before an OpenRouter call used 5,143 tokens.

## Story Studio question cost

Two simple Narrative Assistant questions on the inspected project each had approximately 10,659 prompt tokens and about $0.011 recorded cost. The likely driver was the Narrative Analysis/context snapshot, not raw conversation replay.

## Savings opportunities, without optimizing yet

| Opportunity | Expected effect | Risk / required proof |
|---|---|---|
| Canonical logical source ID for each derived record | Removes duplicate embeddings immediately | Low; migration must deactivate duplicate versions safely |
| Semantic/field-aware dedup before selection | Removes owner/summary re-expression | Must keep highest-authority source and evidence pointer |
| Atomic facts first, episode second, raw prose on demand | Shrinks normal packets by thousands of tokens | Extraction errors must never become authority |
| Role-specific Story Bible views | Largest Develop Story saving | Must preserve cross-domain signals for synthesis agents |
| Delta handoffs between specialists | Stops resending entire prior output set | Need dependency graph and concise lossless references |
| Per-source token budgets and source diversity | Prevents chapter intelligence domination | Must guarantee authority minimums |
| Provider retry/correction accounting | Improves cost visibility | Does not itself save tokens |
| Deterministic validation before paid extraction retry | Avoids some failed calls | Must not replace higher-quality extraction where needed |

## Estimated opportunity ranges

- **Discovery next chapter:** directly measured 30–39% removable duplication; 46–61% is plausible with compact derived memory, not yet proven.
- **Develop Story:** a tailored 10k–25k packet for each of five specialists would total 50k–125k versus the observed 195k–360k prompt tokens. After allowing shared synthesis/evidence expansion, a conservative implementation target is **55–75% fewer prompt tokens** with non-inferior specialist outputs.
- **Story Studio questions:** targeted finding selection should aim for 25–50% lower prompt tokens on simple questions while preserving cited evidence.
- **Extraction retries:** savings are workload-dependent; the inspected chapters show that retry overhead can rival the writer call.

These are opportunity estimates, not guaranteed production savings.

## Cost priorities

1. Stop full Story Bible delivery to every planning specialist.
2. Fix duplicate chapter-intelligence identity and semantic dedup.
3. Add progressive compact-to-evidence retrieval.
4. Measure all provider attempts and correction passes as one user operation.
5. Tune extraction retries only after correctness gates are reliable.

