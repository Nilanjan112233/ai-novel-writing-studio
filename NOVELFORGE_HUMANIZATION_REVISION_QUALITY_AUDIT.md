# NovelForge Humanization and Revision Quality Audit

## Verdict

Humanization evidence is mixed. The protected selection-based rewrite made a real, specific improvement and preserved the original approved chapter. The protected whole-chapter revision path failed after real provider retries and produced no revision. Therefore humanization is not yet a reliable chapter-quality solution.

## Protected whole-chapter path

Source: approved Chapter 1, draft ID `a77de2f5-0059-4fdc-83f9-e0eeb55f8920`.

- Branch: `fad47a39-ebfe-4470-8d0e-3f74bd57e509`.
- Pass: development.
- Source status: approved.
- Source SHA: `a2dbbe6efa06b0879bf2c4c4c29a9aaea6e106726e7ec5a2ad7bbf660f25cf0e`.
- Editorial report: `34c63b9b-f5f6-4d6e-8724-afc255162bb1`.
- Editorial provider: OpenRouter / DeepSeek V4 Flash.
- Editorial score: 87 overall; style 88, voice consistency 92, pacing 85, emotional 87, progression 82, payoff 85.
- Findings: repeated “the weight of,” “she did not,” “she had never,” “it was not,” “she only knew,” “she wanted to,” and “she thought about”; recommendation to deepen sensory old-life material and keep cost palpable.
- Revision provider call: failed invalid JSON after retry count 2; 5,960 prompt-only tokens; `$0.005960` recorded cost.
- Result: no whole-chapter revision version created; source remained protected and unchanged.

## Selection-based path

Selected source passage: `Renn's hands remembered things her mouth couldn't explain.`

- Branch: `18e44bb4-39e1-4732-adfa-dba3754bf693`.
- Revision: `74920339-9a8f-475a-9737-92fe0e445c4e`.
- Pass: line.
- Instruction: natural rhythm and specific imagery while preserving facts.
- Provider: OpenRouter / DeepSeek V4 Flash.
- Trace total: 7,531 tokens; `$0.007531`; 19,697 ms.
- Revised passage: `Renn's fingers knew the cold of a different river, the vibration of a different wall under a different sky—knowledge that her mouth could not name.`
- Source hash after the operation: unchanged and equal to the protected branch source hash.
- Chapter 1 status: still approved; generated source text unchanged.

## Quality comparison

The selection revision is better than the source sentence because it replaces the vague “things” with cold, vibration, river, wall, and sky. It also preserves the old-life/current-life split and does not invent an event. The improvement is local and modest; it does not address Chapter 1's delayed grounding, backstory block, late dialogue, or generic ending.

The whole-chapter editorial report was valuable because it identified recurring patterns rather than claiming the chapter was ready. The failed revision means the application cannot yet prove that its protected humanization path can apply those findings across a chapter.

## UI findings

Editorial correctly communicates that approved drafts remain authoritative and alternatives are reviewable. However:

- branch creation used an unlabelled browser prompt;
- the selection rewrite was not easy to discover from the normal chapter-reading flow;
- failed generation did not make retry count, failure reason, and source protection visible enough;
- the user must understand branches and review versions before the safe workflow feels intuitive.

## Recommendation

Keep the protected architecture. Repair the whole-chapter provider/JSON path, add a deterministic protected-source check, and evaluate revisions blind for literary improvement, not only similarity or changed wording. Do not call humanization “working” based on the successful line rewrite alone.

