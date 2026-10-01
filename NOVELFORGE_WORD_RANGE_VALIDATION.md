# NovelForge Word-Range Validation

## Implemented behavior

Discovery generation now persists minimum, target, maximum, compliance, and bounded range attempts. If output is outside the requested range, the gateway can make one constrained editorial correction. If the corrected result remains under the minimum, a bounded continuation pass can append a connected scene instead of truncating prose or silently accepting failure.

## Live results

| Chapter | Min | Target | Max | Actual | Attempts | Compliance |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 1,000 | 1,100 | 1,200 | 1,735 | 0 | no |
| 2 | 1,000 | 1,100 | 1,200 | 1,128 | 1 | yes |
| 3 | 1,500 | 1,700 | 2,000 | 1,179 | 2 | no |
| 4 | 2,000 | 2,300 | 3,000 | 2,573 | 1 | yes |
| 5 | 1,000 | 1,100 | 1,200 | 1,101 | 2 | yes |
| 6 | 1,000 | 1,100 | 1,200 | 1,177 | 1 | yes |

The absolute acceptance floor passed for all chapters. Exact range behavior did not. Chapter 1 shows that a strong writer can overshoot when the initial response is already coherent. Chapter 3 shows that a single correction call is not enough for a 1,500-word minimum. The implementation avoids unsafe giant responses and preserves one immutable chapter result, but should next use scene-sized planning/assembly for larger ranges.

The structured workflow was not redesigned in this hardening phase; parity of range controls remains incomplete.

