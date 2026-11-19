# RC5 Bug Fix Report

## Post-RC5 hardening fixes — 2026-07-23

| Defect | Resolution |
| --- | --- |
| Permanent deletion was the normal project action | Added recoverable Trash, Restore, Archive/Unarchive, explicit duplicate modes, and guarded title-confirmed purge |
| Large historical project libraries blocked create navigation | Projects render progressively in groups of 60 while retaining search and lifecycle counts |
| Paragraph-owned records mixed string and ObjectId project identifiers | Added migration/backfill, canonical ObjectId writes, project-scoped child queries, and API-boundary serialization |
| A paragraph-content fallback returned a raw ObjectId and caused HTTP 500 | Serialized the synthesized editor payload; Paragraph Editor E2E now passes |
| Analysis cache hits created misleading new analysis identities/history | Cache hits reuse the authoritative identity and do not append false history |
| Concurrent analysis requests could duplicate work | Added a per-project lock and background-request coalescing |
| Companion recommendations disappeared during cooldown refresh | Cooldown now limits presentation, not active-feed visibility |
| Opening the Companion before its feed arrived left delivered messages unread | Read acknowledgement is tied to open state and reacts when the feed arrives |
| Companion overlaid workspace content | Added dock-aware desktop safe padding and remembered left/right placement |
| Workspace deep links hydrated differently on server and client | Initial render is deterministic; the query destination is applied on mount and Back/Forward is synchronized |
| Destructive controls and muted badge text missed WCAG AA contrast | Darkened the relevant semantic color tokens; Axe reports no serious/critical findings on audited primary pages |
| Timeline E2E referenced an obsolete test identifier | Aligned the test with the current Story Timeline contract |
| Chronology comparison used lexical date ordering | Dates are parsed structurally and findings use author-readable transitions |
| Project context invented an unanalyzed Story Health score | Unanalyzed projects now report an explicit unavailable state |
| Wildcard CORS and broad container bindings exposed local services | Added explicit origins/trusted hosts and loopback-only container ports |
| Approved manuscripts had no governed publication output | Added preflight plus Markdown, text, HTML, DOCX, EPUB, PDF, and hashed package exports |

| Defect | Resolution | Evidence |
|---|---|---|
| Continue Writing opened fabricated Mara/chapter prose | Removed the placeholder and routed the primary action to governed Drafting | RC5 Playwright asserts the fabricated text is absent |
| Application questions used story-first reasoning and provider tokens | Added application/project/combined classification and a deterministic Application Knowledge path | Backend contract test and RC5 Assistant E2E |
| Assistant application action skipped Arc Board and opened its downstream workflow | Added the explained surface as the first action while retaining downstream choices | Backend and browser navigation assertions |
| Canon Queue was hidden in an Assistant tab | Added a toolbox destination, page guidance, and visible Canon action | RC5 Canon Queue E2E |
| Recommendations explained issues without a destination | Added validated Review/Open actions to banners, guidance, Companion, Assistant, critique, and timeline reasons | Application catalog contract plus E2E |
| Companion repeated unstable recommendation identities | Replaced snapshot fingerprints with stable action keys and persisted lifecycle/cooldown state | Backend lifecycle test |
| Companion looked like a repeating notification panel | Added state-aware avatar, bounded recap, milestone context, priority cards, quiet sleep state, polling, and reduced-motion support | Component test, animation E2E, screenshot |
| Companion cooldown refresh could remove an item while the author was reading it | Preserved the active in-session message set until the author acts or a replacement recommendation arrives | Component regression and RC5 browser workflow |
| Knowledge Graph exposed objects and metadata | Replaced raw rendering with readable entity/evidence cards and progressive controls | Frontend test and E2E leakage assertions |
| Story Health exposed nodes, dependencies, cache timing, and IDs | Removed engineering statistics and translated findings into author language | Frontend regression |
| Canon rendered JSON, dotted fields, and legacy-source terminology | Added author value/evidence rendering and normalized labels | Frontend regression |
| Critique/evidence panels serialized payloads | Routed through shared author-facing presenters | Frontend regression |
| Page purpose and next step were inconsistent or absent | Added shared Page Guidance for all cataloged workspace surfaces | Catalog contract, component test, E2E |
| No project evolution or health-change history | Added Project Timeline and Story Health History over existing events/snapshots | Backend and frontend tests |
| Settings exposed routing, cost, and agent controls to every author | Kept provider setup visible and moved technical controls behind Developer Mode | Settings unit and E2E |
| Project Activity and project-local Settings exposed calls, tokens, cost, cognition, and orchestration graphs | Replaced default views with author-facing status/outcomes and gated diagnostics behind Developer Mode | RC5 Developer Mode E2E |
| Icon rail relied only on browser title text | Added explicit accessible labels | Desktop Playwright audit |
| Run Cycle and execution traces leaked engineering language | Renamed the action to Advance Project and hid traces from normal author views | Build and UI regressions |
| Duplicate Mongo update paths in Companion state | Removed overlapping `$set`/`$setOnInsert` fields | Runtime verification and backend lifecycle test |
| React Hook build warnings in AI suggestion/editor code | Corrected effect dependencies and stale-closure refs without adding editor capability | Warning-clean production build |

No Paragraph Editor feature was added. Its only change was a critical hook/stale-closure correctness fix required for a clean production build.
