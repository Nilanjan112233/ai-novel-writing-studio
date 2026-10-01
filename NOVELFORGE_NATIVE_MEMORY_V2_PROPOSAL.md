# NovelForge Native Memory V2 Proposal

**Status:** design only; no implementation performed.  
**Recommendation:** Native plus selected Tencent-inspired concepts, adapted to NovelForge's story authority.

## Design objective

Return the smallest set of correct, chronologically valid, provenance-linked story information needed by each consumer, while expanding to episode summaries or raw prose only when compact memory is insufficient.

## Non-negotiable invariant

```text
Memory retrieval may explain or locate story authority.
Memory retrieval may never create, override, or silently promote story authority.
```

Approved prose, active canon, author decisions and confirmed planning remain in their existing owner collections. All V2 memory is rebuildable derivation.

## Proposed architecture

```text
AUTHORITATIVE OWNERS
  approved prose | canon | decisions | confirmed planning | current revision
          |
          | project events / owner version changes
          v
DERIVATION LEDGER (rebuildable)
  source owner + source version + as-of chapter + authority + evidence pointers
          |
          +-- atomic assertions
          +-- chapter/scene episodes (improved chapter intelligence)
          +-- computed progression views (relationship, mystery, artifact, arc)
          +-- open-thread obligations
          +-- character-knowledge assertions
          +-- governed project/author preferences
          |
          v
RETRIEVAL CANDIDATE GENERATION
  metadata/authority filters + BM25 + semantic embedding + graph candidates
          |
          v
STORY-SPECIFIC RANKING
  authority > validity/chronology > explicit task links > semantic/lexical
  + graph proximity + narrative importance + unresolved priority + recency
          |
          v
SELECTION
  logical + semantic dedup | source diversity | per-source budgets
  | mandatory authority coverage | token-aware packing
          |
          v
PROGRESSIVE DELIVERY
  compact assertions first
       -> episode/progression if confidence or coverage insufficient
       -> raw prose/evidence only for verification or precise voice/continuity
          |
          v
consumer-specific packet: Writer | Story Studio | Develop Story | Editorial
```

## Derived-memory contract

Every derived item should contain, conceptually:

- stable derived ID and derivation type;
- project and optional branch/arc/chapter/scene scope;
- subject, predicate, object or structured episode fields;
- `authority_source_type`, `authority_source_id`, `authority_source_version`;
- evidence spans/pointers, not copied authority;
- `valid_from_chapter`, optional `valid_to_chapter`, and `observed_at_chapter`;
- character knowledge scope: who knows/does not know and as of when;
- derivation confidence and extractor/model version;
- active/superseded state and reason;
- content hash and logical identity;
- rebuild generation/version.

Deleting all derived V2 records and rebuilding from owners must preserve the story unchanged.

## Atomic memory

### Recommendation

Add compact atomic assertions as a retrieval projection, not a new story database.

### Sources

1. Direct deterministic projection from confirmed owner records.
2. Approved prose extraction, labelled derived until linked to a confirmed owner or used only as prose evidence.
3. Chapter intelligence fields after consistency validation.
4. Canon/decision versions, represented as pointers with compact display text.

### Example

```text
subject: Mara.left_palm
predicate: injury_state
object: injured
valid_from_chapter: 4
authority: approved_prose_observation
evidence: chapter_draft/<id>/version/2#span-17
```

This assertion helps retrieval; it does not update the character record or canon.

### Deduplication and supersession

- Use domain logical keys, not Mongo `_id`, for identity.
- Exact duplicates merge evidence pointers.
- Semantically equivalent values consolidate after normalized domain comparison.
- Conflicts remain side by side with authority and valid-time labels; they are not averaged.
- An owner version change emits invalidation for every derived item that points to the old version.
- Later chapter state closes `valid_to_chapter`; it does not erase historical state.

## Episode and scenario memory

Do not create a generic new “scenario authority.” Improve chapter intelligence into a compact episode view:

- ordered events;
- participating characters and state deltas;
- knowledge gained/lost by character;
- relationship changes;
- mystery/thread changes;
- artifact ownership/state changes;
- chronology anchors;
- unresolved obligations;
- evidence pointers.

Cross-chapter progression views should be computed from episodes and owner records for a query (for example, “Northglass ownership history”), cached if useful, and always drill down to chapters. Story Bible and Narrative Analysis remain product projections; they should consume or link to the same derivation ledger rather than duplicate assertions independently.

## Author preference memory

### Scope order

1. **Explicit project preference** — default and highest preference authority.
2. **Conversation/session instruction** — applies only to the named operation unless saved.
3. **Inferred project suggestion** — never active until reviewed or repeatedly confirmed.
4. **Author-global preference** — explicit opt-in only, with project override.

### Governance

- One request is insufficient for a permanent inference.
- Store evidence count, recency, confidence, scope and contradiction examples.
- Let the author accept, edit, dismiss, expire or make project-only.
- Separate prose style from story facts and canon.
- Allow scene/chapter exceptions without changing the profile.
- Do not learn from provider-generated text as though it were an author preference.

## Retrieval model

### Stage 1: hard filters

