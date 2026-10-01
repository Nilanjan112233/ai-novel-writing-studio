# NovelForge V2 Phase 7 Implementation Plan

## Frozen boundaries

- Preserve the Phase 6 Narrative Analysis Engine as the sole story-analysis authority.
- Preserve the Paragraph Editor architecture and add no paragraph capability.
- Use existing Canon Governance, Change Impact, Timeline Intelligence, Story Bible, provider gateway, settings, and project event services.

## Delivery slices

### 7A — Character Conversations

- Build a chronology-bounded context selector over Narrative Analysis and Story Bible data.
- Persist project- and character-scoped conversation turns and reusable memories.
- Enforce death and learned-information boundaries.
- Route generated facts to canon proposals.

### 7B and 7G — Project Assistant and modes

- Add one workspace-wide assistant with six reasoning lenses.
- Ground every answer in the current analysis snapshot and persist evidence identifiers.
- Emit deterministic typed navigation actions for chapters, scenes, and intelligence workspaces.

### 7C — Knowledge Graph

- Project live Narrative Analysis nodes and edges directly into an interactive graph.
- Add kind/search filters and evidence-rich node inspection.
- Do not add a duplicate graph store.

### 7D — Canon proposals

- Persist proposals with confidence, evidence, affected locations, provenance, and Change Impact.
- Require explicit author review and high-impact confirmation.
- On approval, promote through Canon Governance, rebuild Story Bible, and incrementally refresh Narrative Analysis.

### 7E and 7F — Workspace Intelligence and explainability

- Add an ambient recommendation banner to project surfaces.
- Reuse Narrative Analysis finding identifiers for contextual guidance.
- Expose rule, evidence, contributing chapters/scenes/elements, canon/timeline references, confidence, action, and analysis identifier.

### Persistence and lifecycle

- Add idempotent Phase 7 indexes.
- Include interaction collections in database audit and project deletion.
- Extend Story Bible with interaction memory, assistant history, proposal queue, and source policy.

## Validation gates

- RC1: focused backend and frontend capability tests.
- RC2: full backend/frontend regression, production build, focused and broad Playwright, real `gemini-3.1-flash-lite` provider proof, and 500-chapter benchmark.
- RC3: desktop/mobile visual review, keyboard/semantic navigation, explainability clarity, and overflow review.
- RC4: architecture, five workflow walkthroughs, results, benchmark, limitations, and completion report.

