# Tencent Failure and Fallback Report

The gateway was stopped during a live application request. NovelForge recorded `ConnectError: All connection attempts failed`, retained `configured_primary: tencent`, selected Native as the actual primary, returned five Native hits, and kept `authoritative: false`.

Focused provider tests pass 6/6, including Tencent failure fallback, hybrid safe-for-writing behavior, documented conversation-search fallback, and message-boundary parsing. Full backend regression also passed. Native project operation therefore remains available when Tencent is unavailable; backup/recovery does not depend on the derived Tencent index.

