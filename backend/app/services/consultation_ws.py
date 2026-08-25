from __future__ import annotations

import logging
from collections import defaultdict
from typing import DefaultDict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConsultationConnectionManager:
    def __init__(self) -> None:
        self._connections: DefaultDict[int, Set[WebSocket]] = defaultdict(set)

    async def connect(
        self, ticket_id: int, websocket: WebSocket, subprotocol: str | None = None
    ) -> None:
        await websocket.accept(subprotocol=subprotocol)
        self._connections[ticket_id].add(websocket)

    def disconnect(self, ticket_id: int, websocket: WebSocket) -> None:
        connections = self._connections.get(ticket_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(ticket_id, None)

    async def broadcast(self, ticket_id: int, payload: dict) -> None:
        # A dead/stale socket raising must not stop delivery to the other
        # participants, and must not propagate into the caller — callers like
        # prescription creation call this *after* their own DB commit already
        # succeeded, so a send failure here is not a request failure.
        connections = list(self._connections.get(ticket_id, set()))
        for websocket in connections:
            try:
                await websocket.send_json(payload)
            except Exception:
                logger.warning(
                    "Failed to broadcast to a consultation websocket; dropping it",
                    exc_info=True,
                )
                self.disconnect(ticket_id, websocket)
                # The connection's own receive loop (consultation_websocket in
                # routes/consultations.py) is still awaiting receive_json() on
                # this same socket — without closing it here too, that loop
                # never learns it was dropped, so it keeps accepting incoming
                # messages but silently never receives another broadcast until
                # the client itself notices and reconnects.
                try:
                    await websocket.close(code=1011)
                except Exception:
                    pass


manager = ConsultationConnectionManager()
