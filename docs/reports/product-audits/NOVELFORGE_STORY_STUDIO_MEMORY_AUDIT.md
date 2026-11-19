# NovelForge Story Studio Memory Audit

**Audit date:** 2026-08-13  
**Scope:** brainstorming, questions, rejection, confirmed planning, Develop Story discussions, feedback and preferences.

## Finding

Story Studio is not a chat transcript driving the novel. It is an intent router over current story state. That is the right product model. Raw interaction history is persisted for jobs/audit, while only confirmed planning and approved prose should reach writing authority.

The main remaining risk is not direct old-chat replay. It is that candidate or mistaken extraction can be summarized into chapter intelligence and later receive heavy retrieval weight.

## Actual request flow

1. Classify request: question, plan/explore, write, modify, develop or other.
2. Ask for clarification when the change is ambiguous.
3. For planning-like input, extract concrete candidates; vague brainstorming should yield none.
4. Project candidates into existing owner collections with `candidate` status and provenance.
5. Require explicit confirmation/rejection/reconsideration.
6. Route write requests to Discovery Writing, develop requests to Develop Story, and modifications to protected proposal/revision paths.
7. Persist the Story Studio job and optionally send an observational capture to the configured memory provider.

Relevant code: `story_studio_service.py:155-204,361-402,464-723` and `story_knowledge_projection_service.py:137-388`.

## What should be remembered

| Interaction | Persistence | Future influence policy |
|---|---|---|
| Brainstorming alternatives | Raw job history; optional candidate only if concrete | No writer influence until confirmed |
| Clarifying answers | Decision/shared-context/planning owner where explicitly captured | Influence within declared scope |
| Confirmed planning | Owning structured collection with provenance | Yes, below canon/approved prose |
| Rejected ideas | Raw history plus rejected candidate state | Negative constraint/audit only; never story fact |
| Revision instructions | Revision branch/version and operation instruction | Only applied revision changes current prose |
| Author criticism of a draft | Job/revision/editorial context | May guide that revision; not global preference automatically |
| Repeated explicit style preference | Project preference proposal | Active only if explicit/saved, or reviewed inference |
| Chapter feedback | Revision/decision/project preference according to content | Scope must be explicit |
| Develop Story discussion | Job, cycle, outputs, agent memory | Accepted plan changes only after owner/governance workflow |
| Failure/retry recommendation | Workflow memory/telemetry | Helps orchestration; never story truth |

## What must not influence future writing

- rejected, reconsidered or superseded ideas;
- speculative “maybe” statements;
- assistant-generated alternatives the author did not select;
- abandoned revision branches;
- provider errors and fallback text;
- previous agent recommendations merely because they were repeated;
- raw Tencent L0 messages without NovelForge authority/chronology checks;
- a style experiment as a permanent author-global preference.

## Rejection scenario

For:

> Maybe Elias is secretly the villain.

followed by:

> No, forget that idea.

the current Native path is mostly safe:

- raw prior chat is not replayed into the Discovery writer packet;
- a projected planning candidate remains non-authoritative;
- rejection changes candidate and authority status to rejected;
- confirmed-planning context excludes it;
- safe-for-writing recall uses Native even in Tencent mode.

Residual risks:

1. an unfiltered indexed legacy/agent-output source may still contain the phrase;
2. a derived Story Bible, Narrative Analysis or chapter-intelligence projection may retain it until rebuilt/invalidation;
3. Tencent L0 can return the earlier “maybe” in non-safe conversational recall;
4. regex/content invalidation may miss a paraphrase.

V2 should add an explicit supersession link from the rejection event to every derived assertion and invalidate those items transactionally/asynchronously with observable completion.

## Story Studio question context

Narrative Assistant responses use current project state, Narrative Analysis, writing state, confirmed planning and selected findings/nodes. They do not receive the complete old chat transcript. This avoids history pollution, but the inspected simple questions still reached about 10.7k prompt tokens because broad analysis context was included.

Recommended future behavior: retrieve targeted findings and compact facts first, then allow the assistant to request chapter evidence. Preserve source links so an author can ask “why?” without preloading every analysis node.

## Candidate governance quality

Strengths:

- candidates live in existing domain owners rather than a parallel story model;
- authority and candidate status are explicit;
- source type, source ID and chapter provenance are retained;
- confirmation/rejection/reconsideration is author-controlled;
- confirmed Story Studio planning is queried separately from raw chat.

Weaknesses:

- extraction quality can be poor: the inspected project produced chronology, identity and relationship errors;
- candidate records and confirmed records share collections, so every reader/indexer must filter correctly;
- correction of a chapter-intelligence error is indirect;
- invalidation relies partly on content matching rather than explicit derivation dependencies.

## Author preference memory

### Current state

NovelForge persists project fields such as tone, story vision and planning targets, and each request carries its instruction. There is no dedicated governed author preference profile for prose density, dialogue style, POV, pacing, repetitive phrasing, romance intensity or exposition tolerance. Agent “core” memory currently means canon/decisions, not author style.

### Proposed governance

| Scope | Default | How created | Override / expiry |
|---|---|---|---|
| Operation/conversation | Temporary | Current instruction | Ends with operation unless saved |
| Project | Preferred durable scope | Explicit setting or accepted suggestion | Project edit wins |
| Author global | Opt-in only | Explicit author action | Per-project override; revocable |
| Inferred suggestion | Inactive | Multiple consistent author edits/criticisms | Requires review; confidence decay/expiry |

Inference rules:

- never infer permanence from one request;
- require multiple independent author-authored examples;
- record positive and contradictory evidence;
- distinguish “for this chapter” from “for this project”;
- never infer from model-generated prose alone;
- show plain-language suggestions, not confidence algorithms;
- allow accept, edit, dismiss and “do not suggest again.”

## Develop Story and workflow memory

Specialists need short-term memory of:

- the current author instruction;
- assigned role and deliverable;
- accepted/rejected recommendations;
- dependencies on prior specialist outputs;
- unresolved workflow conflicts;
- previous failed approach when retrying.

They do not need every prior discussion/editorial section. Compact handoffs should contain claims, proposed changes, constraints, evidence pointers and acceptance status. The underlying output stays available for drill-down.

## Product implications

No separate “Tencent Memory” author experience is warranted. Story Studio can expose:

- Confirmed from this conversation;
- Suggestions awaiting your review;
- Ideas you rejected;
- Preferences for this project;
- Why NovelForge remembered this;
- Correct or forget this suggestion.

“Forget” must route to a governed status/supersession operation. It must not delete approved prose, canon or audit history.

## Recommendation

Keep Story Studio raw history out of writer prompts. Strengthen candidate-to-derived invalidation, add explicit scoped preference governance, and give Narrative Assistant progressive targeted recall. Tencent may remain a sandbox for conversation/workflow memory only after L1/L2 are genuinely enabled and rejection leakage passes tests.

