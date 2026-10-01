# Phase 7 E2E and Regression Results

Date: 2026-07-18  
Status: PASS

## Provider validation

The encrypted Google AI Studio credential already stored by NovelForge was exercised through the normal provider gateway. No credential was printed or copied into test code.

- Provider: Google AI Studio
- Requested and returned model: `gemini-3.1-flash-lite`
- Settings model test: HTTP 200
- `NarrativeProjectAssistant` generation: HTTP 200
- `CharacterConversationAgent` generation: HTTP 200
- Result: live inference confirmed; Phase 7 browser proof used the real provider rather than a mocked conversation response

## Automated results

### Backend

Command:

```text
py -3.11 -m pytest backend/tests -q
```

Result: **94 passed, 7 skipped** in 298.56 seconds.

The skipped cases are pre-existing optional/integration paths. Phase 7's focused backend coverage passed 5/5 and includes graph reuse, explainability, navigation, chronology/death boundaries, conversation memory, canon proposal governance, migrations, audit integrity, and deletion cleanup.

### Frontend

Command:

```text
npm test -- --run
```

Result: **54 passed** across 13 test files in 20.71 seconds.

Phase 7 component coverage includes Assistant navigation, Character Conversation interaction, Knowledge Graph evidence, proposal review, explainability, contextual recommendations, and the Story Health refresh-order regression.

### Production build

Command:

```text
npm run build
```

Result: **PASS**. Type checking, compilation, prerendering, and route generation completed.

- Project workspace route: 197 kB
- Project workspace first load: 346 kB
- Shared first load: 99.2 kB

Two existing React hook dependency warnings remain in `AiSuggestionPanel.tsx` and the frozen `ParagraphEditor.tsx`; neither is a build error.

### Playwright

The broad serial Chromium matrix executed 38 journeys. Its first pass produced 33 passed, 2 intentionally skipped, and 3 failures. The failures were investigated rather than retried blindly:

1. new paragraph comments were persisted with a legacy `pending` status while the UI expected `open`;
2. an empty legacy Story Bible health projection could overwrite the dedicated Story Health response;
3. one workflow title locator was ambiguous under strict mode.

After correction, the exact closure matrix passed **4/4** in 1.1 minutes:

```text
npx playwright test \
  e2e/paragraph-editor-productivity.spec.ts \
  e2e/phase6-story-intelligence.spec.ts \
  e2e/workflow.spec.ts \
  e2e/interactive-narrative-phase7.spec.ts \
  --project=chromium --reporter=line
```

The dedicated live-provider Phase 7 journey subsequently passed repeatedly (clean post-build restart: 35.3 seconds). It proves:

- stored Gemini model configuration;
- grounded Project Assistant response and typed workspace navigation;
- Character Conversation with a Chapter 3 death/awareness boundary;
- live Knowledge Graph selection and evidence inspector;
- canon proposal creation, approval, Story Bible rebuild, and analysis refresh;
- contextual recommendations and `Why was this generated?` evidence;
- database audit integrity and project deletion cleanup;
- 390 px mobile drawer bounds and no document-level horizontal overflow.

Evidence images:

- `artifacts/phase7-interactive-studio-desktop.png`
- `artifacts/phase7-interactive-studio-mobile.png`

## Performance benchmark

Command:

```text
py -3.11 backend/scripts/run_phase_7_benchmark.py
```

Measured cached-read scenario:

| Scenario | Scale | Result |
|---|---:|---:|
| Knowledge Graph | 500 chapters, 100 characters, 600 nodes, 999 edges | 0.2171 s |
| Repeated cached graph | same analysis ID, 600 nodes | 0.2092 s |
| Workspace Intelligence | cached graph, 1 recommendation | 0.0244 s |

The machine-readable result is `artifacts/phase7-performance-benchmark.json`.

## Regression closure

The Paragraph Editor architecture remains frozen. Phase 7 added no paragraph editing capability. The only editor-area change was the critical status compatibility defect above: new comments now use `open`, while old `pending` comments remain visible and replyable.