- project/branch isolation;
- active source version;
- candidate/rejected/stale exclusion for writing;
- chapter `as_of` boundary;
- character-knowledge boundary;
- consumer and role eligibility;
- explicit arc/scene/entity constraints.

### Stage 2: candidate generation

- BM25/keyword for names, objects, exact phrases and rare story terms;
- real semantic embeddings for paraphrase/meaning;
- graph neighbors from active characters, location, arc, thread and artifacts;
- mandatory authority records directly linked from the task/plan.

### Stage 3: fusion and story ranking

Use rank fusion (RRF is a reasonable starting point) across lexical, semantic and graph candidate lists, then apply bounded story-specific features. The priority order should be:

1. authority and source validity;
2. chronology/as-of correctness;
3. explicit plan/entity relation;
4. unresolved obligation or current state relevance;
5. character-knowledge relevance;
6. semantic and lexical relevance;
7. narrative importance;
8. graph proximity;
9. recency, used as a tiebreaker rather than truth.

Scores from different providers must not be directly sorted without normalization/fusion.

### Stage 4: selection

- group by logical fact/event;
- retain highest authority plus distinct evidence;
- enforce source diversity;
- pack by token utility rather than fixed top-k alone;
- reserve mandatory space for canon/decisions/confirmed planning relevant to the task;
- label every derived item and conflict.

## Progressive retrieval

```text
1. Resolve authority and task entities.
2. Retrieve compact assertions and open obligations.
3. Check coverage/confidence/conflicts.
4. If insufficient, add relevant chapter/progression episodes.
5. If exact voice, disputed fact or chronology proof is needed, add bounded prose spans.
6. Stop when coverage is met or budget exhausted; report unresolved conflict.
```

“Enough” should be measurable: all mandatory plan entities covered, no unresolved high-authority conflict, chronology anchors present, and confidence above a replay-calibrated threshold.

## Initial budget ranges for evaluation

These ranges are based on observed packets and must be calibrated in shadow mode:

| Budget | Pilot range |
|---|---:|
| Compact hits | 6–12 |
| Compact derived memory | 1.5k–3k tokens |
| Recent chapter episodes | 2–4 chapters, 1.5k–4k tokens |
| Older relevant memory | 1k–3k tokens |
| Raw evidence expansion | 2k–6k tokens per expansion, normally one |
| Discovery total story context | 12k–24k tokens |
| Structured scene total story context | 16k–40k tokens |
| Develop specialist normal packet | 10k–25k tokens; 30k–50k synthesis ceiling |

Budget policy must express a minimum authority set and per-source caps; a single chapter summary cannot consume most of the packet.

## Develop Story redesign

- Build a shared cycle manifest once: instruction, authority snapshot IDs, active arc/entity IDs and packet version.
- Give each specialist a role-specific slice, not the full Story Bible.
- Pass compact deltas from prior agents: claims, recommendations, conflicts, changed owner/proposal IDs and evidence pointers.
- Persist workflow memory about accepted/rejected recommendations and failures, but never merge it with story facts.
- Let cross-domain synthesis agents request expansion rather than preloading every section.

## Product implications

Most implementation should remain invisible. Useful author-facing concepts are:

- **What NovelForge remembers** — current confirmed facts and preferences;
- **Current story context** — the compact packet for a chapter, with source labels;
- **Suggestions from your writing** — candidate-only;
- **Open threads** — unresolved, chapter-aware obligations;
- **Why this was included** — evidence/provenance drill-down;
- **Forget/correct this** — routes to the owning authority record, never deletes evidence silently.

Do not expose L0/L1/L2/L3, embeddings, providers, RRF or token budgets in the normal author workflow.

## Explicit non-goals

- No second Story Bible, canon, graph, timeline, character or writing database.
- No Tencent-owned story truth.
- No automatic candidate promotion.
- No permanent preferences inferred from one request.
- No whole-manuscript prompt at long scale.
- No destructive rewrite of existing memory embeddings before shadow validation.
- No raw conversation recall in safe writing unless a specific, governed evidence expansion requests it.

## Acceptance criteria for implementation

1. Zero candidate/rejected/stale/future-chapter leakage in a labelled regression set.
2. All retrieved assertions have valid owner version and evidence pointer.
3. Duplicate logical chapter-intelligence hit defect eliminated.
4. Important-memory recall@k and first-relevant rank non-inferior to current Native on 10/25/50/100/250/500 chapter corpora.
5. Chronology and character-knowledge tests pass at every scale.
6. Real two-chapter contradiction/POV case is detected or explicitly surfaced.
7. Discovery context drops at least 25% on the measured packet without losing labelled facts.
8. Develop Story prompt tokens drop at least 50% on the measured cycles with blind specialist-quality non-inferiority.
9. P95 retrieval latency meets a target set after baseline measurement; no silent 2,000-record ceiling.
10. Derived store can be deleted and rebuilt with identical logical outputs from the same authority snapshot.
11. Backup/restore preserves authority and can rebuild V2 without Tencent.
12. Provider-cost telemetry includes initial, retry, range-edit, extraction, validation and editorial calls under one operation ID.

