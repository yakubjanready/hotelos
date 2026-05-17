"""
HotelOS xabar brokeri abstraksiyasi.

Bu modul OOP tamoyili "Abstraksiya"ni amalda namoyish etadi: yuqori darajadagi
kod brokerning ichki ishlash mexanizmini bilmaydi. Mijoz oddiygina .publish() va
.subscribe() chaqiradi va kerakli ish bajariladi — Redis bo'ladimi yoki ichki
in-memory implementatsiya bo'ladimi.

Ikki amalga oshirish:
- RedisBroker: ishlab chiqarish (production) uchun Redis Pub/Sub.
- InMemoryBroker: testlar va offline rivojlantirish uchun.
"""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, Awaitable, Callable

logger = logging.getLogger("hotelos.broker")

# Hodisa qabul qiluvchi funksiya turi.
EventHandler = Callable[[str, dict], Awaitable[None]]


class MessageBroker(ABC):
    """Abstrakt broker interfeysi.

    Barcha aniq amalga oshirishlar shu interfeysni qondiradi —
    polimorfizm: bir xil chaqiriqlar boshqacha xatti-harakat hosil qiladi.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Brokerga ulanish ochadi."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Brokerni xavfsiz tarzda yopadi."""

    @abstractmethod
    async def publish(self, topic: str, payload: dict) -> None:
        """Hodisani belgilangan mavzuga nashr etadi.

        Yuk JSON serializatsiya qilinishi kerak. Pasport va to'lov ma'lumotlari
        kabi maxfiy maydonlar yo'q ekanligini chaqiruvchi ta'minlashi kerak.
        """

    @abstractmethod
    async def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Mavzuga obuna bo'lib, hodisa kelganda ishlatuvchini chaqiradi."""

    @abstractmethod
    async def start_listening(self) -> None:
        """Obunalarga tinglashni boshlaydi (uzoq ishlaydigan vazifa)."""


class InMemoryBroker(MessageBroker):
    """Test va lokal ishlash uchun jarayon ichidagi broker.

    asyncio.Queue ishlatadi — bir obunachi bir vaqtning o'zida bir xabar oladi.
    Bu Redis Pub/Sub semantikasini soddalashtiradi (har bir obunachi har bir
    xabarni oladi).
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._queue: asyncio.Queue[tuple[str, dict]] = asyncio.Queue()
        self._running = False
        self._task: asyncio.Task | None = None

    async def connect(self) -> None:
        logger.info("InMemoryBroker ulandi (jarayon ichi)")

    async def disconnect(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
        logger.info("InMemoryBroker uzildi")

    async def publish(self, topic: str, payload: dict) -> None:
        await self._queue.put((topic, payload))
        logger.debug("Nashr etildi: %s -> %s", topic, payload)

    async def subscribe(self, topic: str, handler: EventHandler) -> None:
        self._handlers[topic].append(handler)
        logger.info("Obuna bo'lindi: %s (jami obunachilar: %d)", topic, len(self._handlers[topic]))

    async def start_listening(self) -> None:
        self._running = True
        while self._running:
            try:
                topic, payload = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            for handler in self._handlers.get(topic, []):
                try:
                    await handler(topic, payload)
                except Exception as exc:  # noqa: BLE001 — har bir handler alohida tutiladi
                    logger.exception("Handler xatosi (%s): %s", topic, exc)


class RedisBroker(MessageBroker):
    """Ishlab chiqarish brokeri — Redis Pub/Sub asosida.

    `redis.asyncio` mijozidan foydalanadi. Agar redis paketi mavjud bo'lmasa,
    import xatosi `connect()` paytida aniqlanadi.
    """

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0) -> None:
        self._host = host
        self._port = port
        self._db = db
        self._client: Any = None
        self._pubsub: Any = None
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._running = False

    async def connect(self) -> None:
        try:
            import redis.asyncio as aioredis
        except ImportError as exc:
            raise RuntimeError(
                "redis paketi o'rnatilmagan. `pip install redis` yoki "
                "USE_IN_MEMORY_BROKER=true ni o'rnating."
            ) from exc

        self._client = aioredis.Redis(host=self._host, port=self._port, db=self._db)
        await self._client.ping()
        self._pubsub = self._client.pubsub()
        logger.info("RedisBroker ulandi: %s:%s/%s", self._host, self._port, self._db)

    async def disconnect(self) -> None:
        self._running = False
        if self._pubsub is not None:
            await self._pubsub.close()
        if self._client is not None:
            await self._client.close()
        logger.info("RedisBroker uzildi")

    async def publish(self, topic: str, payload: dict) -> None:
        if self._client is None:
            raise RuntimeError("Broker ulanmagan — connect() chaqiring")
        message = json.dumps(payload, default=str)
        await self._client.publish(topic, message)
        logger.debug("Redis nashr etildi: %s", topic)

    async def subscribe(self, topic: str, handler: EventHandler) -> None:
        if self._pubsub is None:
            raise RuntimeError("Broker ulanmagan — connect() chaqiring")
        self._handlers[topic].append(handler)
        await self._pubsub.subscribe(topic)
        logger.info("Redis obuna: %s", topic)

    async def start_listening(self) -> None:
        if self._pubsub is None:
            raise RuntimeError("Broker ulanmagan — connect() chaqiring")
        self._running = True
        async for message in self._pubsub.listen():
            if not self._running:
                break
            if message["type"] != "message":
                continue
            topic = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
            raw = message["data"]
            if isinstance(raw, bytes):
                raw = raw.decode()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                logger.exception("Yuk parse xatosi: %s", raw)
                continue
            for handler in self._handlers.get(topic, []):
                try:
                    await handler(topic, payload)
                except Exception:  # noqa: BLE001
                    logger.exception("Handler xatosi: %s", topic)


def build_broker(use_in_memory: bool, host: str, port: int, db: int) -> MessageBroker:
    """Konfiguratsiyaga qarab to'g'ri broker amalga oshirishini qaytaradi.

    Bu Factory pattern — chaqiruvchi qaysi konkret klass yaratilayotganini
    bilmasdan abstrakt turni oladi.
    """
    if use_in_memory:
        return InMemoryBroker()
    return RedisBroker(host=host, port=port, db=db)
