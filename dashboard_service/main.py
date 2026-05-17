"""
Dashboard Servisi — HotelOS operatsion paneli.

Mas'uliyatlar:
- Brokerdagi barcha hodisalarga obuna bo'lish va ichki holatni yangilash.
- WebSocket orqali ulangan brauzerlarga jonli yangilanish uzatish.
- Login (JWT) bilan himoyalangan asosiy panel sahifasini xizmat qilish.

Bu servis hodisaga asoslangan paradigmaning aniq misoli — uning butun mantig'i
broker hodisalari va WebSocket ulanishlari atrofida quriladi.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from shared.broker import MessageBroker, build_broker
from shared.config import get_settings
from shared.events import (
    ALL_EVENTS,
    EVT_DASHBOARD_STATE,
    EVT_ISSUE_ASSIGNED,
    EVT_ISSUE_REPORTED,
    EVT_ISSUE_RESOLVED,
    EVT_ORDER_DELIVERED,
    EVT_ORDER_DELIVERING,
    EVT_ORDER_PREPARING,
    EVT_ORDER_RECEIVED,
    EVT_ROOM_CLEANED,
    EVT_ROOM_CLEANING_STARTED,
    EVT_ROOM_OCCUPIED,
    EVT_ROOM_VACATED,
)
from shared.security import (
    AuthenticationError,
    SimpleJWT,
    hash_password,
    redact_sensitive,
    verify_password,
)

logger = logging.getLogger("hotelos.dashboard")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


# === Yig'ma holat ===

class DashboardState:
    """Barcha servislardan yig'ilgan ko'rinish.

    Thread-safe — ham broker handlers, ham WebSocket har xil event loopdan kirishi mumkin.
    """

    def __init__(self) -> None:
        self._rooms: dict[int, dict] = {}
        self._orders: dict[str, dict] = {}
        self._issues: dict[str, dict] = {}
        self._guests_by_room: dict[int, dict] = {}
        self._lock = threading.RLock()

    def update_room(self, room_number: int, **fields) -> None:
        with self._lock:
            existing = self._rooms.setdefault(room_number, {"number": room_number})
            existing.update(fields)
            existing["updated_at"] = datetime.now(timezone.utc).isoformat()

    def set_guest(self, room_number: int, guest: dict | None) -> None:
        with self._lock:
            if guest is None:
                self._guests_by_room.pop(room_number, None)
            else:
                self._guests_by_room[room_number] = guest

    def update_order(self, order_id: str, **fields) -> None:
        with self._lock:
            self._orders.setdefault(order_id, {"order_id": order_id}).update(fields)

    def remove_order(self, order_id: str) -> None:
        with self._lock:
            self._orders.pop(order_id, None)

    def update_issue(self, issue_id: str, **fields) -> None:
        with self._lock:
            self._issues.setdefault(issue_id, {"issue_id": issue_id}).update(fields)

    def remove_issue(self, issue_id: str) -> None:
        with self._lock:
            self._issues.pop(issue_id, None)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "rooms": sorted(self._rooms.values(), key=lambda r: r["number"]),
                "orders": [o for o in self._orders.values() if o.get("status") != "delivered"],
                "issues": sorted(
                    self._issues.values(),
                    key=lambda i: (
                        {"critical": 0, "high": 1, "normal": 2, "low": 3}.get(i.get("urgency"), 9),
                        i.get("reported_at", ""),
                    ),
                ),
                "guests_by_room": self._guests_by_room.copy(),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }


# === WebSocket ulanishlar registri ===

class ConnectionManager:
    """Faol WebSocket mijozlarini boshqaradi va xabar uzatadi."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)
        logger.info("WebSocket ulandi (jami: %d)", len(self._connections))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            if ws in self._connections:
                self._connections.remove(ws)
        logger.info("WebSocket uzildi (jami: %d)", len(self._connections))

    async def broadcast(self, payload: dict) -> None:
        async with self._lock:
            targets = list(self._connections)
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(redact_sensitive(payload))
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)


state = DashboardState()
manager = ConnectionManager()
broker: MessageBroker | None = None
jwt_handler: SimpleJWT | None = None


# === Hodisa handler'lari — har bir kanal alohida tartibga solinadi ===

async def on_room_occupied(topic: str, payload: dict) -> None:
    room = int(payload["room_number"])
    state.update_room(room, status="occupied")
    state.set_guest(room, {"guest_id": payload["guest_id"], "name": payload["guest_name"]})
    await manager.broadcast({"type": "room.occupied", "payload": payload})


async def on_room_vacated(topic: str, payload: dict) -> None:
    room = int(payload["room_number"])
    state.update_room(room, status="dirty")
    state.set_guest(room, None)
    await manager.broadcast({"type": "room.vacated", "payload": payload})


async def on_room_cleaning_started(topic: str, payload: dict) -> None:
    room = int(payload["room_number"])
    state.update_room(room, status="cleaning")
    await manager.broadcast({"type": "room.cleaning_started", "payload": payload})


