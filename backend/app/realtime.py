from __future__ import annotations

import asyncio

from fastapi import WebSocket


class RealtimeHub:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self.lock:
            self.clients.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self.lock:
            self.clients.discard(websocket)

    async def publish(self, event: str) -> None:
        async with self.lock:
            clients = list(self.clients)
        stale: list[WebSocket] = []
        for client in clients:
            try:
                await client.send_json({"event": event})
            except Exception:
                stale.append(client)
        if stale:
            async with self.lock:
                for client in stale:
                    self.clients.discard(client)


hub = RealtimeHub()
