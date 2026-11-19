# Tencent Retrieval Smoke-Gate Result

The browser-visible smoke gate passed after the clean gateway restart:

| Check | Result |
|---|---:|
| Labeled memories captured | 10/10 |
| Labeled memories recalled | 10/10 |
| Minimum required | 8/10 |
| Provenance present | yes |
| Authoritative | no |
| Browser-observed average recall | 547.1 ms |

The API smoke gate independently passed 10/10 with approximately 510.6 ms average recall. Captures were scoped to the NovelForge provider session key, so the gate also checks project/session isolation. The gate is run through NovelForge’s settings endpoint and UI; it is not a direct external benchmark script.

