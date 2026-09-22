# Canon Explorer Walkthrough

## Authoritative view

Open a project and choose **Canon**. Canon Explorer loads the governed `canon_registry` and normalizes older canon entries for backward-compatible inspection. The registry is the source of truth; the explorer is not a separate canon database.

## Browse and inspect

Authors can:

1. Search fact text, subject, field, value, or identifier.
2. Filter by canon type and active/inactive status.
3. Open a fact to inspect its source collection and source identifier, confidence, evidence, originating chapter, relationships, conflicts, versions, and approval history.
4. Compare versions without changing either version.
5. Deactivate or reactivate a governed fact while retaining history.

The explorer intentionally shows inactive records. Canon is governed, not hidden.

## Editing canon

**Propose edit** calculates downstream impact and creates a Canon Proposal. The proposal shows affected chapters, scenes, characters, plot threads, canon consequences, timeline consequences, and narrative risk. It is not applied until the author approves it through the existing proposal workflow.

On approval, the existing workflow updates official canon, rebuilds the Story Bible, emits a narrative change event, and refreshes dependent analysis. Rejection preserves the proposal record and leaves canon unchanged.

## Safety properties

- AI-generated facts cannot enter canon directly.
- Provenance and approval history remain visible.
- Legacy records remain inspectable.
- Canon edits do not bypass impact analysis or author control.

