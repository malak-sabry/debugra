from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis
from fastapi import WebSocket

from debugra_schemas import RunEventType
from orchestrator.config import get_settings

settings = get_settings()

# In-memory fallback for when Redis is not available
_in_memory_subscribers: dict[str, list[WebSocket]] = {}


def _make_channel(run_id: str) -> str:
    return f"debugra:run:{run_id}"


def _serialize(run_id: str, event_type: RunEventType, payload: dict[str, Any]) -> str:
    return json.dumps(
        {
            "run_id": run_id,
            "type": event_type,
            "payload": payload,
            "ts": datetime.now(timezone.utc).isoformat(),
        },
        default=str,
    )


async def publish_event(run_id: str, event_type: RunEventType, payload: dict[str, Any]) -> None:
    """Publish a run event to Redis pub/sub and in-memory subscribers."""
    message = _serialize(run_id, event_type, payload)

    # In-memory delivery (always)
    subscribers = _in_memory_subscribers.get(run_id, [])
    dead: list[WebSocket] = []
    for ws in subscribers:
        try:
            await ws.send_text(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        subscribers.remove(ws)

    # Redis delivery (best-effort)
    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.publish(_make_channel(run_id), message)
        await r.aclose()
    except Exception:
        pass


def subscribe_websocket(run_id: str, ws: WebSocket) -> None:
    if run_id not in _in_memory_subscribers:
        _in_memory_subscribers[run_id] = []
    _in_memory_subscribers[run_id].append(ws)


def unsubscribe_websocket(run_id: str, ws: WebSocket) -> None:
    subs = _in_memory_subscribers.get(run_id, [])
    if ws in subs:
        subs.remove(ws)
