# Context and Memory Report

The native path remains primary. Context now prioritizes current request/target, authoritative canon, approved decisions, timeline, relevant characters/threads, unresolved questions, retrieval results, recent prose, and compressed memory. Retrieval is bounded to eight relevant records before the existing token-cap trimming.

ObjectId values remain valid Mongo persistence values and are stringified only at prompt token-measurement boundaries. This fixes context construction without changing stored provenance.

TencentDB Agent Memory was deliberately not integrated. It is an optional future `MemoryProvider` adapter candidate only after native retrieval is benchmarked. It must never own canon, decisions, Story Bible, timeline authority, approved prose, or manuscript state.

