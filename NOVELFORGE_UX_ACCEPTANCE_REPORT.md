# NovelForge UX Acceptance Report

Date: 2026-08-09

## Author-facing verdict

The normal workflow is materially simpler: an author can open Story Studio to ask about the project or open Writing to see the actual chapters and continue. Discovery writing and structured writing now share the same visible writing-state projection instead of presenting conflicting “no chapters” and “create your first arc” guidance.

## What an author can now understand

- how many chapters exist;
- which chapter is latest and approved;
- where to open an earlier chapter;
- the active version and word count;
- whether continuity and extraction are ready;
- what Story Studio believes it is doing;
- that conversation is not canon;
- that extracted details are candidate/derived information until governed;
- how to continue from the latest approved chapter.

## Still imperfect

- The current chapter library opens approved prose and routes revision actions into existing editorial/revision tools, but the route does not yet deep-link to a selected Discovery chapter inside the editor.
- Version comparison is surfaced only where the existing lineage reports multiple versions; richer comparison remains an existing specialist capability.
- The current Story Studio still retains some historical job responses that were generated before the projection fix. They are historical conversation, not current authority, but the UI should eventually label old answers more visibly as historical.
- Some existing Story Studio evidence payloads are objects rather than arrays and therefore need a later presentation polish for full evidence expansion.
- Background-job persistence exists, but the normal author surface still needs a more explicit durable activity inbox for jobs resumed after navigation.

## Acceptance answers

1. Primarily through Story Studio: yes for questions, guidance, brainstorming, and governed proposals; Writing remains the clear companion surface for prose and chapter management.
2. Discovery writer starts immediately: the existing Discovery flow remains available and is now connected to the shared writing projection.
3. Approved writing builds reusable context: yes; approved chapters feed extraction, chapter intelligence, Story Bible rebuild, and Narrative Analysis Engine ingestion through existing services.
4. Authoritative changes remain governed: yes; the Story Studio path does not apply model text directly to canon or approved story state.
5. Structured and Discovery workflows coexist: yes; both project into the same writing-state surface and reuse existing authorities.
6. Cost/safety: the changes do not weaken provider validation or route high-impact authority through a new cheap path. Deterministic read-model projection avoids unnecessary AI calls.
7. TencentDB: not necessary for this UX integration phase. Native retrieval and provenance hygiene were improved first, as required.

