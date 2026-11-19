# RC5 Desktop UX Audit Report

Date: 2026-07-19  
Target: desktop only

## Baseline results

The existing desktop stability suite visited the projects page, all current project sections, and AI settings at four widths. Result: **12 passed, 0 failed**. No page-level horizontal overflow was detected.

The suite used 1280, 1440, 1920, and 2560 pixel widths at 900 pixels high. RC5 validation must replace/add the requested exact targets: 1366×768, 1440×900, 1920×1080, and 2560×1440.

The baseline production build completes but is not warning-clean. It reports missing React Hook dependencies in `AiSuggestionPanel.tsx` and `ParagraphEditor.tsx`. These will be treated strictly as defect corrections—no paragraph capability or architecture change.

## Shell and hierarchy

- The 64-pixel icon rail is visually clean but the controls are unlabeled until hover.
- The 256-pixel toolbox contains twenty-seven flat destinations. At 768 pixels high, scrolling is unavoidable and workflow relationships are not visible.
- The header identifies the project and provides Run Cycle, but does not explain the current page.
- The intelligence banner competes with page titles and repeats findings already shown in Story Health.
- The Assistant overlay covers 480 pixels of the right side. At 1366 pixels, the remaining main workspace becomes narrow while the toolbox remains open.
- The Companion occupies the bottom-right action area and can collide visually with long forms or the Assistant.

## Typography, cards, and spacing

- Page titles range from absent to repeated inside nested panels.
- Technical uppercase labels are overused where short author language would be clearer.
- Dashboard cards use a consistent border system, but information hierarchy is weak because health, pipeline, critique, and dashboard summaries are stacked as equal-weight sections.
- Dense surfaces rely on multiple nested bordered cards, reducing scanability.
- Evidence is frequently shown in monospace/raw form, breaking the visual language of the rest of the product.

## States

| State | Audit |
|---|---|
| Loading | Present but inconsistent; several surfaces show plain text while others use spinners. |
| Empty | Present on some collections, often “None yet” without a reason or next action. |
| Error | Usually inline, but recovery actions are uncommon. |
| Success | Often implied by changed data; explicit success confirmation varies. |
| Warning | Severity colors exist, but author impact and navigation are inconsistent. |
| Focus | Standard controls are acceptable; custom icon rail and graph nodes need explicit focus-visible treatment. |
| Tooltips | Primary icon rail uses `title`; most unfamiliar controls have no contextual tooltip. |
| Scrollbars | Functional, but nested page/toolbox/assistant scrolling creates three simultaneous scroll regions. |

## Visual evidence findings

- Story Health exposes “nodes,” “dependencies,” “cached,” recomputation count, and milliseconds in the author view.
- Canon displays `legacy` source language and subject-field dotted identifiers.
- Assistant displays a shortened analysis identifier.
- Context recommendations can repeat the same issue twice in one visible drawer.
- Companion collapsed messages truncate before conveying the action.
- Graph node details serialize internal payloads rather than presenting readable fields.

## Desktop completion criteria

RC5 is not complete until all four exact desktop targets pass:

- no viewport or component overflow;
- no overlapping Companion/Assistant/action controls;
- no unlabeled interactive control;
- no raw technical metadata outside Developer Mode;
- visible focus for keyboard interactions;
- one clear page title, purpose, and next action;
- consistent empty/loading/error/success language;
- clean application console and production build.

## RC5 resolution

- The desktop suite now uses the exact requested targets: 1366×768, 1440×900, 1920×1080, and 2560×1440.
- All cataloged workspace destinations, including Canon Queue, Knowledge Graph, Project Timeline, and Story Health History, are included in the overflow sweep.
- The toolbox is grouped by the shared Application Knowledge workflow hierarchy.
- Every primary icon-rail action has an accessible label and visible focus treatment.
- The Companion is bounded to the desktop corner, uses a scroll-contained panel, and respects reduced motion.
- Page Guidance establishes one purpose/why/do/next hierarchy on every workspace destination.
- Raw evidence and technical diagnostics were replaced by author cards or moved behind Developer Mode.
- Settings keeps provider connection tasks visible but hides routing, budgets, agents, and diagnostics until Developer Mode is selected.

Final command evidence is recorded in `RC5_TEST_RESULTS.md`.
