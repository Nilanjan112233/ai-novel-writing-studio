# NovelForge Real Ten-Chapter Novel Audit

Date: 2026-08-16 (Asia/Calcutta)

## Executive verdict

NovelForge completed a real-provider ten-chapter generation journey in an isolated project, but it did not pass a real-novel acceptance bar. The project is not ready for an author to trust with a first serious novel without an authority-safe writing pass.

The generated material has a promising seed: a practical disaster-mapping mind reincarnated into a poor river household, a failing levy, and a perception of seams between unrealized outcomes. Chapter 1 has a genuine local problem, a readable close-third voice, a cost-bearing power, and a reason to continue. It is not yet a strong published opening because the reader receives the protagonist's present identity and the reincarnation frame too late, while the old-life explanation arrives as a concentrated backstory block.

The decisive production failures were:

- Chapter 2 switches from Renn/she to a ten-year-old boy/he and assumes a different farm-family setup. It was not approved.
- A retry intended for Chapter 2 created Chapter 3 because the continuation service computed the next number from the latest raw draft. Two Chapter 4 drafts were then created by a late provider completion plus a retry; both raw records remained active/version 1.
- Develop Story generated a large provisional plan around “Kael,” a farm, a well, and a buried-sky arc even though the author had not confirmed those details and had explicitly left the exact identity and setting open.
- The controlled Drafting surface remained empty while Discovery Writing held ten chapters. The application describes the project as mixed workflow, which is technically accurate but not novice-comprehensible.
- The full-chapter protected revision path failed with invalid JSON after retries. The smaller protected selection rewrite succeeded and improved one sentence without altering the source.

## Test identity and scope

| Item | Evidence |
|---|---|
| Isolated project | `6a81af51cd566e919fdc052b` |
| Project name | `REAL NOVEL AUDIT — Ashes of the Unwritten Sky — 20260816` |
| Story title | `Ashes of the Unwritten Sky` |
| Backend | `http://127.0.0.1:8005/health`, healthy, `novelforge-api`, `2.0.0-rc9` |
| Frontend | `http://localhost:3000` |
| Database/workflow | Real MongoDB-backed application paths; no mock responses in the main journey |
| Provider path | Normal NovelForge gateway; Story Studio used Gemini; Develop Story and writing used OpenRouter DeepSeek V4 Flash |
| Memory | Native Phase C production mode; Tencent remained observational/non-authoritative and was not enabled for writing |
| Browser acceptance | In-app Browser used for project creation, Story Studio, Develop Story, writing, review, Toolbox, Companion, and navigation |
| Project disposition | Preserved for manual inspection; no unrelated projects were deleted |

## Author journey exercised

1. Created the project through the normal UI/API workflow with a flexible reincarnation/progression premise.
2. Held four Story Studio turns: useful questioning, author answers, explicit brainstorming, and explicit rejection/confirmation.
3. Verified that brainstorming did not mutate canon, then ran Develop Story from the current discussion.
4. Ran the normal discovery writing flow at a 2,000–3,000-word target.
5. Generated Chapters 1–10 through actual provider calls. Chapter 1 was approved through the normal status endpoint after the UI approval action failed to refresh reliably. Chapters 2–10 were deliberately left drafts when they were not safe to approve.
6. Inspected chapter context, writing state, memory-provider status, Story Studio, Companion, Dashboard, Writing, Story Vision, Questions, Characters, World, Relationships, Arcs, Timeline, Drafting, Story Health, Knowledge, Canon, Manuscript, Editorial, and Settings.
7. Ran the protected editorial review path, a failed whole-chapter protected revision, and a successful selection-based protected rewrite.

## Chapter inventory

The UI exposed ten chapters. Mongo contained eleven raw discovery drafts because Chapter 4 was duplicated.

| Chapter | Draft ID | Words | Status | Versions shown | Provider | Tokens recorded | Latency ms | Notes |
|---:|---|---:|---|---:|---|---:|---:|---|
| 1 | `a77de2f5-0059-4fdc-83f9-e0eeb55f8920` | 2,664 | approved | 1 | OpenRouter / DeepSeek V4 Flash | 16,647 | 44,911 | Good local opening; extraction candidate-only |
| 2 | `c6b029c3-a7d3-480a-9a9b-e4fe649f19dc` | 2,885 | draft | 1 | OpenRouter / DeepSeek V4 Flash | 16,528 | 50,692 | Fatal identity/POV continuity break |
| 3 | `3ae9a7f7-ff29-48dd-a0ac-489c91f431b4` | 2,435 | draft | 1 | OpenRouter / DeepSeek V4 Flash | 16,552 | 73,733 | Corrected Renn/she direction; depends on a broken Ch2 |
| 4A | `f949eb14-f4a8-44c3-b3a7-06d314b79e24` | 2,430 | draft | raw version 1 | OpenRouter / DeepSeek V4 Flash | 18,175 | 46,666 | Late completion from an earlier retry |
| 4B active | `60ba454c-7a94-4f2e-978f-5cc094a06032` | 2,569 | draft | UI version 2 | OpenRouter / DeepSeek V4 Flash | 16,794 | 187,598 | Active UI version; duplicate raw records remain active/version 1 |
| 5 | `06b14f9d-8487-4920-8c1b-69dfa6d94e09` | 2,335 | draft | 1 | OpenRouter / DeepSeek V4 Flash | 14,995 | 59,523 | Escalates missing Darin/seam mystery |
| 6 | `bd45bef7-921d-4ea0-961c-c1d5e8b1fa84` | 2,151 | draft | 1 | OpenRouter / DeepSeek V4 Flash | 16,090 | 86,517 | Deeper well/seam escalation |
| 7 | `3c3aa50d-1175-4469-bb1c-6f3044e07feb` | 2,999 | draft | 1 | OpenRouter / DeepSeek V4 Flash | 18,017 | 129,452 | Introduces suture-bearer lore; increasingly plan-driven |
| 8 | `34e201c7-673f-44c2-a85d-225f6f2391af` | 2,230 | draft | 1 | OpenRouter / DeepSeek V4 Flash | 17,597 | 121,293 | Keeps seam/blight/other-world hooks, weakens local specificity |
| 9 | `078cb917-3394-4fb3-9188-2a837e6a58a8` | 2,409 | draft | 1 | OpenRouter / DeepSeek V4 Flash | 16,844 | 53,385 | Quiet levy-road chapter; still repeats abstract hooks |
| 10 | `6a2e7afd-120f-4168-92a9-b33c5f8da74b` | 2,268 | draft | 1 | OpenRouter / DeepSeek V4 Flash | 17,023 | 51,816 | Strongest later hook; not canonically safe |

