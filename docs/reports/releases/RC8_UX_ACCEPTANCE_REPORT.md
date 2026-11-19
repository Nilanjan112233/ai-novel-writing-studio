# NovelForge V2 RC8 — UX Acceptance Report

## Method

Acceptance combined the real-stack Playwright journeys with a separate in-app
browser inspection of a developed fantasy project at 1280×720. The live check
used visible DOM state after Workspace Bootstrap readiness, opened the Workspace
Companion, and inspected Story Health, milestones, next actions, navigation, and
author-facing labels.

## Beginner orientation

The workspace exposes:

- workflow-grouped navigation: Start Here, Build, Plan, Write, Review, Publish,
  and Settings;
- project/section breadcrumb;
- page purpose and inline guidance;
- a seven-step “Start Your Novel” continuation action;
- a current milestone plus one direct next action;
- separate Story Consistency and Narrative Completeness language;
- one-click destinations for findings and publication blockers.

A novice can distinguish planning readiness from prose progress. The live
project showed **Draft Ready** while correctly reporting no generated chapter
prose. RC8 further qualified the former ambiguous readiness card as **Arc Draft
Readiness** and treats a 0/0 report as **Not evaluated**.

## Author-language verification

The first live inspection caught one unresolved foreshadowing finding displayed
as an internal UUID. The Narrative Analysis Engine label projection was fixed to
prefer the story seed, event, question, title, or description while keeping
machine identity separate.

The corrected live check found:

- story label visible: “The crown's map has one deliberate blank.”;
- raw UUID matches in the normal workspace: 0;
- Story Consistency 94 visible;
- the direct “All planned chapters have drafts” next action visible.

This is direct browser evidence rather than a source-only claim.

## Workspace Companion

At 1280×720 with the panel open:

- constrained width: 336 px (26% of viewport);
- dock: right, with one-click left docking;
- state: `celebrating` after reaching Draft Ready;
- visible current milestone and explanation;
- direct navigation action on every recommendation;
- dismiss, complete, and “Tomorrow” snooze controls;
- direct animation disable control;
- live polite status announcement;
- “Ask how this page works” entry point.

Automated desktop acceptance also keeps Toolbox and Companion open at 1280×720
to verify usable writing width. The Companion respects reduced motion and never
automatically edits story state.

## Large-project workspaces

The 10-chapter/50-scene project and synthetic 100–1,000 chapter datasets were
used to inspect bounded lists. Drafting and Editorial do not display every prose
version at once. Canon Queue and Project Timeline load bounded rows and expose
search/filter controls. The graph uses readable cards and keeps internal payload
detail behind Developer Mode.

## Failure and recovery experience

A real UI failure journey forces draft generation to fail and verifies that the
workspace announces:

- the failed operation;
- an author-language reason;
- that existing prose is unchanged;
- a safe retry;
- the owning destination;
- no raw implementation detail in normal mode.

The same shared contract now wraps other writing, review, manuscript, canon,
workflow, and planning writes. The failure persists until acknowledged or a
successful retry clears it.

## Remaining UX limitations

- A cold 500-chapter workspace can take about 3.7 seconds to become fully
  ready, although staged loading communicates progress and warm reloads are
  fast.
- The normal local database contains legacy pre-RC8 validation projects. New
  E2E runs do not add to it, but old records require explicit user review rather
  than unsafe prefix-based deletion.
- Narrative-quality findings are decision support; subtle style judgments still
  require author/editor review.
