# RC8 Commercial Launch Hardening

RC8 closes verified RC7 audit defects inside the current service boundaries.
The detailed source-of-truth map and state-transition overview are in
`RC8_ARCHITECTURE_NOTES.md` at the repository root.

## Invariants

1. Every failed author write is visible and states whether existing work is
   safe.
2. Writer's Room cannot activate, replace, or unapprove its source.
3. A chapter-bounded character response cannot use future or hidden knowledge.
4. Concurrent identical request IDs create one logical result.
5. AI output uses story labels; the server resolves database identity.
6. Scene order is chapter number followed by scene order.
7. One semantic problem is shown and scored once.
8. Provider success is distinct from usable application success.

## Incremental analysis

Material writes continue to publish project events and invalidate the existing
Workspace Bootstrap source token. The Narrative Analysis Engine compares source
manifests and fingerprints, recomputes changed nodes, and reuses unchanged graph
records. Canon, Timeline, Character Intelligence, Story Bible, Story Health,
Knowledge Graph, Companion, milestones, and publication readiness consume these
same refreshed projections.

## Dedicated E2E isolation

Playwright refuses to start unless its database name contains `e2e`. Setup
copies only provider configuration required for the real stack and records the
exact pre-run project/model identities. Teardown deletes project-owned records
by the exact IDs created during that run and removes only provider-model records
that were not present before setup. It never deletes by title prefix.

## Release evidence

The root reports `RC8_TEST_RESULTS.md`, `RC8_LONG_FORM_SOAK_REPORT.md`,
`RC8_UX_ACCEPTANCE_REPORT.md`, and `RC8_COMMERCIAL_LAUNCH_AUDIT.md` contain the
measured validation results and the supported-deployment release decision.