Unique Chapters 1–10 contained 167,087 provider-recorded tokens, approximately `$0.167087` under the gateway's recorded one-token cost convention. Including the duplicate Chapter 4 call, the raw writing journey consumed 185,262 recorded tokens, approximately `$0.185262`.

## Acceptance results

| Acceptance area | Result | Evidence |
|---|---|---|
| Fresh isolated project | Pass | Exact project ID above; preserved |
| Conversational Story Studio | Partial | Four real turns; questions useful, but second turn misclassified as review and no visible confirmed/candidate controls |
| Rejected ideas remain rejected | Partial | The chat response acknowledged rejection; Develop Story still injected provisional Kael/farm/well material into writing context |
| Develop Story uses discussion | Partial/fail | It used seam/local-problem themes, but also over-planned and invented unconfirmed structure |
| Real Chapter 1 generation | Pass as execution, fail as literary acceptance | 2,664 words, provider success, readable opening, not safe as final prose |
| Chapter 1 approval workflow | Partial | Direct status update succeeded; visible UI did not refresh to approved until later and showed stale draft state |
| Chapter 2 continuation | Fail | He/him, ten-year-old boy, farm-family assumptions after Chapter 1's Renn/she/fifteen-year-old river-household opening |
| Chapter retry/idempotency | Fail | Ch2 retry produced Ch3; delayed Ch4 completion plus retry produced duplicate Ch4 |
| Chapters 2–10 | Partial at best | Later chapters mostly return to Renn/she and preserve seam/Darin/blight direction, but they inherit the Ch2 break and remain unapproved |
| Memory retrieval | Fail for authority-safe writing | Ch1 candidate extraction is labeled candidate, but provisional Kael and large Develop threads dominate later context |
| Humanization/revision | Partial | Protected selection revision passed; full chapter revision failed before output |
| UI novice journey | Fail | Story Studio, Discovery Writing, controlled Drafting, Toolbox truth, Canon, Knowledge, and health states do not form one understandable path |
| Audit integrity | Fail | `/audit` returned `status: fail` with invalid `cycle_generated` metadata in character bibles, mysteries, and relationship graphs |

## What is genuinely promising

- The seed is more distinctive than a generic “truck, god, status window” opening. The old-life emergency-infrastructure reflex, local levy, and costly seam perception can support a real progression novel.
- Chapter 1 begins with a physical problem rather than a lore lecture and avoids an instant overpowered reward.
- The power has an appropriate initial limit: perception before manipulation, physical pain, memory/emotional cost.
- The application can preserve approved prose, keep revisions as branches, and label Ch1 extraction as candidate rather than silently making it canon.
- Native Phase C was kept as production default, and the provider status correctly says MongoDB story systems remain authoritative.

## What must be fixed before a real novel

1. Make chapter numbering, retries, and delayed completions idempotent and anchored to an explicit target chapter/draft, not the latest raw document.
2. Prevent provisional Develop artifacts from entering the writing context as if they were the author's chosen protagonist, family, location, or power details.
3. Add a Chapter 1 opening gate that forces present identity, location, immediate human stakes, and POV grounding before extended backstory or system material.
4. Make approval and refresh state authoritative in the visible UI.
5. Make the Discovery Writing and controlled Drafting workflows explain their relationship or provide one clear default author path.
6. Add a real continuation check for identity, pronouns, age, family structure, active problem, and rejected planning constraints before a draft can be presented as a natural continuation.
7. Repair the protected whole-chapter revision path and expose the source/branch/review state clearly in the UI.

## Recommended implementation phase

After author review, the next phase should be an “Authority-safe writing journey” phase. It should be narrowly grounded in this audit: chapter lifecycle/idempotency, provisional-versus-confirmed retrieval, Chapter 1 opening context, approval-state synchronization, candidate review, and real-provider continuation regression. Do not enable Phase D or Tencent as a writing primary; neither is needed to explain these failures.

