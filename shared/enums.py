"""
HotelOS uchun nomlangan ro'yxatlar (enumerations).

Enum'lar 'magic strings'larni almashtiradi va xato qilish ehtimolini kamaytiradi:
agar tipografik xato qilinsa, IDE ham, runtime ham darhol bayroq qo'yadi.
"""

from __future__ import annotations

from enum import Enum


class RoomType(str, Enum):
    """Xona turlari — mehmonning bron qilgan kategoriyasiga mos kelishi kerak."""

    SINGLE = "single"
    DOUBLE = "double"
    SUITE = "suite"
    ACCESSIBLE = "accessible"


class RoomStatus(str, Enum):
    """Xonaning hozirgi operatsion holati.

    Holat mashinasi: CLEAN -> OCCUPIED -> DIRTY -> CLEANING -> CLEAN
    yoki istalgan vaqtda MAINTENANCE ga o'tishi mumkin.
    """

    CLEAN = "clean"
    OCCUPIED = "occupied"
    DIRTY = "dirty"
    CLEANING = "cleaning"
    MAINTENANCE = "maintenance"


class ProximityPreference(str, Enum):
    """Mehmonning lift/zinapoyaga yaqinlik afzalligi."""

    LIFT = "lift"
    STAIRS = "stairs"
    NONE = "none"


class OrderStatus(str, Enum):
    """Xona xizmati buyurtmasi hayot tsikli.

    Holat o'tishlari: RECEIVED -> PREPARING -> DELIVERING -> DELIVERED
    """

    RECEIVED = "received"
    PREPARING = "preparing"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class IssueUrgency(str, Enum):
    """Texnik xizmat so'rovi shoshilinchlik darajasi.

    Tartib: CRITICAL > HIGH > NORMAL > LOW
    Ustuvorlik navbatida raqamli qiymat ishlatiladi (priority_value()).
    """

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"

    def priority_value(self) -> int:
        """Raqamli ustuvorlik qiymati. Past raqam = yuqori ustuvorlik (min-heap uchun)."""
        mapping = {
            IssueUrgency.CRITICAL: 0,
            IssueUrgency.HIGH: 1,
            IssueUrgency.NORMAL: 2,
            IssueUrgency.LOW: 3,
        }
        return mapping[self]


class IssueStatus(str, Enum):
    """Texnik xizmat so'rovi holati."""

    REPORTED = "reported"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


class StaffRole(str, Enum):
    """Xodim rollari — OOP meros olishida kalit klasslar bilan mos keladi."""

    RECEPTIONIST = "receptionist"
    HOUSEKEEPER = "housekeeper"
    TECHNICIAN = "technician"
    MANAGER = "manager"
