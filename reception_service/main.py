"""
Reception Servisi — HotelOSning kirish-chiqish nuqtasi.

Mas'uliyatlari:
- Check-in: assign_room() algoritmini ishga tushiradi, mehmon yozuvini saqlaydi.
- Check-out: calculate_bill() ni ishlatadi, "xona bo'shatildi" hodisasini nashr etadi.
- Xona inventari so'rovlari.

Bu fayl protsedural va OOP paradigmalarini birlashtiradi (2-Vazifa uchun misol):
- `RoomInventory` klassi (OOP — inkapsulyatsiya: thread-safe state).
- `_process_checkin()` funksiyasi (protsedural — bosqichma-bosqich oqim).
- FastAPI ishlovchilari (hodisaga asoslangan — HTTP so'rovlari bo'yicha trigger).
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from reception_service.algorithms import (
    NoRoomAvailableError,
    assign_room,
    calculate_bill,
)
from shared.broker import MessageBroker, build_broker
from shared.config import get_settings
from shared.enums import ProximityPreference, RoomStatus, RoomType
from shared.events import (
    EVT_GUEST_CHECKED_IN,
    EVT_GUEST_CHECKED_OUT,
    EVT_ROOM_CLEANED,
    EVT_ROOM_OCCUPIED,
    EVT_ROOM_VACATED,
)
from shared.models import Booking, BookingPreference, Guest, Room, RoomServiceOrder
from shared.security import InputValidator, ValidationError, redact_sensitive

logger = logging.getLogger("hotelos.reception")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


# === Inkapsulyatsiyalangan inventar holati (OOP) ===

class RoomInventory:
    """Xonalar uchun thread-safe inventar.

    Ichki ma'lumotlar (`_rooms`) ataylab ostida chiziq bilan boshlanadi —
    bu shartli "private" konventsiyasi. Tashqi kod faqat aniq metodlar
    orqali ma'lumotlarga kirishi kerak (inkapsulyatsiya).
    """

    def __init__(self) -> None:
        self._rooms: dict[int, Room] = {}
        self._lock = threading.RLock()

    def load_from_json(self, path: Path) -> None:
        """Boshlang'ich xona inventarini diskdan yuklaydi."""
        raw = json.loads(path.read_text())
        with self._lock:
            for entry in raw:
                room = Room(**entry)
                self._rooms[room.number] = room
        logger.info("Inventar yuklandi: %d xona", len(self._rooms))

    def all_rooms(self) -> list[Room]:
        with self._lock:
            return list(self._rooms.values())

    def get(self, number: int) -> Room:
        with self._lock:
            try:
                return self._rooms[number]
            except KeyError as exc:
                raise KeyError(f"Xona #{number} mavjud emas") from exc

    def update_status(self, number: int, new_status: RoomStatus) -> Room:
        """Xona holatini xavfsiz tarzda yangilaydi."""
        with self._lock:
            room = self._rooms[number]
            room.mark_status_changed(new_status)
            return room


# === Servis bo'ylab state (kichik miqyos uchun; ishlab chiqarishda DB) ===

inventory = RoomInventory()
guests: dict[str, Guest] = {}
bookings: dict[str, Booking] = {}
orders_by_room: dict[int, list[RoomServiceOrder]] = {}
state_lock = threading.RLock()
broker: MessageBroker | None = None


# === FastAPI so'rov sxemalari (validation Pydantic orqali) ===

class CheckInRequest(BaseModel):
    """Check-in HTTP so'rovi yuki."""

    full_name: str
    document_id: str
    payment_card_last4: str = Field(..., pattern=r"^\d{4}$")
    requested_room_type: RoomType
    preferred_floor: int | None = Field(default=None, ge=1, le=6)
    proximity: ProximityPreference = ProximityPreference.NONE
    nights: int = Field(..., ge=1, le=365)


