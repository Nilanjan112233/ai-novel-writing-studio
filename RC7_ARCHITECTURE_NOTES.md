# NovelForge V2 RC7 — Architecture Notes

RC7 is an additive writing-experience release. It preserves the Narrative
Analysis Engine, planning model, database design, public API compatibility,
agent roster, and frozen Paragraph Editor.

## Sources of truth

| Concern | Existing authority | RC7 use |
|---|---|---|
| Planning and author decisions | Current planning records and decision registry | Read into bounded generation context |
| Narrative knowledge | Story Bible and shared Narrative Analysis graph | Reused; never copied into a new graph |
| Paragraph prose | Paragraph Engine content and immutable versions | Preserved during whole-scene generation |
| Scene alternatives | `scene_drafts` lineage | Version A/B/C, favorite, compare, merge, restore |
| Structured revisions | Editorial branches and revision versions | Ten named passes with explicit author promotion |
| Canon governance | Canon Proposal Queue and approval workflow | New AI facts are proposals only |
| Guidance | Workspace Companion and Application Knowledge | Writing-aware actions built from the writing projection |

## Generation sequence

```mermaid
sequenceDiagram
    participant Author
    participant UI as Writing Desk
    participant Drafting as Drafting Service
    participant Context as Existing Narrative Intelligence
    participant Writer as Scene Writer
    participant Validator as Existing Draft Validator
    participant Canon as Canon Proposal Queue

    Author->>UI: Generate draft or focused alternative
    UI->>Drafting: operation + instruction + stable request ID
    Drafting->>Drafting: return existing result when request ID exists
    Drafting->>Context: assemble bounded story and adjacent-scene context
    Drafting->>Writer: generate prose plus explanation
    Writer-->>Drafting: draft candidate
    Drafting->>Validator: preflight candidate without persistence
    alt provider authority violation
        Drafting->>Writer: one corrective retry with evidence
        Writer-->>Drafting: corrected candidate
        Drafting->>Validator: validate again
    end
    alt still invalid
        Drafting-->>UI: friendly failure; no partial records
    else safe to store
        Drafting->>Drafting: append immutable scene version
        Drafting->>Canon: submit newly suggested stable facts
        Drafting-->>UI: reviewable version and explanation
    end
    Author->>UI: compare, revise, approve, or discard
```

## Incremental behavior

Generating or revising one scene does not rerun whole-project narrative
analysis. The service reads cached Narrative Intelligence and a bounded Story
Bible projection, adds only adjacent-scene handoff context, and invalidates the
existing workspace source token after a material state change. The next
bootstrap is recomputed once and then served from the persisted cache.

## Safety and compatibility

- All RC7 routes and fields are additive.
- Stable request IDs deduplicate provider work and stored versions.
- Provider output is validated before persistence.
- Existing approved prose is never overwritten by generation, merge, or
  revision.
- Paragraph planning skeletons are seeded only when absent.
- Revision approval and promotion remain separate author actions.
- Canon proposals cannot bypass the existing approval workflow.

The detailed implementation is in
`docs/architecture/rc7-writing-experience.md`; the author workflow is in
`docs/workflows/rc7-writing-flow.md`.

