# Model Routing and Cost Report

The existing provider gateway remains the runtime authority. `TASK_TIERS` is policy metadata, not a hard-coded permanent model assignment.

| Work | Tier | Policy |
|---|---|---|
| navigation, classification, extraction, tagging, summarization | lightweight | deterministic code first; Flash-Lite/free model when semantics are needed |
| ordinary brainstorming and routine explanation | cheap | free/low-cost capable model |
| continuity, canon-impact reasoning, difficult reconsideration | strong | stronger reasoning model with validation |
| final prose, major revisions, difficult continuity | strong/premium | preserve author/provider choice; DeepSeek V4 Flash-class or explicitly selected premium model |

Malformed JSON, empty output, provider timeout/rate limit, low confidence, or validation/continuity failure should retry through the gateway and escalate. Discovery extraction already has conservative local fallback. No validation was weakened for cost.

Typical low-cost conversation: deterministic intent classification plus one assistant call. Typical discovery chapter: one strong prose call, one existing validation pass, and one lightweight extraction call after approval. Read-only questions do not create canon proposals. The exact dollar cost depends on the author's selected provider/model and token usage recorded by the existing gateway.

