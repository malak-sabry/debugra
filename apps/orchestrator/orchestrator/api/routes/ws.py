from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from orchestrator.event_bus import subscribe_websocket, unsubscribe_websocket

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/runs/{run_id}")
async def run_websocket(run_id: str, ws: WebSocket):
    """WebSocket endpoint — streams RunEvent JSON for a given run."""
    await ws.accept()
    subscribe_websocket(run_id, ws)

    try:
        # Keep connection alive; server pushes events via event_bus
        while True:
            # Handle pings or client messages (ignore content)
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        pass
    finally:
        unsubscribe_websocket(run_id, ws)
