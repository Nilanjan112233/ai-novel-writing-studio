# RC5 Known Limitations

Updated: 2026-07-23

1. RC5 remains desktop-first. Existing smaller-screen behavior is retained, but this hardening pass targets 1366×768 through 2560×1440.
2. Project Timeline replay explains historical effects and opens the related workspace; it does not roll project state back.
3. Story Health History needs at least two stored Narrative Analysis snapshots before it can compare score changes.
4. The Companion uses event-aware cached intelligence plus a bounded visible-page poll. It is not a remote push notification service when NovelForge is closed.
5. Developer Mode is a presentation boundary, not multi-user role authorization. The optional local access token protects a local deployment but does not replace an identity provider.
6. Publication exports are governed local artifacts. NovelForge does not submit directly to printers, retailers, ISBN agencies, or ebook stores.
7. The Projects API currently returns the latest 1,000 records. The UI progressively renders 60 at a time and can search within those records; server-side cursor pagination is the next scale step for libraries above 1,000 projects.
8. Historical development and E2E projects remain in the configured database unless explicitly purged by the author. Recoverable Trash and guarded permanent deletion are available.
9. Python/Pydantic emits migration deprecations for legacy schema classes. They do not fail tests, but should be removed before Pydantic 3.
10. Real Gemini regression tests depend on Google AI Studio availability, quota, and network latency. The credential remains encrypted and is never written to reports.
11. The in-application Browser connector exposed no browser session in this environment. Browser validation therefore used the repository Chromium Playwright harness.

Resolved since the original RC5 report:

- workspace sections are URL-deep-linkable and support browser Back/Forward;
- the Companion can dock left or right and remembers its motion preference;
- project deletion is recoverable by default;
- approved manuscripts can be exported as Markdown, text, HTML, DOCX, EPUB, PDF, and a provenance package;
- serious WCAG contrast findings on audited primary pages were corrected.
