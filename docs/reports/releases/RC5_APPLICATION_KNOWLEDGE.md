# RC5 Application Knowledge Layer

## Purpose

Application Knowledge explains NovelForge itself. It is deliberately separate from Project Knowledge, which explains the selected novel. This prevents questions such as “What does Arc Board do?” from searching story content or spending an AI-provider call.

## Shared contract

`ApplicationKnowledgeService` owns the author-facing catalog. Its 31 surfaces define:

- label and workflow group;
- purpose and author value;
- what to do on the surface;
- what happens next;
- aliases used to recognize natural questions;
- direct actions with validated destinations.

The same catalog drives the grouped toolbox, page guidance, deterministic Assistant answers, navigation validation, and this capability inventory. No frontend-specific copy map was introduced.

## Reasoning layers

| Layer | Example | Context used | Provider call |
|---|---|---|---|
| Application | What does Arc Board do? | Application catalog | No |
| Project | Why is Story Health 82? | Existing Narrative Analysis | As configured |
| Combined | Where should I fix this canon conflict? | Catalog plus project evidence | As configured |

Pure application responses are tagged `application`, use `application_knowledge` as their source, consume zero model tokens, and never pretend that application help is story evidence.

## API

- `GET /api/projects/{project_id}/application-knowledge`
- `GET /api/projects/{project_id}/application-knowledge/{surface_id}`
- `POST /api/projects/{project_id}/assistant` with `active_surface`

All Assistant navigation destinations are checked against the catalog before they reach the UI.

## Page guidance

Every workspace surface consumes the catalog through one guidance component. The compact row states what the page is. Expanding it answers:

1. Why it matters.
2. What to do here.
3. What happens next.
4. Where the author can go next.

The Ask action opens the same Assistant with the current surface attached.

