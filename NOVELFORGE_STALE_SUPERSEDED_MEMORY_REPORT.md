# Stale and Superseded Memory Report

NovelForge’s authority ordering remains the protection against stale memory. Current canon, approved decisions, confirmed planning, and current structured owner records outrank candidates, extracted prose, raw conversation, and provider-derived memories. Superseded records remain historical/provenance-bearing rather than being silently deleted.

The Tencent adapter reinforces this boundary in two ways:

1. every Tencent event and recalled hit is marked non-authoritative;
2. writing-context calls pass `safe_for_writing=True`, which keeps Native as primary even when Tencent is configured experimentally.

The benchmark did not promote a rejected brainstorm, a superseded fact, or an external recall into story authority. No Tencent recall was allowed to override current NovelForge state.

## Remaining limitation

This pass did not claim a full labeled supersession benchmark across name, relationship, world-rule, reveal-timing, and location changes. That test belongs after Tencent retrieval is functioning; otherwise it would measure an empty result rather than memory correctness.
