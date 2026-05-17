"""
HotelOS ma'lumotlar modellari.

Pydantic v2 ishlatiladi: bu turlarni avtomatik tekshirib, validatsiya xatolarni
aniqlaydi va JSON serializatsiyani ta'minlaydi. OOP nuqtai nazaridan har bir
model bir 'klass' bo'lib, inkapsulyatsiya va validatsiya xatti-harakatini
o'z ichiga oladi.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from shared.enums import (
    IssueStatus,
    IssueUrgency,
    OrderStatus,
    ProximityPreference,
    RoomStatus,
    RoomType,
    StaffRole,
)


def _now() -> datetime:
    """Hozirgi UTC vaqtini qaytaradi — barcha vaqt belgilarining yagona manbai."""
    return datetime.now(timezone.utc)


def _new_id(prefix: str) -> str:
    """Prefiks bilan noyob ID hosil qiladi (masalan: 'GST-3f4a...')."""
    return f"{prefix}-{uuid4().hex[:8]}"


class Room(BaseModel):
    """Mehmonxona xonasi.

    Inkapsulyatsiya: status_changed_at maydoni faqat
    mark_status_changed() metodi orqali yangilanishi kerak — bu eng uzoq
    toza algoritmi to'g'ri ishlashi uchun muhim.
    """

    model_config = ConfigDict(use_enum_values=False, validate_assignment=True)

    number: int = Field(..., ge=100, le=699, description="Xona raqami (qavat*100 + raqam)")
    floor: int = Field(..., ge=1, le=6)
    room_type: RoomType
    status: RoomStatus = RoomStatus.CLEAN
    near_lift: bool = False
    near_stairs: bool = False
    nightly_rate: Decimal = Field(..., ge=0)
    status_changed_at: datetime = Field(default_factory=_now)

    def mark_status_changed(self, new_status: RoomStatus) -> None:
        """Holatni yangilab, status_changed_at ni qayta o'rnatadi."""
        self.status = new_status
        self.status_changed_at = _now()


class Guest(BaseModel):
    """Mehmon yozuvi — maxfiy ma'lumotlar to'lov tafsilotlarini o'z ichiga olishi mumkin."""

    model_config = ConfigDict(validate_assignment=True)

    guest_id: str = Field(default_factory=lambda: _new_id("GST"))
    full_name: str = Field(..., min_length=2, max_length=100)
    document_id: str = Field(..., min_length=4, max_length=30, description="Pasport/ID raqami")
    payment_card_last4: str = Field(..., pattern=r"^\d{4}$")

    @field_validator("full_name")
    @classmethod
    def _sanitize_name(cls, v: str) -> str:
        """Ortiqcha bo'shliqlarni olib tashlash va boshlang'ich tekshirish."""
        cleaned = " ".join(v.split())
        if not cleaned:
            raise ValueError("To'liq ism bo'sh bo'lishi mumkin emas")
        return cleaned

    def public_view(self) -> dict:
        """Ma'lumotlarni oshkor qilmaslik uchun panelga uzatiladigan xavfsiz ko'rinish.

        Pasport va to'lov ma'lumotlari WebSocket orqali hech qachon yuborilmaydi.
        """
        return {
            "guest_id": self.guest_id,
            "full_name": self.full_name,
        }


class BookingPreference(BaseModel):
    """Mehmonning check-in afzalliklari."""

    preferred_floor: Optional[int] = Field(default=None, ge=1, le=6)
    proximity: ProximityPreference = ProximityPreference.NONE


class Booking(BaseModel):
    """Faol bron yoki check-in yozuvi."""

    booking_id: str = Field(default_factory=lambda: _new_id("BKG"))
    guest_id: str
    room_number: Optional[int] = None
    requested_room_type: RoomType
    preference: BookingPreference = Field(default_factory=BookingPreference)
    check_in_at: Optional[datetime] = None
    check_out_at: Optional[datetime] = None
    nights: int = Field(..., ge=1, le=365)
    nightly_rate_locked: Decimal = Field(..., ge=0)
    extra_charges: Decimal = Field(default=Decimal("0"))


class RoomServiceOrder(BaseModel):
    """Xona xizmati buyurtmasi."""

    order_id: str = Field(default_factory=lambda: _new_id("ORD"))
    room_number: int
    items: list[dict] = Field(..., min_length=1, description="[{'name': str, 'qty': int, 'price': Decimal}]")
    total: Decimal
    status: OrderStatus = OrderStatus.RECEIVED
    placed_at: datetime = Field(default_factory=_now)
    status_changed_at: datetime = Field(default_factory=_now)


class MaintenanceIssue(BaseModel):
    """Texnik xizmat so'rovi."""

    issue_id: str = Field(default_factory=lambda: _new_id("ISS"))
    room_number: int
    description: str = Field(..., min_length=3, max_length=500)
    urgency: IssueUrgency
    status: IssueStatus = IssueStatus.REPORTED
    reported_at: datetime = Field(default_factory=_now)
    assigned_technician: Optional[str] = None
    resolved_at: Optional[datetime] = None


class Staff(BaseModel):
    """Xodim asosiy klassi — OOP meros olishi uchun asos."""

    staff_id: str = Field(default_factory=lambda: _new_id("STF"))
    full_name: str
    role: StaffRole
    on_duty: bool = True
