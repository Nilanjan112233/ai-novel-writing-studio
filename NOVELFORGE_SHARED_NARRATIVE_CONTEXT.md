# Shared Narrative Context

## Objective

Shared Narrative Context ensures that meaningful author answers become reusable, attributable project knowledge. It prevents agents from repeatedly asking for information that the author has already supplied.

## Persistence rules

Input is persisted when it is a declarative story fact with sufficient confidence and narrative importance. Navigation commands, questions, acknowledgements, and transient chat are not persisted.

Each stored record includes:

- structured domain, subject, field, and value;
- normalized text and a stable deduplication fingerprint;
- confidence and importance;
- active status;
- provenance entries identifying source type, source ID, author, and timestamp;
- routed subsystems.

Equivalent answers merge provenance rather than creating duplicates.

## Routing

| Domain | Primary destinations |
|---|---|
| Character | Story Bible, Character Intelligence, Knowledge Graph |
| World or power | Story Bible, Canon, World/Power systems, Knowledge Graph |
| Timeline | Story Bible, Timeline Intelligence, Canon |
| Relationship | Story Bible, Relationship Graph, Character Intelligence, Knowledge Graph |
| Plot or mystery | Story Bible, Plot Thread Intelligence, future planning agents |

## Canon boundary

High-confidence author facts that would alter canon create Canon Proposals. They are available as attributed project context immediately, but do not become official canon until approved. This preserves memory without bypassing governance.

## Refresh behavior

Explicit context updates rebuild the Story Bible and emit a project change event. Narrative Analysis consumes active shared context as a source collection, so downstream character, timeline, graph, completeness, critique, and companion projections can reuse it.

## API

- `GET /api/projects/{project_id}/shared-narrative-context`
- `POST /api/projects/{project_id}/shared-narrative-context`
- `PATCH /api/projects/{project_id}/shared-narrative-context/{context_id}/active`

