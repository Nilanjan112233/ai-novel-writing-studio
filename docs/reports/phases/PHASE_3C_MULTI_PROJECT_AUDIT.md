# NovelForge Narrative Studio V2 - Phase 3C Multi-Project Audit

Audit date: 2026-06-14

## Result

Passed with zero detected leaks.

## Projects

Primary validation project:

- ID: `6a2ef4727851cfbde7d3b439`
- title: `Phase 3C Validation: The Bell Beneath Winter`
- chapters: 50
- words: 89,063

Isolation project:

- ID: `6a2ef4727851cfbde7d3b43a`
- separate chapter intelligence, canon, and story identity.

## Assertions

The validation checked:

- no chapter-intelligence record from the isolation project appeared in the
  primary project;
- no primary-project chapter appeared in isolation memory;
- service queries required project ownership;
- change impact ignored records from other projects;
- canon and knowledge lookups remained project-scoped;
- agent context packets used the requested project ID;
- memory indexes included project ownership;
- Story Bible chapter intelligence contained only the selected project;
- cross-project artifact and continuity IDs were rejected.

Measured isolation leaks: 0.

## Regression Coverage

Backend regressions create a second project with similarly named entities and
verify chapter memory, impact previews, and health calculations do not include
it.

The full E2E suite also creates many independent projects across planning,
drafting, editorial, manuscript, canon, and Story Auditor workflows without
observed record contamination.

## Residual Risks

- project-scoped MongoDB queries rely on application enforcement rather than
  database row-level security;
- future background jobs must continue to include `project_id`;
- aliases shared across projects can confuse unscoped analytics if a new query
  omits ownership;
- backups, exports, collaboration, and tenant-level permissions are outside
  this phase.

## Recommendation

Add a static query audit that flags project-owned collection reads lacking a
`project_id` predicate, plus a nightly contamination test with deliberately
identical character, artifact, and mystery names across at least ten projects.
