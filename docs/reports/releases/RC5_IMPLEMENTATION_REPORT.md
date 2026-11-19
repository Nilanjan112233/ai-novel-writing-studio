# NovelForge V2 RC5 Bounded Implementation Report

Date: 2026-07-19  
Status: approved implementation boundary produced after audit and before significant additions

## Objective

Make the frozen intelligence platform understandable, discoverable, proactive, and pleasant. RC5 adds application and presentation projections; it does not add narrative-analysis capabilities.

## Additions

### Application Knowledge Layer

A typed catalog will define every author-facing destination, page purpose, terminology, actions, statuses, workflows, agents, settings concepts, shortcuts, and next-step relationships. It will be the single contract for Assistant application answers, page guidance, tooltips, validated navigation, and capability documentation.

Application knowledge and story knowledge remain separate. The Assistant will classify queries as `application`, `project`, or `combined` before loading context. Pure application questions will not search Narrative Analysis first.

### Workflow guidance

Narrative Completeness remains the owner of progress. The Application Knowledge catalog will explain each recommended destination, while a guide projection will combine current milestone, blockers, dependency readiness, and the next uncompleted action.

### Companion state and recommendation lifecycle

Extend the existing Companion projection with:

- idle, thinking, working, celebrating, notifying, and sleeping presentation state;
- last interaction and last visit summaries;
- stable recommendation identity independent of completeness snapshot fingerprints;
- active, dismissed, completed, snoozed, and superseded lifecycle;
- cooldown and presentation count;
- dependency and completion checks;
- bounded daily/project recap language.

No duplicate story memory will be stored.

### Project and explainability timelines

Project Timeline will normalize existing project events, milestone history, canon decisions, and background completions into author-readable evolution entries.

Explainability Timeline will compare existing analysis snapshots and finding lifecycles to explain score deltas. It will not recalculate Story Health.

### Author-language presenters

Shared frontend presenters will convert evidence, entities, canon values, warnings, and graph details into cards and sentences. Technical fields remain available only when Developer Mode is explicitly enabled.

### Knowledge Graph UX

Keep the existing graph source. Add search/filter controls, typed node cards, status/importance/warnings/relationships/chapters/timeline/canon/health impact, explain/open/navigate actions, neighborhood expansion, centering, progressive loading, readable labels, and focus-visible keyboard behavior.

### Desktop shell and guidance

- grouped toolbox navigation;
- page header with what/why/do/next guidance;
- direct Canon Queue entry;
- validated one-click actions on every recommendation;
- companion/assistant collision handling;
- exact target desktop breakpoints;
- consistent states, terminology, tooltips, focus, and density.

The hard-coded Continue Writing placeholder will be removed from navigation and replaced by the existing governed Drafting destination. The Paragraph Editor implementation remains untouched.

## Validation gates

1. contract tests for the complete application catalog and every navigation target;
2. Assistant application/project/combined query tests;
3. recommendation lifecycle and cooldown tests;
4. Project Timeline and score-delta tests;
5. graph presentation and Canon discoverability frontend tests;
6. exact desktop viewport audit at 1366×768, 1440×900, 1920×1080, 2560×1440;
7. console/page-error/hydration/duplicate-key capture;
8. backend and frontend regressions;
9. clean production build;
10. full Playwright and real Gemini application/project Assistant proof;
11. RC5 documentation and known limitations.

## Implemented boundary

The planned projections are now implemented. The only Paragraph Editor change was a critical stale-hook closure correction required for warning-free production compilation; no paragraph editing capability was added. See `RC5_ARCHITECTURE_NOTES.md` for the final module boundaries and `RC5_TEST_RESULTS.md` for closure evidence.