async def on_room_cleaned(topic: str, payload: dict) -> None:
    room = int(payload["room_number"])
    state.update_room(room, status="clean")
    await manager.broadcast({"type": "room.cleaned", "payload": payload})


async def on_order(topic: str, payload: dict) -> None:
    state.update_order(
        payload["order_id"],
        room_number=payload["room_number"],
        status=payload["status"],
        total=payload.get("total"),
        timestamp=payload["timestamp"],
    )
    if payload["status"] == "delivered":
        state.remove_order(payload["order_id"])
    await manager.broadcast({"type": topic, "payload": payload})


async def on_issue(topic: str, payload: dict) -> None:
    issue_id = payload["issue_id"]
    if topic == EVT_ISSUE_RESOLVED:
        state.remove_issue(issue_id)
    else:
        state.update_issue(
            issue_id,
            room_number=payload["room_number"],
            urgency=payload.get("urgency"),
            description=payload.get("description"),
            status="assigned" if topic == EVT_ISSUE_ASSIGNED else "reported",
            technician=payload.get("technician"),
            reported_at=payload.get("timestamp"),
        )
    await manager.broadcast({"type": topic, "payload": payload})


@asynccontextmanager
async def lifespan(app: FastAPI):
    global broker, jwt_handler
    settings = get_settings()
    jwt_handler = SimpleJWT(secret=settings.jwt_secret, expiry_minutes=settings.jwt_expiry_minutes)
    broker = build_broker(
        use_in_memory=settings.use_in_memory_broker,
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
    )
    await broker.connect()

    # Boshlang'ich xona inventarini Reception servisidan tortib olamiz
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"http://localhost:{settings.reception_port}/rooms")
            for room in resp.json():
                state.update_room(room["number"], **room)
    except httpx.HTTPError:
        logger.warning("Reception servisidan inventar tortilmadi — bo'sh holatda davom etadi")

    # Barcha hodisalarga obuna bo'lish
    await broker.subscribe(EVT_ROOM_OCCUPIED, on_room_occupied)
    await broker.subscribe(EVT_ROOM_VACATED, on_room_vacated)
    await broker.subscribe(EVT_ROOM_CLEANING_STARTED, on_room_cleaning_started)
    await broker.subscribe(EVT_ROOM_CLEANED, on_room_cleaned)
    for topic in (EVT_ORDER_RECEIVED, EVT_ORDER_PREPARING, EVT_ORDER_DELIVERING, EVT_ORDER_DELIVERED):
        await broker.subscribe(topic, on_order)
    for topic in (EVT_ISSUE_REPORTED, EVT_ISSUE_ASSIGNED, EVT_ISSUE_RESOLVED):
        await broker.subscribe(topic, on_issue)

    listener = asyncio.create_task(broker.start_listening())
    try:
        yield
    finally:
        listener.cancel()
        await broker.disconnect()


app = FastAPI(title="HotelOS Dashboard", version="1.0.0", lifespan=lifespan)
static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

bearer_scheme = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str
    password: str


@app.get("/")
async def index() -> FileResponse:
    """Login va panel HTML faylini xizmat qiladi."""
    return FileResponse(static_dir / "index.html")


@app.post("/login")
async def login(req: LoginRequest) -> dict:
    """Foydalanuvchi ma'lumotlarini tekshirib JWT qaytaradi."""
    settings = get_settings()
    # Ishlab chiqarishda DB lookup; bu yerda env dan oddiy taqqoslash
    if req.username != settings.dashboard_user:
        raise HTTPException(status_code=401, detail="Foydalanuvchi yo'q")
    expected_hash = hash_password(settings.dashboard_password)
    if not verify_password(req.password, expected_hash):
        raise HTTPException(status_code=401, detail="Parol noto'g'ri")
    assert jwt_handler is not None
    return {"token": jwt_handler.encode(req.username)}


def _verify_token(token: str) -> str:
    """Tokenni dekodlaydi yoki HTTP 401 ko'taradi."""
    assert jwt_handler is not None
    try:
        return jwt_handler.decode(token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/state")
async def get_state(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> JSONResponse:
    """Joriy yig'ma holat (panel boshlang'ich yuk uchun)."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Token kerak")
    _verify_token(credentials.credentials)
    return JSONResponse(redact_sensitive(state.snapshot()))


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str | None = None) -> None:
    """WebSocket endpoint — token query parametri orqali auth."""
    if token is None:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        _verify_token(token)
    except HTTPException:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(ws)
    # Boshlang'ich holat — yangi ulanish darhol to'liq ko'rinishni oladi
    await ws.send_json({"type": "initial_state", "payload": state.snapshot()})
    try:
        while True:
            # Mijoz xabarlarini eshitamiz (keep-alive, ping). Hech narsa qilmaymiz.
            await ws.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(ws)
    except Exception:  # noqa: BLE001
        logger.exception("WebSocket xatosi")
        await manager.disconnect(ws)


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "dashboard_service.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.dashboard_port,
        reload=False,
    )