class CheckOutRequest(BaseModel):
    """Check-out HTTP so'rovi yuki."""

    booking_id: str
    minibar_charge: float = 0.0
    late_checkout: bool = False
    discount_percent: float = 0.0


# === Asosiy oqim funksiyalari (PROTSEDURAL paradigma misoli) ===
#
# Bu funksiya 2-Vazifada protsedural dasturlash misoli sifatida ishlatiladi.
# E'tibor bering: bu yerda OOPdagi kabi "obyekt" yo'q — bu oddiy bosqichli
# protsedura: tekshir → tayinla → saqla → nashr et.
#
async def _process_checkin(req: CheckInRequest) -> dict:
    """Check-in protsedurasi — bosqichma-bosqich qaror qabul qilish."""

    # 1-bosqich: kiritishni tekshirish
    name = InputValidator.validate_name(req.full_name)
    doc = InputValidator.validate_document_id(req.document_id)
    card = InputValidator.validate_card_last4(req.payment_card_last4)

    # 2-bosqich: xona tayinlash algoritmini ishga tushirish
    try:
        result = assign_room(
            inventory.all_rooms(),
            requested_type=req.requested_room_type,
            preferred_floor=req.preferred_floor,
            proximity=req.proximity,
        )
    except NoRoomAvailableError as exc:
        # Brief talabi: "tizim aniq 'xonalar mavjud emas' xabarini qaytaradi"
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    chosen_room = inventory.get(result.room_number)

    # 3-bosqich: yozuvlarni saqlash + xona holatini yangilash (atomar)
    with state_lock:
        guest = Guest(full_name=name, document_id=doc, payment_card_last4=card)
        guests[guest.guest_id] = guest

        booking = Booking(
            guest_id=guest.guest_id,
            room_number=chosen_room.number,
            requested_room_type=req.requested_room_type,
            preference=BookingPreference(
                preferred_floor=req.preferred_floor,
                proximity=req.proximity,
            ),
            check_in_at=datetime.now(timezone.utc),
            nights=req.nights,
            nightly_rate_locked=chosen_room.nightly_rate,
        )
        bookings[booking.booking_id] = booking
        inventory.update_status(chosen_room.number, RoomStatus.OCCUPIED)

    # 4-bosqich: hodisalarni nashr etish (boshqa servislar tinglashi mumkin)
    assert broker is not None
    await broker.publish(
        EVT_GUEST_CHECKED_IN,
        redact_sensitive({
            "guest_id": guest.guest_id,
            "full_name": guest.full_name,
            "room_number": chosen_room.number,
            "booking_id": booking.booking_id,
            "timestamp": booking.check_in_at.isoformat(),
        }),
    )
    await broker.publish(
        EVT_ROOM_OCCUPIED,
        {
            "room_number": chosen_room.number,
            "guest_id": guest.guest_id,
            "guest_name": guest.full_name,
            "timestamp": booking.check_in_at.isoformat(),
        },
    )

    return {
        "booking_id": booking.booking_id,
        "guest_id": guest.guest_id,
        "room_number": chosen_room.number,
        "reasoning": result.reasoning,
    }


