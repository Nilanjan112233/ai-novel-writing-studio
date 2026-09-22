# NovelForge Continuity Conflict Report

## Observed defect

The prior real run established a confirmed planning fact that Elias disappeared five years ago, while later generated prose stated two years. This was a genuine precedence failure: derived prose/chapter intelligence was allowed to coexist with a higher-priority confirmed decision without an author-visible guard.

## Implemented hardening

`backend/app/services/draft_validation_service.py` now checks meaningful duration conflicts against canon, approved decisions, and confirmed timeline information. A contradiction fails safely before authoritative approval rather than silently becoming a new fact. The existing writer precedence guidance also prioritizes approved canon, decisions, confirmed planning, and only then derived/candidate information.

The old prose was not silently rewritten. The safe behavior is to preserve history, report the conflict, and require correction or author review.

## Validation status

Focused regression tests pass for the guard and authority boundary. A new real-provider contradiction generation was not run in this final pass; the original live contradiction remains the evidence that motivated the fix.

