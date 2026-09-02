"""Central Domain Event Bus for decoupling backend domain events from downstream execution."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List

logger = logging.getLogger(__name__)

# Callback type signature: must be an async callable taking event_data dict
EventCallback = Callable[[Dict[str, Any]], Awaitable[None]]

class DomainEventBus:
    """A thread-safe, asynchronous in-memory event bus for domain events."""
    
    _instance: DomainEventBus | None = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DomainEventBus, cls).__new__(cls, *args, **kwargs)
            cls._instance._subscribers = {}
        return cls._instance

    def subscribe(self, event_type: str, callback: EventCallback) -> None:
        """Register a callback for a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)
            logger.info(f"Subscribed callback {callback.__name__ if hasattr(callback, '__name__') else callback} to event: {event_type}")

    def unsubscribe(self, event_type: str, callback: EventCallback) -> None:
        """Unsubscribe a callback from an event type."""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                logger.info(f"Unsubscribed callback from event: {event_type}")
            except ValueError:
                pass

    def publish(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Publish a domain event asynchronously in the background."""
        subscribers = self._subscribers.get(event_type, [])
        if not subscribers:
            logger.debug(f"Published event '{event_type}' but no subscribers were registered.")
            return

        logger.info(f"Publishing event '{event_type}' to {len(subscribers)} subscribers.")
        
        # Fire-and-forget background execution of subscribers
        for callback in subscribers:
            asyncio.create_task(self._safe_execute(callback, event_type, event_data))

    async def _safe_execute(self, callback: EventCallback, event_type: str, event_data: Dict[str, Any]) -> None:
        """Safely execute a callback catching and logging any errors to prevent pipeline failure."""
        try:
            await callback(event_data)
        except Exception as e:
            logger.exception(f"Error executing callback on event '{event_type}': {e}")


# Singleton instance of the domain event bus
domain_event_bus = DomainEventBus()
