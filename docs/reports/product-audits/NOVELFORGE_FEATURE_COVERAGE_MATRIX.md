# NovelForge Feature Coverage Matrix

Date: 2026-07-19

Legend: **Exists** = directly supported and integrated; **Partial** = foundation or isolated workflow exists but requested end-to-end behavior does not; **Missing** = no unified implementation.

## Narrative critique detection

| Capability | Status | Existing evidence | Gap to close |
|---|---|---|---|
| Plot holes | Partial | continuity reports, unresolved obligations, missing timeline dependencies, StoryAuditorAgent | no causal setup/payoff or required-event detector |
| Contradictions | Exists | canon conflicts, continuity reports, knowledge audience conflicts, shared findings | normalize routing into critique projection |
| Pacing problems | Exists | chapter length outliers, dead zones, repeated shape, Story Health pacing | add improvement ownership and workflow state |
| Weak motivations | Partial | character goals/motivations and AI reviewer context exist | no continuous motivation-to-action comparison |
| Inconsistent dialogue | Partial | DialogueAgent and repetitive dialogue detector | only explicit editorial review; not project-wide continuous critique |
| Missing emotional payoff | Partial | EditorAgent emotional progression/payoff readiness | not normalized into shared project findings |
| Unresolved mysteries | Exists | mystery status and shared plot findings | expose via critique routing |
| Weak foreshadowing | Partial | abandoned/unresolved foreshadow detection | no clue spacing, relevance, or payoff-strength analysis |
| Dangling plot threads | Exists | unresolved/abandoned plot and promise findings | expose improvement workflow |
| Worldbuilding inconsistencies | Partial | canon conflicts and Worldbuilding Consultant | no dedicated world rule/location/organization consistency rules |
| Timeline issues | Exists | impossible dates, duplicate order, missing dependencies, gaps | add travel/transition evidence where source metadata permits |
| Canon inconsistencies | Exists | typed/ledger conflict validation and Story Health | Canon Explorer transparency incomplete |
| Repetitive scenes | Partial | repeated chapter/paragraph/dialogue structure | no scene-purpose similarity detector |
| Redundant exposition | Partial | exposition phrase and DialogueAgent controls | not continuous across approved scenes/chapters |
| Structural weaknesses | Partial | StoryAuditorAgent and repeated chapter shape | not a stable categorized critique workflow |
| Weak chapter endings | Missing | no ending-strength detector | add approved chapter ending evidence lens |
| Weak chapter hooks | Missing | no hook detector | add opening/hook evidence lens distinct from repeated openings |
| Missing conflict escalation | Missing | tension/progression data exists | no cross-scene/chapter escalation curve detector |

## Canon transparency

| Capability | Status | Notes |
|---|---|---|
| Browse all canon | Partial | API returns all; UI shows active only and truncates each group. |
| Search canon | Missing | no author-facing search. |
| Filter canon | Partial | API supports type/active; UI does not. |
| Edit canon | Missing | must become governed change proposal, not direct overwrite. |
| Deactivate canon | Exists | API and UI supported with downstream rebuild. |
| Compare canon versions | Missing | source versions persist, but no comparison projection/UI. |
| Inspect canon history | Partial | promotion-history API and review reports exist; no unified detail view. |
| Source and evidence | Exists | stored and conflict evidence exposed. |
| Confidence | Partial | proposals/conflicts have it; registry records are inconsistent. |
| Originating chapter | Partial | derivable from sources but not normalized/displayed. |
| Relationships | Partial | available through graph edges, not canon detail. |
| Approval history | Partial | proposal/review/promotion records exist but are not joined. |

## Completeness and milestones

| Capability | Status |
|---|---|
| Story Completion | Missing unified score |
| Character Completion | Missing unified score |
| World Completion | Missing unified score |
| Power System Completion | Missing unified score |
| Relationship Completion | Missing unified score |
| Mystery Completion | Partial metrics only |
| Timeline Completion | Missing unified score |
| Canon Completion | Partial conflict metrics only |
| Remaining work list | Partial readiness/AI insights |
| Concept Complete gate | Missing |
| World Ready gate | Missing |
| Draft Ready gate | Partial arc drafting eligibility only |
| Revision Ready gate | Missing |
| Publication Ready gate | Partial manuscript/readiness indicators only |

## Companion, memory, and guide

| Capability | Status | Notes |
|---|---|---|
| Persistent assistant | Partial | drawer persists in workspace, but must be opened. |
| Proactive status | Partial | banner/run status exist, not a companion feed. |
| Background completion reaction | Missing | project events exist but are not interpreted by a companion. |
| Milestone celebration | Missing | milestone model absent. |
| Next action | Partial | backend and frontend each derive one independently. |
| Onboarding/page help | Partial | Assistant can answer from project evidence but lacks guide metadata. |
| Structured user knowledge | Partial | decisions/canon exist, mostly free text. |
| Confidence rules | Missing | current two-token threshold is insufficient. |
| Provenance | Partial | source IDs/versions exist; routing/approval chain is incomplete. |
| Cross-agent reuse | Partial | Story Bible, retrieval index, and per-agent memory exist. |
| Duplicate question prevention | Partial | fuzzy question suppression exists. |
| Interactive creation guide | Missing | destinations exist; guide model/UI does not. |
| Free step navigation | Exists as toolbox | not organized as a guided pipeline. |
| Completion percentage | Missing | arc readiness percentages do not represent project creation. |

