"""Process-wide provider request throttling."""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import Awaitable, Callable, Deque, Dict


class ProviderRateLimiter:
    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        window_seconds: float = 60.0,
        safety_seconds: float = 0.1,
    ) -> None:
        self._clock = clock
        self._sleep = sleep
        self._window_seconds = window_seconds
        self._safety_seconds = safety_seconds
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    @staticmethod
    def normalize_limit(limit: int | float | None) -> int:
        return max(5, min(int(limit or 5), 10))

    @staticmethod
    def is_app_limited(provider: str) -> bool:
        """Return whether NovelForge applies its conservative local throttle.

        Google AI Studio quotas are commonly low and were the reason this
        guard exists. Other hosted providers already enforce their own account
        and model limits; serialising OpenRouter, OpenAI, Anthropic, or Groq
        traffic here makes multi-agent orchestration unnecessarily stall.
        """
        return (provider or "").strip().lower() == "gemini"

    async def acquire(self, provider: str, limit: int | float | None) -> int:
        provider_key = (provider or "unknown").lower()
        if not self.is_app_limited(provider_key):
            return 0
        request_limit = self.normalize_limit(limit)
        waited = 0.0
        lock = self._locks[provider_key]
        while True:
            sleep_for = 0.0
            async with lock:
                now = self._clock()
                window = self._requests[provider_key]
                protected_window = self._window_seconds + self._safety_seconds
                while window and now - window[0] >= protected_window:
                    window.popleft()
                if len(window) < request_limit:
                    window.append(now)
                    return int(round(waited * 1000))
                sleep_for = max(
                    0.001,
                    protected_window - (now - window[0]),
                )
            await self._sleep(sleep_for)
            waited += sleep_for

    def reset(self) -> None:
        self._requests.clear()
        self._locks.clear()


provider_rate_limiter = ProviderRateLimiter()
