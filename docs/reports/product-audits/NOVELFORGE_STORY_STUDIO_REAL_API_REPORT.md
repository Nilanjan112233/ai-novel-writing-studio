# NovelForge Story Studio Real API Report

## Tested through the running UI

- Project question: answered with a grounded recommendation and no mutation.
- Brainstorm: after correcting a classifier false positive, “Do not change canon” returned alternatives without a decision gate or mutation.
- Ambiguous mutation: explicitly displayed that nothing had changed and requested author confirmation.
- Explicit mutation: went through the governed action path and created no authoritative state because no owning record existed.
- Contradiction review: completed, but the result was too generic and navigational rather than a strong contradiction analysis.
- Writing request: opened the Discovery Writing flow, generated real prose, and used the normal review/approval controls.

The chat is a control layer, not a second authority. Long generation showed author-facing loading/progress state, and provider retries were recorded. A notable UX issue remains: approval can display “Approval did not complete” while extraction/intelligence work is still completing; the backend later showed the chapter approved. This needs a durable job/progress surface and clearer retry semantics.

