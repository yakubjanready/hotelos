"""
HotelOS markaziy konfiguratsiya moduli.

Barcha sozlamalar muhit o'zgaruvchilaridan o'qiladi va majburiy turlar bilan
ta'minlanadi. Bu yondashuv 12-Factor App tamoyiliga muvofiq: konfiguratsiya
koddan ajratilgan (Wiggins, 2017).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


# Sehrli raqamlar emas — nomlangan konstantalar. Kodlash standartiga muvofiq.
DEFAULT_REDIS_HOST = "localhost"
DEFAULT_REDIS_PORT = 6379
DEFAULT_JWT_EXPIRY_MINUTES = 60
DEFAULT_HOTEL_FLOORS = 6
DEFAULT_ROOMS_PER_FLOOR = 20


def _get_env_int(key: str, default: int) -> int:
    """Muhit o'zgaruvchisini xavfsiz tarzda butun songa o'tkazadi."""
    raw = os.getenv(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """O'zgarmas (immutable) sozlamalar konteyneri.

    `frozen=True` orqali konfiguratsiya dastur ishlashi davomida tasodifan
    o'zgarishidan himoyalangan — inkapsulyatsiya tamoyili.
    """

    # Redis broker
    redis_host: str = DEFAULT_REDIS_HOST
    redis_port: int = DEFAULT_REDIS_PORT
    redis_db: int = 0

    # Servis portlari
    reception_port: int = 8001
    housekeeping_port: int = 8002
    roomservice_port: int = 8003
    maintenance_port: int = 8004
    dashboard_port: int = 8000

    # Xavfsizlik
    jwt_secret: str = "change-me-in-production"  # noqa: S105
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = DEFAULT_JWT_EXPIRY_MINUTES
    dashboard_user: str = "admin"
    dashboard_password: str = "admin123"  # noqa: S105

    # Mehmonxona miqyosi
    hotel_floors: int = DEFAULT_HOTEL_FLOORS
    rooms_per_floor: int = DEFAULT_ROOMS_PER_FLOOR

    # Ma'lumotlar bazasi
    database_url: str = "sqlite:///./hotelos.db"

    # Brokerni rejimini almashtirish — test rejimida xotirada ishlaydi
    use_in_memory_broker: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Sozlamalarni bir marta yuklab, keshlangan namunani qaytaradi."""
    return Settings(
        redis_host=os.getenv("REDIS_HOST", DEFAULT_REDIS_HOST),
        redis_port=_get_env_int("REDIS_PORT", DEFAULT_REDIS_PORT),
        redis_db=_get_env_int("REDIS_DB", 0),
        reception_port=_get_env_int("RECEPTION_PORT", 8001),
        housekeeping_port=_get_env_int("HOUSEKEEPING_PORT", 8002),
        roomservice_port=_get_env_int("ROOMSERVICE_PORT", 8003),
        maintenance_port=_get_env_int("MAINTENANCE_PORT", 8004),
        dashboard_port=_get_env_int("DASHBOARD_PORT", 8000),
        jwt_secret=os.getenv("JWT_SECRET", "change-me-in-production"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_expiry_minutes=_get_env_int("JWT_EXPIRY_MINUTES", DEFAULT_JWT_EXPIRY_MINUTES),
        dashboard_user=os.getenv("DASHBOARD_USER", "admin"),
        dashboard_password=os.getenv("DASHBOARD_PASSWORD", "admin123"),
        hotel_floors=_get_env_int("HOTEL_FLOORS", DEFAULT_HOTEL_FLOORS),
        rooms_per_floor=_get_env_int("ROOMS_PER_FLOOR", DEFAULT_ROOMS_PER_FLOOR),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./hotelos.db"),
        use_in_memory_broker=os.getenv("USE_IN_MEMORY_BROKER", "false").lower() == "true",
    )
