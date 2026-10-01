# NovelForge V2 RC8 — Architecture Notes

RC8 is a hardening release. It changes contracts and state transitions inside
the established services; it does not add an agent, narrative graph, writing
pipeline, database authority, or Paragraph Editor capability.

## Supported deployment boundary

RC8 supports a local/private desktop-style NovelForge deployment with a trusted
MongoDB instance and a user-configured provider credential. It is not a claim of
multi-tenant SaaS security. A hosted deployment requires a separate audit of
authentication, authorization, tenant isolation, project ownership, exposed
APIs, secrets, rate limiting, and provider credential custody.

## Preserved authorities

| Concern | Authority retained in RC8 |
|---|---|
| Narrative knowledge | Narrative Analysis Engine, shared graph, and Story Bible |
| Official facts | Canon governance and proposal approval workflow |
| Scene prose | Existing scene-draft lineage and Paragraph Engine |
| Editorial changes | Existing revision branches and version promotion |
| Project loading | Existing Workspace Bootstrap projection/cache |
| Provider access | Existing provider gateway and model registry |
| Guidance | Existing Application Assistant and Workspace Companion |

## Corrected safety contracts

### Author-facing operation failures

The project store owns one persistent operation failure record. Writing,
revision, approval, canon, and assembly failures populate the same shape:
operation, author explanation, preservation statement, retry metadata, optional
destination, and debug-only detail. The workspace-level live region keeps the
failure visible until acknowledgement, a successful retry, or an intentional
state reset.

### Writer's Room

Writer's Room is exploratory. The drafting service snapshots the source state,
creates alternatives as inactive review versions, and checks that source
`active` and `status` fields remain unchanged. Failed rooms remove only partial
room alternatives. Selection, merge, promotion, and activation remain explicit
author operations. The RC8 migration repairs identifiable legacy alternatives
without destructive schema changes.

### Character chronology

Bounded character conversations receive a knowledge-filtered projection rather
than the full future-bearing Story Bible. Allowed evidence is assembled from
chapter-safe canon, timeline, scene, decision, relationship, and memory records.
Generated factual claims are then checked against that boundary. One corrective
generation is permitted; a second unsafe response is rejected before display.

### Atomic idempotency

Scene generation uses the existing stable request ID plus project and scene as
one logical identity. An in-process keyed lock prevents duplicate provider work
in the local deployment, and a unique MongoDB index supplies the persistence
barrier. A losing concurrent insert reuses the established result rather than
surfacing `DuplicateKeyError` or creating another version.

## Provider and validation sequence

```mermaid
sequenceDiagram
    participant UI as Author workspace
    participant Drafting as Existing drafting service
    participant Gateway as Existing provider gateway
    participant Validator as Existing draft validator
    participant DB as MongoDB

    UI->>Drafting: operation plus stable request ID
    Drafting->>Drafting: reuse or acquire logical-operation lock
    Drafting->>Gateway: bounded story labels and narrative context
    Gateway-->>Drafting: normalized Gemini response
    Drafting->>Validator: structural and semantic contract
    Validator->>Validator: resolve labels to stable internal identities
    alt recoverable contract variation
        Drafting->>Gateway: one bounded correction
        Gateway-->>Drafting: corrected candidate
        Drafting->>Validator: validate again
    end
    alt unsafe or invalid
        Drafting-->>UI: visible recoverable failure; prose unchanged
    else valid
        Drafting->>DB: append one immutable version
        Drafting-->>UI: reviewable result and application outcome
    end
```

The model reasons with story labels. Reference reconciliation resolves timeline,
artifact, knowledge, foreshadowing, character, scene, and chapter identities on
the server. Internal IDs remain in persistence and Developer Mode, not ordinary
repair instructions or finding titles.

## Shared analysis changes

POV continuity, manuscript-level prose repetition, and semantic finding
deduplication remain inside the Narrative Analysis Engine/Story Auditor
ownership. One semantic issue receives one stable semantic identity and one
score penalty even when several projections observe it. Node and finding labels
prefer story content (`seed`, `event`, `question`, and similar fields) while
machine identity remains separate.

## Scale behavior

Drafting, Editorial, Canon Queue, and Project Timeline now request or render
bounded records with search/filter controls and lazy detail/prose expansion.
Workspace Bootstrap still computes the authoritative projections, reports stage
timings, caches by source token, and exposes staged readiness. No new cache or
source of truth was introduced.

## Observability

Execution traces retain provider transport status and add application outcomes:
provider, parse, validation, reference resolution, persistence, approval
eligibility, and final outcome. Correlation/request identity is carried from UI
through provider, validation, persistence, and analysis so provider HTTP 200 can
still be recorded honestly as an application failure.

## Compatibility

- Existing routes and response fields are preserved; RC8 fields are additive.
- The database architecture is unchanged; indexes and legacy repairs are
  bounded, idempotent migrations.
- The agent roster is unchanged.
- The Paragraph Editor is unchanged except previously verified regression fixes.
- Old records without new explanation or outcome fields remain readable.

