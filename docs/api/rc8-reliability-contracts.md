# RC8 API Reliability Contracts

RC8 preserves existing endpoint paths and request compatibility.

## Stable request identity

Generation and revision callers should send a stable `request_id` for one user
intent. Repeating or concurrently sending the same request ID returns the one
logical operation result where available. It must not create another scene
version or expose a database uniqueness error.

## Failure responses

State and validation failures continue to use the established HTTP status
semantics. The UI converts them into a persistent author-facing operation
failure containing:

- the operation that failed;
- a plain-language explanation;
- an explicit statement that existing prose or approved work is unchanged;
- a safe retry action when applicable;
- a destination when another record must be reviewed first;
- technical detail only when Developer Mode is enabled.

## Generation outcome trace

Execution traces distinguish these stages:

- `provider_success`;
- `parse_success`;
- `validation_success`;
- `reference_resolution_success`;
- `persistence_success`;
- `approval_eligible`;
- `final_outcome`.

A provider HTTP 200 followed by contract rejection is an application failure.
No invalid or partial draft is persisted.

## Character conversation boundary

Character conversation requests with a chapter boundary return the existing
response plus the allowed evidence projection. Unsafe direct or indirect future
claims are corrected once or rejected. Rejection does not persist the unsafe
assistant text as approved character memory.

## List projections

Drafting, Editorial, Canon Queue, and Project Timeline list endpoints retain
their existing records while supporting bounded result sets and author-facing
search/status/chapter/pass filters. Details and prose can be loaded separately
by the existing UI instead of embedding all versions in the initial workspace.

