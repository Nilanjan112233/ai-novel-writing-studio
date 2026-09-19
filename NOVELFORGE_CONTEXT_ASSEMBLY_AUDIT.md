# NovelForge Context Assembly Audit

**Audit date:** 2026-08-13  
**Method:** static runtime-path tracing plus read-only inspection of persisted context packets and provider traces. Token counts below are the application's estimates or trace-recorded counts; no paid call was made for this audit.

## Finding

NovelForge does not have one universal context builder. It has three materially different paths:

1. **Discovery next-chapter writing:** `ContextEngine` authority-first packet plus Native hits.
2. **Structured scene writing:** broad NarrativeStudio state internally, then a smaller writing-specific projection.
3. **Story Studio / Develop Story:** Narrative Analysis for conversational answers; full Story Bible and accumulating outputs for most planning specialists.

The separation is sensible, but budgets, authority filters, deduplication, and chronology policy are inconsistent.

## Real next-chapter ordering

For Chapter 2 of `Memory Fantasy Experiment`, the actual Discovery path was:

```text
Author instruction
  -> project + cycle marker + latest timeline messages (active context)
  -> active canon (up to 40)
  -> approved/resolved decisions (up to 30)
  -> confirmed non-candidate timeline (up to 40)
  -> confirmed/approved characters (up to 12)
  -> unresolved confirmed plot threads (up to 10)
  -> themes (up to 3)
  -> continuity reports (up to 5)
  -> unanswered confirmed questions (up to 8)
  -> Native query = task + last 8 active messages
  -> Native top 8 hits, safe-for-writing
  -> latest 5 compressed cycle summaries
  -> trim Native hits, then active context, only if total > 24,000
  -> Discovery writer prompt
  -> optional Range Editor / continuation / compression
  -> provider routing/failover
```

This comes from `context_engine.py:33-113` and `discovery_writing_service.py:110-230`. The ContextEngine does **not** inject the full Story Bible or Narrative Analysis snapshot directly. Those can be represented indirectly through indexed source documents and structured owner rows.

## Measured real packet

Chapter 2 packet total: **5,428 estimated tokens**.

| Packet source | Tokens | Share | Observation |
|---|---:|---:|---|
| Task | 83 | 1.5% | Author instruction |
| Active context | 107 | 2.0% | Project and cycle marker |
| Working/authority context | 1,210 | 22.3% | Timeline, three characters, one plot thread, two continuity reports |
| Native retrieved memory | 3,988 | 73.5% | Dominated by two versions of the same Chapter 1 intelligence |
| Compressed memory | 0 | 0% | No cycle compaction for this path/project |
| **Total** | **5,428** | **100%** | Within 24k cap, so no trimming occurred |

### What the eight Native hits were

| Hit | Approx. tokens | Role / problem |
|---|---:|---|
| Chapter 1 intelligence, representation A | 2,110 | Useful episodic context, but internally repetitive |
| Chapter 1 intelligence, representation B | 1,416 | Same logical record; word-set Jaccard similarity 0.916 |
| Plot thread | 86 | Repeats working-memory plot state |
| Project | 118 | Repeats active project information |
| World | 65 | Useful but not authority-labelled in the hit packet |
| Elias character | 60 | Repeats a structured character row |
| Ivo character | 66 | Repeats a structured character row |
| Mara character | 61 | Repeats a structured character row |

The two continuity reports contributed about 352 tokens and were 92.8% similar; both reported PASS.

## Missing and conflicting information in the real packet

- Confirmed planning said Elias disappeared five years earlier.
- Derived extraction/intelligence attributed that disappearance to Lindon and inferred an identity substitution.
- Chapter 2 prose said Mara last saw Elias two years earlier and had been in Northglass for three months.
- Chapter 2 switched from Chapter 1's third-person limited voice to first person.
- A relationship extraction described Mara as Lindon's brother.

The validation path did not stop these conflicts. This demonstrates that authority precedence in the prompt is insufficient when a very large derived record dominates attention and the continuity layer is weak.

## Structured scene-writing packet

The structured path is different:

1. `DraftingService` loads the scene/chapter/arc, linked characters, relationships, world, timeline, foreshadowing, knowledge, artifacts, progressions and dependencies.
2. It includes a bounded previous-approved-scene excerpt of about 2,400 characters.
3. `build_persistent_state` loads canon, decisions, rejected decisions, confirmed Story Studio planning, Story Bible, arc and orchestration state.
4. NarrativeStudio performs Native recall and agent-memory retrieval.
5. The Scene Writer receives project, drafting context, arc, a bounded `_writing_story_context`, recent chapter memory, canon, decisions, confirmed planning, rejected decisions and agent memory.

