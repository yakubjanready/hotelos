"""
Room Service Servisi.

Xona xizmati buyurtmalarini boshqaradi. Holat oqimi:
    RECEIVED -> PREPARING -> DELIVERING -> DELIVERED

Har bir holat o'zgarishi brokerga nashr etiladi. Buyurtmalar yetkazib
berilganidan keyin to'lov Reception servisiga HTTP orqali yuboriladi
(servislararo aloqa — broker emas, chunki bu sinxron natija talab qiladi).
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.broker import MessageBroker, build_broker
from shared.config import get_settings
from shared.enums import OrderStatus
from shared.events import (
    EVT_ORDER_DELIVERED,
    EVT_ORDER_DELIVERING,
    EVT_ORDER_PREPARING,
    EVT_ORDER_RECEIVED,
)
from shared.models import RoomServiceOrder
from shared.security import InputValidator, ValidationError

logger = logging.getLogger("hotelos.roomservice")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


# Holat o'tish jadvali — qaror mantig'i sinflarga emas, tafsilotlarga ajratilgan.
STATE_TRANSITIONS: dict[OrderStatus, OrderStatus | None] = {
    OrderStatus.RECEIVED: OrderStatus.PREPARING,
    OrderStatus.PREPARING: OrderStatus.DELIVERING,
    OrderStatus.DELIVERING: OrderStatus.DELIVERED,
    OrderStatus.DELIVERED: None,
}

STATUS_TO_EVENT: dict[OrderStatus, str] = {
    OrderStatus.RECEIVED: EVT_ORDER_RECEIVED,
    OrderStatus.PREPARING: EVT_ORDER_PREPARING,
    OrderStatus.DELIVERING: EVT_ORDER_DELIVERING,
    OrderStatus.DELIVERED: EVT_ORDER_DELIVERED,
}


class OrderRegistry:
    """Buyurtmalar uchun thread-safe register.

    Deque + dict birlashmasi: deque FIFO ishlov uchun (oshxona keyingisini olishi),
    dict O(1) buyurtmaga kirish uchun (holat yangilash).
    """

    def __init__(self) -> None:
        self._orders: dict[str, RoomServiceOrder] = {}
        self._queue: deque[str] = deque()
        self._lock = threading.RLock()

    def add(self, order: RoomServiceOrder) -> None:
        with self._lock:
            self._orders[order.order_id] = order
            self._queue.append(order.order_id)

    def get(self, order_id: str) -> RoomServiceOrder:
        with self._lock:
            try:
                return self._orders[order_id]
            except KeyError as exc:
                raise KeyError(f"Buyurtma topilmadi: {order_id}") from exc

    def advance(self, order_id: str) -> RoomServiceOrder:
        """Buyurtmani keyingi holatga o'tkazadi."""
        with self._lock:
            order = self._orders[order_id]
            next_state = STATE_TRANSITIONS[order.status]
            if next_state is None:
                raise ValueError(f"Buyurtma allaqachon yakuniy holatda: {order.status.value}")
            order.status = next_state
            order.status_changed_at = datetime.now(timezone.utc)
            return order

    def snapshot(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "order_id": o.order_id,
                    "room_number": o.room_number,
                    "status": o.status.value,
                    "total": str(o.total),
                    "placed_at": o.placed_at.isoformat(),
                }
                for o in self._orders.values()
                if o.status != OrderStatus.DELIVERED
            ]


registry = OrderRegistry()
broker: MessageBroker | None = None
menu_cache: dict = {}


class OrderItemRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    qty: int = Field(..., ge=1, le=20)


class CreateOrderRequest(BaseModel):
    room_number: int = Field(..., ge=100, le=699)
    items: list[OrderItemRequest] = Field(..., min_length=1, max_length=20)


def _price_lookup(name: str) -> Decimal | None:
    """Menyu narxini topadi (kategoriyalarni o'tib)."""
    for category in menu_cache.get("categories", {}).values():
        for item in category:
            if item["name"].lower() == name.lower():
                return Decimal(str(item["price"]))
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global broker, menu_cache
    settings = get_settings()
    menu_path = Path(__file__).resolve().parent.parent / "data" / "menu.json"
    menu_cache = json.loads(menu_path.read_text())

    broker = build_broker(
        use_in_memory=settings.use_in_memory_broker,
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
    )
    await broker.connect()
    listener = asyncio.create_task(broker.start_listening())
    try:
        yield
    finally:
        listener.cancel()
        await broker.disconnect()


app = FastAPI(title="HotelOS Room Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "roomservice", "active_orders": len(registry.snapshot())}


@app.get("/menu")
async def get_menu() -> dict:
    return menu_cache


@app.get("/orders")
async def list_orders() -> list[dict]:
    return registry.snapshot()


@app.post("/orders", status_code=201)
async def create_order(req: CreateOrderRequest) -> dict:
    """Yangi buyurtma — narxlar menyu lookup orqali, total kalkulatsiya."""
    try:
        room_number = InputValidator.validate_room_number(req.room_number)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    enriched_items: list[dict] = []
    total = Decimal("0")
    for item in req.items:
        price = _price_lookup(item.name)
        if price is None:
            raise HTTPException(status_code=400, detail=f"Menyu elementi yo'q: {item.name}")
        enriched_items.append({"name": item.name, "qty": item.qty, "price": float(price)})
        total += price * item.qty

    order = RoomServiceOrder(
        room_number=room_number,
        items=enriched_items,
        total=total,
    )
    registry.add(order)

    assert broker is not None
    await broker.publish(
        EVT_ORDER_RECEIVED,
        {
            "order_id": order.order_id,
            "room_number": order.room_number,
            "total": str(order.total),
            "status": order.status.value,
            "timestamp": order.placed_at.isoformat(),
        },
    )
    return {"order_id": order.order_id, "total": str(total), "status": order.status.value}


@app.post("/orders/{order_id}/advance")
async def advance_order(order_id: str) -> dict:
    """Buyurtmani keyingi holatga o'tkazadi (RECEIVED -> PREPARING -> ...)."""
    try:
        order = registry.advance(order_id)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    assert broker is not None
    event_name = STATUS_TO_EVENT[order.status]
    await broker.publish(
        event_name,
        {
            "order_id": order.order_id,
            "room_number": order.room_number,
            "status": order.status.value,
            "timestamp": order.status_changed_at.isoformat(),
        },
    )

    # Buyurtma yetkazib berilganda — to'lovni Reception ga qo'shamiz
    if order.status == OrderStatus.DELIVERED:
        await _post_charge_to_reception(order)

    return {"order_id": order.order_id, "status": order.status.value}


async def _post_charge_to_reception(order: RoomServiceOrder) -> None:
    """Yetkazib berilgan buyurtma to'lovini Reception ga yuborish (servislararo HTTP)."""
    settings = get_settings()
    url = f"http://localhost:{settings.reception_port}/internal/order_charge"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                url,
                json={
                    "room_number": order.room_number,
                    "order": json.loads(order.model_dump_json()),
                },
            )
        logger.info("To'lov Reception ga yuborildi: %s", order.order_id)
    except httpx.HTTPError as exc:
        logger.exception("To'lov POST muvaffaqiyatsiz: %s", exc)


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "roomservice_service.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.roomservice_port,
        reload=False,
    )
