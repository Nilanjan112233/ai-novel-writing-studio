# Memory Token and Context Comparison

## Live measurements

The matched eight-query comparison recorded Native context estimates of 1,365, 2,112, 1,593, 1,722, 1,758, 1,671, 2,394, and 291 tokens, averaging 1,613.2 tokens. Native returned five hits per query.

Tencent recorded zero context tokens because every query returned an empty recall. Its average request latency was 303.1 ms versus Native’s 218.8 ms. The zero token figure must not be interpreted as efficient compression: no relevant content was supplied.

## Context policy

NovelForge continues to use relevance-first bounded context rather than filling the model window. Context Engine prioritizes current request, authority, structured state, relevant unresolved material, recent approved prose, Story Bible, Narrative Intelligence, and only then retrieved memory. Tencent-derived hits are not allowed to bypass that ordering.

## Conclusion

No valid Tencent token-saving claim can be made yet. A future comparison must measure equal-quality writing packets, not an empty Tencent packet versus a useful Native packet.
