"""In-process asynchronous event and P2P reactive message bus for agent sessions."""
from __future__ import annotations

import asyncio
import datetime
import inspect
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Set

from archon.exceptions import InvalidRecipientError, MessageBusClosedError


class MessageBus:
    """Reactive message bus providing both pub/sub events and direct P2P FIFO message queues."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[..., Any]]] = defaultdict(list)
        self._recipient_queues: Dict[str, asyncio.Queue] = {}
        self._is_closed: bool = False

    @property
    def is_closed(self) -> bool:
        """True if the message bus has been closed."""
        return self._is_closed

    def register_recipient(self, agent_id: str) -> None:
        """Register an agent identifier to receive direct and broadcast messages."""
        if self._is_closed:
            raise MessageBusClosedError("Cannot register recipient on a closed MessageBus.")
        if agent_id not in self._recipient_queues:
            self._recipient_queues[agent_id] = asyncio.Queue()

    def unregister_recipient(self, agent_id: str) -> None:
        """Unregister an agent recipient and discard its remaining queue."""
        self._recipient_queues.pop(agent_id, None)

    async def send_message(
        self,
        sender_id: str,
        recipient_id: str,
        payload: Any,
        event_type: str = "TASK_UPDATE",
        priority: str = "NORMAL",
    ) -> None:
        """Send a direct message or broadcast to registered recipient agents."""
        if self._is_closed:
            raise MessageBusClosedError("Cannot send message to closed MessageBus.")

        msg = {
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "payload": payload,
            "event_type": event_type,
            "priority": priority,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        if recipient_id == "*":
            # Broadcast to all registered recipients
            for q in list(self._recipient_queues.values()):
                await q.put(msg)
            return

        if recipient_id not in self._recipient_queues:
            raise InvalidRecipientError(
                f"Recipient agent '{recipient_id}' not found in session."
            )

        await self._recipient_queues[recipient_id].put(msg)

    async def receive_message(
        self,
        agent_id: str,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Receive the next FIFO message for the specified recipient agent."""
        if self._is_closed:
            raise MessageBusClosedError("Cannot receive message from closed MessageBus.")

        if agent_id not in self._recipient_queues:
            raise InvalidRecipientError(
                f"Recipient agent '{agent_id}' not registered in MessageBus."
            )

        queue = self._recipient_queues[agent_id]

        if timeout is not None:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=timeout)
            except asyncio.TimeoutError:
                raise TimeoutError(f"No message received for '{agent_id}' within {timeout}s.")
        else:
            item = await queue.get()

        if self._is_closed:
            raise MessageBusClosedError("MessageBus was closed while waiting for message.")

        return item

    def subscribe(self, event_type: str, handler: Callable[..., Any]) -> None:
        """Register a callback for an event type."""
        if self._is_closed:
            raise MessageBusClosedError("Cannot subscribe on closed MessageBus.")
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable[..., Any]) -> None:
        """Unregister a callback for an event type."""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    async def publish(self, event_type: str, payload: Any = None) -> None:
        """Publish an event to all registered subscribers."""
        if self._is_closed:
            raise MessageBusClosedError("Cannot publish on closed MessageBus.")

        handlers = list(self._subscribers.get(event_type, []))
        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    await handler(payload)
                else:
                    res = handler(payload)
                    if inspect.isawaitable(res):
                        await res
            except Exception:
                # Subscriber failures should not crash the publisher
                pass

    def clear(self) -> None:
        """Clear all subscribers and recipient queues."""
        self._subscribers.clear()
        self._recipient_queues.clear()

    def close(self) -> None:
        """Close the message bus and release all queued resources."""
        self._is_closed = True
        self.clear()
