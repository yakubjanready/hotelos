"""
Housekeeping Servisi.

Hodisaga asoslangan: "room.vacated" hodisasiga obuna bo'ladi va xonani
tozalash navbatiga qo'shadi. Tozalovchi xodimlar HTTP endpoint orqali xona
holatini Tozalanmoqda -> Toza ga o'tkazadi.

FIFO navbati `collections.deque` orqali amalga oshirilgan — bu O(1)
qo'shish va olish operatsiyalarini ta'minlaydi.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from shared.broker import MessageBroker, build_broker
from shared.config import get_settings
from shared.enums import RoomStatus
from shared.events import EVT_ROOM_CLEANED, EVT_ROOM_CLEANING_STARTED, EVT_ROOM_VACATED
from shared.security import InputValidator, ValidationError

logger = logging.getLogger("hotelos.housekeeping")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


class CleaningQueue:
    """Inkapsulyatsiyalangan tozalash navbati — FIFO tartibida.

    `deque` mutex bilan o'ralgan, chunki bir vaqtning o'zida bir nechta
    tozalovchi xona olishi mumkin (race condition oldini olish).
    """

    def __init__(self) -> None:
        self._queue: deque[int] = deque()
        self._in_progress: set[int] = set()
        self._lock = threading.RLock()

    def enqueue(self, room_number: int) -> None:
        with self._lock:
            if room_number in self._queue or room_number in self._in_progress:
                logger.info("Xona %s allaqachon navbatda", room_number)
                return
            self._queue.append(room_number)
            logger.info("Tozalash navbatiga qo'shildi: xona %s (navbat: %d)",
                        room_number, len(self._queue))

    def claim_next(self) -> int | None:
        """Navbatdagi keyingi xonani oladi va in_progress to'plamiga qo'shadi."""
        with self._lock:
            if not self._queue:
                return None
            room = self._queue.popleft()
            self._in_progress.add(room)
            return room

    def mark_done(self, room_number: int) -> bool:
        with self._lock:
            if room_number in self._in_progress:
                self._in_progress.discard(room_number)
                return True
            return False

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "queued": list(self._queue),
                "in_progress": sorted(self._in_progress),
            }


queue = CleaningQueue()
broker: MessageBroker | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global broker
    settings = get_settings()
    broker = build_broker(
        use_in_memory=settings.use_in_memory_broker,
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
    )
    await broker.connect()

    # "room.vacated" hodisasiga obuna — xonalar avtomatik ravishda navbatga tushadi
    async def on_room_vacated(topic: str, payload: dict) -> None:
        try:
            number = InputValidator.validate_room_number(payload.get("room_number"))
        except ValidationError:
            logger.warning("room.vacated yuki noto'g'ri: %s", payload)
            return
        queue.enqueue(number)
        logger.info("Hodisa qabul qilindi: %s -> xona %s navbatga", topic, number)

    await broker.subscribe(EVT_ROOM_VACATED, on_room_vacated)
    listener = asyncio.create_task(broker.start_listening())
    try:
        yield
    finally:
        listener.cancel()
        await broker.disconnect()


app = FastAPI(title="HotelOS Housekeeping Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "housekeeping", "queue": queue.snapshot()}


@app.get("/queue")
async def get_queue() -> dict:
    return queue.snapshot()


@app.post("/claim")
async def claim_next() -> dict:
    """Tozalovchi keyingi xonani oladi (Iflos -> Tozalanmoqda)."""
    room_number = queue.claim_next()
    if room_number is None:
        raise HTTPException(status_code=404, detail="Tozalash navbatida xona yo'q")

    assert broker is not None
    await broker.publish(
        EVT_ROOM_CLEANING_STARTED,
        {
            "room_number": room_number,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "new_status": RoomStatus.CLEANING.value,
        },
    )
    return {"room_number": room_number, "status": "cleaning"}


@app.post("/mark_clean/{room_number}")
async def mark_clean(room_number: int) -> dict:
    """Tozalovchi xonani toza deb belgilaydi (Tozalanmoqda -> Toza)."""
    try:
        room_number = InputValidator.validate_room_number(room_number)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not queue.mark_done(room_number):
        raise HTTPException(status_code=409, detail="Xona tozalash jarayonida emas")

    assert broker is not None
    await broker.publish(
        EVT_ROOM_CLEANED,
        {
            "room_number": room_number,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "new_status": RoomStatus.CLEAN.value,
        },
    )
    return {"room_number": room_number, "status": "clean"}


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "housekeeping_service.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.housekeeping_port,
        reload=False,
    )