Important inconsistency: general `retrieved_memory` is assembled and recorded for the agent, but the final Scene Writer prompt does not include that field. Planning specialists do receive up to 20 hits. The bounded Story Bible projection is therefore the structured writer's main derived context.

## Story Studio context

### Read-only question

The Narrative Assistant uses:

- project identity and requested question;
- current Narrative Analysis snapshot;
- writing state and requested chapter context;
- confirmed planning;
- supporting findings/nodes.

Raw prior Narrative Assistant messages are persisted but are not replayed as a chat transcript. This prevents casual old conversation from automatically becoming writing context, but it also means conversational preference continuity is limited.

### Planning

The current user message can produce candidate projections. Only explicitly confirmed Story Studio planning is added to governed planning context. Rejected candidates remain history and should not enter the writer packet.

### Writing

Story Studio delegates to the Discovery path above. It does not have a separate writer memory system.

## Develop Story context

For a planning specialist, the prompt generally receives:

- project;
- up to 20 recent messages;
- up to 60 canon records;
- up to 60 decisions;
- up to 120 confirmed planning items;
- up to 30 rejected decisions;
- up to 20 Native hits;
- per-agent memory;
- active arc;
- earlier cycle outputs;
- recent chapter memory;
- **the full reconstructed Story Bible**.

The Story Bible includes authority projections but also large discussion, editorial, workflow, intelligence and approved-content sections. Model windows up to 900,000 tokens mean the “progressive disclosure” loops often do nothing: they trim only after the oversized packet already exceeds the selected budget (`narrative_studio.py:1014-1050`).

## Authority and leakage assessment

| Risk | Status | Evidence |
|---|---|---|
| Candidate planning directly treated as confirmed | Mostly controlled | Owner queries filter candidate/suggested/rejected rows |
| Candidate-derived chapter intelligence influencing prose | **Present** | Chapter intelligence is retrieved as derived memory even when its assertions remain unconfirmed |
| Rejected Story Studio idea leaking through raw chat | Controlled in Native writer | Raw chat is not replayed; Tencent L0 could retrieve it, but safe writing forces Native |
| Stale/superseded owner record | Partially controlled | Some index sources filter authority; others do not |
| Chronology beyond current chapter | **Not explicitly controlled** | Retrieval has no chapter cutoff/as-of filter |
| Old agent output leakage | Possible | Agent outputs and compacted workflow memory can enter later specialists without a story-authority role |
| Authority conflicts | Prompt-labelled, not algorithmically resolved | No conflict gate before final retrieval selection |

## Current budget behavior

- Discovery: explicit total `24,000`, but no per-source or minimum-authority budget.
- ContextEngine default elsewhere: `120,000`.
- Native retrieval: fixed top 8 in ContextEngine, no token-aware hit selection.
- NarrativeStudio: model-window-derived budget up to `900,000`; full Bible retained until overflow.
- Working memory is never trimmed by ContextEngine, even if it alone exceeds the cap.
- Source diversity, chronology coverage and evidence expansion have no explicit budgets.

## Recommended measurement ranges for a V2 pilot

These are experiment ranges derived from the observed 5.4k Discovery packet, current 24k cap, and 33k–80k Develop Story specialist packets—not permanent constants:

| Consumer | Initial compact context | Evidence expansion ceiling | Rationale |
|---|---:|---:|---|
| Discovery/next chapter | 4k–8k memory/state; 12k–24k total | 32k only on explicit unresolved evidence need | Current useful packet is under 5.5k but 30–39% duplicates |
| Structured scene writer | 8k–16k state plus bounded scene evidence | 24k–40k | Preserve current targeted domain packet and adjacent prose |
| Story Studio answer | 4k–12k targeted findings/state | 16k–24k | Current simple questions reached 10.7k prompt tokens |
| Develop Story specialist | 10k–25k role-specific packet | 30k–50k for cross-domain synthesis | Current 33k–80k per specialist contains massive irrelevant sections |

Each pilot should also test 6–12 compact hits, per-source caps, current-chapter/as-of filters, and explicit authority coverage. Numbers must be finalized using replay evaluation, not hard-coded from this audit alone.

## Conclusion

The next-chapter packet is authority-first in construction but text-similarity-heavy in its largest component. The full Story Bible is the primary Develop Story cost driver. V2 should unify authority/chronology filtering, semantic deduplication and progressive evidence expansion while retaining consumer-specific packet shapes.

