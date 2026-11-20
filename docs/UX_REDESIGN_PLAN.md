# UX redesign plan

Goal: a first-time author can open a project, see where the book stands, and
know the one thing to do next, without learning the app's internal vocabulary.

## What is wrong today (audit, November 2026)

I went through every screen as a new author with the demo project
(`backend/scripts/seed_demo_project.py`) and the real-AI test project.

**Too many places to go**
- The project workspace has two navigation systems side by side: an icon rail
  with six unlabeled icons (Dashboard, Story Studio, Writing, AI Guidance,
  Toolbox, Settings) and a "Toolbox" drawer listing **32 sections** in five
  groups, plus a "Recent" list, plus a Ctrl+K palette.
- The same job lives in several places. Writing a chapter can start from
  Writing, Story Studio, Drafting, the Dashboard or the floating companion.
  Confirming extracted facts happens in Story Studio, Characters, World,
  Timeline, Knowledge and the Canon Queue.
- Above every page, before any content, there are three stacked banners: a
  breadcrumb header, a "Page guidance" bar and a "Story guidance" bar. On a
  1280×800 screen the actual page starts about 250 px down.
- A floating "companion" card sits over the bottom-right corner of every page
  and covers buttons.

**Jargon**
- Labels and copy talk about the system, not the book: *canon governance*,
  *orchestration*, *readiness*, *authority*, *authoritative version*,
  *narrative intelligence*, *explainability timeline*, *candidate*, *story
  leads*, *enrichment*, *structured vs discovery writing*.
- The home page sells "govern canon" and "evidence-backed guidance" instead of
  saying what the app does for a writer.

**No sense of progress**
- Nothing persistent tells you how far the book is: no chapter count against a
  target, no word count, no stage. The dashboard's "Story progress" has four
  ticks that do not match the navigation.
- The dashboard opens with a "Project identity" form (rename the project),
  which is a settings task, not the most useful thing to show.

**Unclear next step**
- The "Develop Story" button appears in the header, the dashboard hero and the
  companion, with different labels ("Develop Story", "Develop My Story").
- Pages end without saying where to go next; many empty states point to a
  "Creation guide" that is itself one of the 32 sections.

**Visual**
- Several competing styles: purple gradient home page, flat grey workspace,
  tinted sky/amber/violet boxes inside cards inside cards, mixed radii (6 px to
  24 px), many uppercase micro-labels.
- Dark mode is defined in CSS but there is no way to turn it on, and the
  tinted boxes would not work in it.
- AI Settings shows six provider cards with five status rows each, all
  "UNTESTED", before the author has done anything.

## The new information architecture

One guided path, numbered in the sidebar, mirroring how a novel gets made:

| Step | Sidebar label | What it holds (section ids kept) |
| --- | --- | --- |
| 0 | **Overview** | Where the book stands, the next step, recent chapters (`dashboard`) |
| 1 | **Plan** | Story idea (`vision`), Characters, World, Plot threads (`threads`), Mysteries, Story arcs (`arcs`), Timeline, Questions for you (`questions`) |
| 2 | **Write** | Chapters (`writing`), Write the next chapter (`write-next`, new), Scene planner (`drafting`) |
| 3 | **Review** | Facts to confirm (`facts`, new), Story check (`story-health`), Suggested edits (`editorial`) |
| 4 | **Finish** | Book & export (`manuscript`) |
| | **More tools** (collapsed) | Every other section, unchanged: story chat, setup guide, arc planner, relationships, power system, factions, themes, knowledge, knowledge graph, story bible rules (canon), canon queue, readiness, story room, discussion, AI insights, AI activity, project history, story check history |
| | **Project settings** | Name and title, backups, link to AI settings (`settings`) |

Rules:
- **Every section id still works** (`?section=canon` etc.), so deep links,
  the Ctrl+K palette and the AI assistant's "go to" actions keep working.
- **Each step page has the same shape**: a page header (title, one plain
  sentence, the step's main action), a row of tabs for the step's sections,
  the content, and a "Next step" footer that links to the next step.
- **One persistent progress bar** at the top of the workspace: the five
  stages with the current one highlighted, chapters approved / planned, total
  words, and facts waiting for review.
- **One AI entry point**: an "Ask AI" button in the top bar opens the
  assistant drawer. The floating companion and the page-guidance banner are
  removed from the main path; story guidance shows only on Overview.
- **Plain language**: "Develop Story" becomes "Let AI build the plan";
  "Canon" becomes "Story rules"; "Editorial" becomes "Suggested edits";
  "Story Health" becomes "Story check"; "Manuscript" becomes "Book & export";
  candidate facts are "facts to confirm".

## Visual system

- One set of design tokens in `globals.css` (light and dark): warm neutral
  background, white cards, one indigo accent, green/amber/red for status only.
- Type scale: page title 24 px, section title 18 px, body 14–15 px, prose in a
  serif at 17 px. Fewer uppercase micro-labels.
- Shared building blocks in `components/ui/`: `PageHeader`, `Card`,
  `StatusBadge`, `ProgressBar`, `EmptyState`, `LoadingState`, `ErrorState`.
- 12 px card radius, 8 px controls, consistent 24 px page padding.
- Dark mode toggle in the sidebar; the tinted info boxes used across
  components get dark equivalents.
- Home, Projects and AI Settings get the same look; AI Settings leads with the
  one decision that matters (which provider and model) and tucks the
  per-provider diagnostics behind "Details".

## Out of scope

- Backend API changes (none needed).
- Renaming the product (being decided separately).
- Rewriting the specialist tools under "More tools"; they keep their current
  layout inside the new shell.

## Done when

- A new author can go Idea → Plan → Write → Review → Finish using only the
  numbered sidebar and "Next step" buttons.
- pytest, Vitest, lint and build pass; the offline Playwright run passes
  (specs that need a real AI provider skip themselves when none is set).
- Screenshots and the demo GIF show the new UI.
