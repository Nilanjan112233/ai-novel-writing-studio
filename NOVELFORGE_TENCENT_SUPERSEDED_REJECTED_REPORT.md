# Superseded and Rejected Memory Report

Synthetic authority test results:

- Direct Tencent retrieval returned both the old fact “Elias disappeared two years ago” and the current confirmed fact “Elias disappeared five years ago.”
- Direct Tencent retrieval also returned a rejected brainstorm (“Maybe the king is Mara’s father”).
- NovelForge safe-for-writing retrieval selected Native as primary, returned the five-year confirmed fact, did not return the two-year stale fact in the primary packet, and marked the comparison non-authoritative.
- The rejected brainstorm was never indexed into Native authority and did not enter the safe primary packet.

This is the required behavior for an untrusted memory provider: Tencent may remember historical/raw observations, but current decisions and governed structured state outrank it. Tencent must not be used as a writing-primary source until authority and supersession filtering is applied outside Tencent.

