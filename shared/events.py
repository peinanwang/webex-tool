"""In-process event bus for live UI updates (Server-Sent Events).

When something changes (a message is stored, the assistant replies, focus turns on/off, a summary is
made), the code calls publish(). Every open browser tab has an SSE connection (see listener/api.py)
that subscribed a queue here, and receives the event.

publish() is called from worker threads (the poller, the agent) while the SSE handlers run on the
web server's asyncio event loop. call_soon_threadsafe hands each event to the loop safely.
In the MCP server process nobody subscribes, so publish() does nothing there.
"""

import asyncio
import threading

_lock = threading.Lock()
_subscribers: list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = []


def subscribe() -> asyncio.Queue:
    """Call from async code (an SSE handler). Returns the queue events will arrive on."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    with _lock:
        _subscribers.append((asyncio.get_running_loop(), queue))
    return queue


def unsubscribe(queue: asyncio.Queue) -> None:
    with _lock:
        _subscribers[:] = [(loop, q) for loop, q in _subscribers if q is not queue]


def _put(queue: asyncio.Queue, event: dict) -> None:
    if not queue.full():  # a stalled tab just misses events; it refetches on reconnect
        queue.put_nowait(event)


def publish(event_type: str, data: dict | None = None) -> None:
    event = {"type": event_type, "data": data or {}}
    with _lock:
        targets = list(_subscribers)
    for loop, queue in targets:
        try:
            loop.call_soon_threadsafe(_put, queue, event)
        except RuntimeError:
            pass  # that loop has closed (server shutting down)
