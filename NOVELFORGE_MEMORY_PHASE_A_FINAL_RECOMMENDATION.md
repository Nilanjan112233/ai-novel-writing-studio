# NovelForge Memory Phase A Final Recommendation

## Decision

**PHASE A IS COMPLETE ENOUGH TO PROCEED. NEXT: PHASE E.**

The evidence does not support starting Phase B first. Current Native retrieval is now correct, measurable, complete, and faster at 500 chapters. Its remaining synthetic recall limitation is known, but the much larger measured cost is Develop Story: 25 historical packets consumed 2.48M estimated prompt tokens, with a 97,463-token median, while Native recall contributed only about 2.6k–3.7k per packet.

## Recommended order

1. **Phase E — Develop Story role-specific context and delta handoffs.** Capture complete new per-source attribution, define specialist quality fixtures, reduce repeated Story Bible/prior-agent/workflow context, and target at least 50% prompt reduction without inferior output.
2. **Phase B — atomic derived memory and improved episode memory.** Only after Phase E, derive compact facts/episodes from existing authority and keep provenance/invalidation under the Phase A event ledger.
3. **Phase C — lexical + real semantic + story-specific candidates and fusion.** Use the Phase A corpus to improve the remaining 100+ chapter ranking/MRR limitations.
4. **Phase D — progressive fact → episode → evidence retrieval.** Add only after facts/episodes and relevance are measurable.

## Phase A follow-up, not a blocker

- add a background worker/scheduler for pending events so most projects reach READY before the next request;
- add an internal Developer Mode status surface if operators need it;
- require future owner services to emit project/domain events and add a coverage test when a new indexed collection is introduced;
- optimize rebuild bulk writes if 48-second 500-chapter repair becomes operationally material;
- address deprecation warnings separately.

## Explicitly do not implement next

Do not add Tencent authority/writing dependency, generic chatbot L1/L2 stores, a second Story Bible, destructive V1 cleanup, a graph database, or permanent inferred author preferences. Do not combine Phase B/C/D into one unmeasured rewrite.

## Acceptance criteria for Phase E

- complete per-source attribution for every new specialist call;
- at least 50% median/total prompt-token reduction on the same five-specialist cycles;
- non-inferior labelled specialist quality and authority coverage;
- zero P0 leakage/duplicate regressions;
- no new full index scans or writes during retrieval;
- provider cost, latency, and handoff deltas reported independently.

Tencent remains optional and experimental.
