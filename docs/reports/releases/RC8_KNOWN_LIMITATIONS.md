# NovelForge V2 RC8 — Known Limitations

These limitations are measured or directly observed; they are not speculative
feature requests.

## Deployment

RC8 is supported as a local/private desktop-style application. Authentication,
tenant isolation, project authorization, hosted secret custody, and public API
rate limiting have not been audited for multi-tenant SaaS deployment. Do not
market RC8 as a hosted multi-tenant service without that separate review.

## Cold workspace readiness

Warm Workspace Bootstrap is fast because it reuses the source-token cache, but
cold readiness remains visibly slower on large projects. Final measured cold
totals were 2.04 s at 100 chapters, 2.18 s at 250, 3.69 s at 500, and 7.24 s at
1,000. Story Bible projection dominates those totals. Staged readiness and loading
feedback keep the UI usable, but cold-start optimization remains appropriate
before positioning 1,000-chapter projects as a primary workflow.

## Legacy local validation data

Before RC8 isolation, the normal local `novelforge` database accumulated a
large number of validation projects. RC8 Playwright runs now use
`novelforge_e2e`, record exact created project IDs, and leave the normal project
count unchanged. RC8 intentionally does not bulk-delete legacy records because
there is no exact historical ownership manifest and title-prefix deletion could
remove author work. Existing installations should review and archive/delete
legacy validation projects explicitly.

## Provider variability

Gemini responses remain externally variable. RC8 normalizes recoverable shapes,
reconciles semantic references, performs one bounded correction, and fails
visibly without partial persistence. It does not weaken authority validation or
guarantee that every provider request will succeed. A retry may still be needed
after quota, network, or provider service failure.

## Chronology guard scope

Chapter-bounded character context and output validation passed direct and
indirect adversarial probes. The guard is deliberately conservative, but
semantic language-model validation is not a mathematical proof against every
possible paraphrase. Unsafe uncertainty is rejected rather than shown as
chapter-safe knowledge.

## Writing quality

POV drift, unresolved structures, continuity, and repeated prose patterns are
editorial evidence, not a substitute for a professional editor or the author's
judgment. The repetition detector uses cross-scene thresholds to avoid treating
all thematic recurrence as a defect; subtle stylistic repetition may therefore
remain unflagged.

## Runtime warnings

The backend suite still reports upstream/deprecation warnings from Pydantic v2
compatibility paths. They do not fail current validation, but should be removed
before a future Pydantic v3 upgrade. RC8 did not risk a broad schema rewrite to
silence them.

## Benchmark coverage

The scale benchmark recorded endpoint latency and bounded row counts. Process
working-set values were unavailable in the measured artifact, so it does not
support a numeric memory claim. The 2,000-chapter result is a stress observation,
not a supported primary launch target.

## Soak publication boundary

The 50-scene soak generated all ten chapter drafts and exercised publication
preflight. Its manuscript assembly was correctly blocked because those chapter
drafts had not been separately approved as project manuscript sources. Approved
manuscript export is covered by the real-stack Playwright publication journey;
the soak should not be cited as a successful publication export.
