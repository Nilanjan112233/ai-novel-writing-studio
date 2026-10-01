# RC5 Console Warning Report

## Application console

The dedicated RC5 Chromium workflow captures `console.warning`, `console.error`, and uncaught page errors. It completed with an empty captured list across application guidance, Drafting, Canon, Canon Queue, Project Timeline, Story Health History, Assistant, Companion, and Knowledge Graph navigation.

## Production build

The optimized Next.js build compiles and type-checks without React Hook, duplicate-key, hydration, or application build warnings. The earlier stale effect dependency warnings in `AiSuggestionPanel` and `ParagraphEditor` were corrected.

## Toolchain notices

The following non-application notices remain:

- Vite reports that its CJS Node API compatibility build is deprecated.
- pytest-asyncio reports that a future default fixture loop scope should be configured explicitly.
- Pydantic and FastAPI report upstream migration notices for class configuration, validators, JSON encoders, and startup/shutdown event decorators.
- Playwright’s spawned Node processes report that `NO_COLOR` is ignored when `FORCE_COLOR` is set.

These messages do not appear in the NovelForge author UI or browser application console. They are retained as dependency-upgrade work rather than hidden or misreported as product defects.
