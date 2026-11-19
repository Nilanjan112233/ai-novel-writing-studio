# RC6 Amateur Author Live UX Audit

## Test perspective

The product was exercised as an amateur author who has an idea but does not know novel-planning terminology or NovelForge's workspace hierarchy. The browser journey used a new story, **The Remembering Roads**, and followed the visible interface instead of calling backend setup helpers.

The interactive in-app Browser surface was unavailable in this session, so acceptance was performed in the repository's live Chromium application through Playwright. The browser used the real frontend, FastAPI server, MongoDB records, and configured Gemini provider.

## End-to-end author journey

### 1. Project creation

The Projects page provides a clear new-project entry. After creation, the author lands in the project and immediately sees **Start Your Novel**, rather than a grid of equally weighted expert tools.

Expected beginner feeling: “I know where to begin.”

### 2. Story foundation

The guide asks one understandable question at a time:

1. What is the story idea?
2. Who is the main character?
3. What kind of world do they live in?
4. What central conflict drives the story?
5. What first decision must the author make?
6. What is the first meaningful arc?
7. What happens in the first scene?

Each step explains why it matters. The author can type, import, ask AI, or skip without being trapped. Moving among steps is allowed, and saved answers can be revised later.

Expected beginner feeling: “I can make progress even if I do not have every answer.”

### 3. Entering the wider workspace

Navigation is grouped by intent:

- Start Here for the dashboard and guide;
- Build for people and world;
- Plan for arcs, timeline, relationships, and open questions;
- Write for scene and chapter work;
- Review for consistency and canon;
- Publish for readiness and export.

Breadcrumbs, recent destinations, and the next recommended action reduce the cost of exploring.

Expected beginner feeling: “I understand what this area is for and can get back.”

### 4. Empty tools

Opening an empty Character, World, Timeline, Power System, Relationship, Theme, Plot Thread, Arc, Mystery, Faction, or Drafting area no longer ends at “No data.” Each surface offers manual creation, AI generation, import, and return to guided setup.

Expected beginner feeling: “An empty screen is an invitation, not an error.”

### 5. Making and revising decisions

The author can inspect Decision History, preview affected systems, change a decision, undo it, or reopen the question. The timeline explains when and why a decision changed.

Expected beginner feeling: “I can experiment without losing control of my story.”

### 6. Approving AI suggestions

AI narrative facts remain proposals. Approval visibly routes the fact into official canon, rebuilds Story Bible, refreshes analysis, and updates dependent workspace surfaces. Rejection does not alter canon.

Expected beginner feeling: “The AI helps, but I remain the authority.”

### 7. Understanding progress

The product now separates:

- Story Consistency;
- Content Completeness;
- Draft Progress;
- Revision Progress;
- Publication Readiness.

This avoids presenting a healthy but mostly unwritten story as nearly complete, or a complete draft with consistency problems as unfinished.

Expected beginner feeling: “I understand what each number means.”

### 8. Companion behavior

The companion is compact, friendly, animated, and action-oriented. It explains why a recommendation matters, exposes one-click actions, remembers completion/dismissal/snooze, and does not create another unread item during cooldown. Reduced-motion preferences are respected.

Expected beginner feeling: “I have a guide, not a nagging notification feed.”

## What was confusing before RC6

- Too many expert destinations competed for attention after project creation.
- Empty screens described absence without creating momentum.
- Story Health could be mistaken for overall completion.
- Earlier decisions felt permanent even though story development is exploratory.
- Recommendations could repeat without a durable lifecycle.
- Project actions did not scale gracefully in a growing library.
- Several panels independently fetched overlapping health/context data.

## Remaining experience limitations

1. AI-assisted answers can take noticeably longer than manual entry. The UI communicates work, but a first-time author may still prefer starting manually.
2. The guide intentionally stops at a first scene plan. A short transition explaining the difference between planning a scene and writing its prose would further help new authors.
3. Advanced review pages still contain significant information density. Page guidance and companion explanations help, but these screens are best entered after the guided foundation.
4. Imports accept useful structured text but do not yet provide a pre-import mapping preview for every domain.
5. The full live provider suite takes a long time when run as one monolithic command. Splitting it by workflow gives clearer results and avoids harness timeouts.

## Desktop acceptance

The application was tested at:

- 1366 × 768;
- 1440 × 900;
- 1920 × 1080;
- 2560 × 1440.

The matrix covers workspace and settings layouts, navigation, overflow, panels, cards, and companion placement. All 12 desktop-layout checks passed.

## Accessibility acceptance

- Keyboard-reachable controls and visible focus are retained.
- Action labels are exposed to assistive technology.
- Story Consistency metrics use a valid labelled group.
- Reduced-motion behavior is available for companion animation.
- The automated serious-impact accessibility scan passed.

## UX verdict

RC6 meets the beginner success path: a new author can create a project, find one clear starting point, establish the story, use or decline AI help, revisit decisions, plan a first scene, distinguish progress from consistency, and follow direct next actions without learning the internal architecture.