# === Lifespan: brokerni boshqarish ===

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Servis hayoti — broker ulanishi va obunalarini boshqarish."""
    global broker
    settings = get_settings()
    broker = build_broker(
        use_in_memory=settings.use_in_memory_broker,
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
    )
    await broker.connect()

    # Tozalovchi xonani tozalab bo'lganini eshitamiz — inventarni yangilash uchun
    async def on_room_cleaned(topic: str, payload: dict) -> None:
        try:
            number = InputValidator.validate_room_number(payload.get("room_number"))
        except ValidationError:
            logger.warning("room.cleaned yuki noto'g'ri: %s", payload)
            return
        try:
            inventory.update_status(number, RoomStatus.CLEAN)
            logger.info("Inventar: xona %s -> Toza", number)
        except KeyError:
            logger.warning("Noma'lum xona: %s", number)

    await broker.subscribe(EVT_ROOM_CLEANED, on_room_cleaned)

    # Inventarni yuklash
    inventory.load_from_json(Path(__file__).resolve().parent.parent / "data" / "rooms.json")

    listener = asyncio.create_task(broker.start_listening())
    try:
        yield
    finally:
        listener.cancel()
        await broker.disconnect()


# === FastAPI ilovasi ===

app = FastAPI(
    title="HotelOS Reception Service",
    version="1.0.0",
    description="Check-in, check-out, xona inventari endpointlari",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# === HODISAGA ASOSLANGAN paradigma: HTTP hodisalari ishlovchilari ===

@app.get("/health")
async def health() -> dict[str, Any]:
    """Servis tirikligini tekshiruvchi endpoint."""
    return {"status": "ok", "service": "reception", "rooms_loaded": len(inventory.all_rooms())}


@app.get("/rooms")
async def list_rooms() -> list[dict]:
    """Xona inventari holati (panel uchun)."""
    return [
        {
            "number": r.number,
            "floor": r.floor,
            "room_type": r.room_type.value,
            "status": r.status.value,
            "near_lift": r.near_lift,
            "near_stairs": r.near_stairs,
        }
        for r in sorted(inventory.all_rooms(), key=lambda x: x.number)
    ]


@app.post("/checkin", status_code=status.HTTP_201_CREATED)
async def http_checkin(req: CheckInRequest) -> dict:
    """Yangi mehmon check-in — assign_room() algoritmini chaqiradi."""
    try:
        return await _process_checkin(req)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/checkout")
async def http_checkout(req: CheckOutRequest) -> dict:
    """Mehmon check-out — calculate_bill() ni ishga tushirib hodisani nashr etadi."""
    with state_lock:
        booking = bookings.get(req.booking_id)
        if booking is None:
            raise HTTPException(status_code=404, detail="Bron topilmadi")
        if booking.check_out_at is not None:
            raise HTTPException(status_code=409, detail="Allaqachon check-out qilingan")
        guest = guests[booking.guest_id]
        room_orders = orders_by_room.get(booking.room_number, [])

    bill = calculate_bill(
        booking=booking,
        room_service_orders=room_orders,
        minibar_charge=Decimal(str(req.minibar_charge)),
        late_checkout=req.late_checkout,
        discount_percent=Decimal(str(req.discount_percent)),
        actual_checkout=datetime.now(timezone.utc),
    )

    with state_lock:
        booking.check_out_at = datetime.now(timezone.utc)
        inventory.update_status(booking.room_number, RoomStatus.DIRTY)

    assert broker is not None
    await broker.publish(
        EVT_GUEST_CHECKED_OUT,
        {
            "guest_id": guest.guest_id,
            "booking_id": booking.booking_id,
            "bill": bill,
        },
    )
    await broker.publish(
        EVT_ROOM_VACATED,
        {
            "room_number": booking.room_number,
            "previous_guest": guest.public_view(),
            "timestamp": booking.check_out_at.isoformat(),
        },
    )
    return {"bill": bill, "room_status": "dirty"}


@app.post("/internal/order_charge")
async def add_order_charge(payload: dict) -> dict:
    """Xona xizmati servisi tomonidan chaqiriladi — to'lovni mehmon hisobiga qo'shish.

    Mikroservis chegarasini ishonchli o'tish uchun JWT yoki API kalit kerak bo'lardi —
    soddalashtirilgan versiyada ichki tarmoq deb hisoblaymiz va loyihalashtiramiz.
    """
    try:
        room_number = InputValidator.validate_room_number(payload.get("room_number"))
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    order = RoomServiceOrder(**payload["order"])
    with state_lock:
        orders_by_room.setdefault(room_number, []).append(order)
    return {"ok": True, "orders_count": len(orders_by_room[room_number])}


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "reception_service.main:app",
        host="0.0.0.0",  # noqa: S104 — lokal demo uchun
        port=settings.reception_port,
        reload=False,
    )
