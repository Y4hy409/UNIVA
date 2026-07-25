"""
CLARIUS Backend - Domain Event Bus

This module implements a lightweight, thread-safe domain event bus to enable
decoupled, asynchronous inter-module communication (ADR-007).
"""

import asyncio
from typing import Dict, List, Callable, Any, Awaitable
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger("clarius.events")

@dataclass
class DomainEvent:
    """Base class for all domain events."""
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime = datetime.utcnow()


# Type signature for event handlers
EventHandler = Callable[[DomainEvent], Awaitable[None]]


class DomainEventBus:
    """Thread-safe event registry and publishing bus."""
    
    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe a handler function to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        """Publish an event to all registered subscribers concurrently."""
        handlers = self._handlers.get(event.event_type, [])
        if not handlers:
            return
            
        async with self._lock:
            # Execute handlers concurrently as background tasks to prevent blocking publisher
            tasks = []
            for handler in handlers:
                task = asyncio.create_task(self._safe_execute(handler, event))
                tasks.append(task)
            
            # Fire and forget; don't wait for completion here
            # (Allows handlers to complete in background)
            
    async def _safe_execute(self, handler: EventHandler, event: DomainEvent) -> None:
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                f"Error executing event handler {handler.__name__} for event {event.event_type}: {str(e)}", 
                exc_info=True
            )


# Global singleton instance
event_bus = DomainEventBus()

def get_event_bus() -> DomainEventBus:
    """Dependency injection helper."""
    return event_bus
