# RC7 Writing API

All endpoints are project-scoped and additive.

## Writing projection

- `GET /api/projects/{project_id}/writing-dashboard`

Returns current writing location, metrics, workflow stages, scene health,
context counts, and the recommended next action.

## Scene alternatives

- `POST /api/projects/{project_id}/scene-plans/{scene_id}/generate-draft`
- `POST /api/projects/{project_id}/scene-drafts/{draft_id}/regenerate`
- `GET /api/projects/{project_id}/scene-drafts`
- `PUT /api/projects/{project_id}/scene-drafts/{draft_id}/favorite`
- `GET /api/projects/{project_id}/scene-drafts/compare`
- `POST /api/projects/{project_id}/scene-drafts/merge`
- `POST /api/projects/{project_id}/scene-drafts/{draft_id}/writers-room`
- `POST /api/projects/{project_id}/scene-drafts/{draft_id}/rollback`
- `PUT /api/projects/{project_id}/scene-drafts/{draft_id}/status`

Generation accepts an optional `operation`, `change_reason`, stable
`request_id`, and `allow_exploratory`. Exploratory generation changes only the
ability to create a reviewable draft; it does not bypass validation or
approval.

Successful draft responses include the existing draft record plus
author-facing explanation fields such as `scene_goal`, `scene_trouble`,
`scene_stakes`, `connection_from_previous`, `distinct_progression`, and
`handoff_to_next`. These fields describe the generation; they do not create a
new source of story truth.

Comparison accepts `left_draft_id` and `right_draft_id`. Merge accepts both
source IDs, explicit `merged_text`, and a reason, then creates a new review
version.

## Editorial revision

- `POST /api/projects/{project_id}/editorial/review/scene/{draft_id}`
- `POST /api/projects/{project_id}/editorial/review/chapter/{draft_id}`
- `POST /api/projects/{project_id}/revision-branches`
- `POST /api/projects/{project_id}/revision-branches/{branch_id}/generate`
- `PUT /api/projects/{project_id}/revision-branches/{branch_id}/status`
- `POST /api/projects/{project_id}/revision-branches/{branch_id}/apply`
- `GET /api/projects/{project_id}/revision-branches/{branch_id}/lineage`
- `GET /api/projects/{project_id}/revision-branches/{branch_id}/compare`

Branch creation accepts `revision_pass`. Revision generation accepts a
`change_reason`, optional report IDs, revision pass, and stable request ID.
Apply requires an approved branch and promotes the selected revision to a new
review draft without modifying its source.

## Error behavior

Invalid state transitions and unmet writing gates return HTTP 409 with
author-actionable details. Invalid identifiers and request data use the
existing 400/404 behavior. Provider and network failures preserve the previous
draft and can be retried safely with the same request ID.

Provider output is checked through the existing draft validator before
persistence. Correctable provider-authority violations receive one retry.
Uncorrected violations fail without creating partial draft or paragraph
records.
