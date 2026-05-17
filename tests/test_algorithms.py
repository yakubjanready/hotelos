"""
Birlik (unit) testlari — algoritmlar uchun.

`pytest tests/test_algorithms.py -v` bilan ishga tushiring.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from reception_service.algorithms import (
    NoRoomAvailableError,
    assign_room,
    calculate_bill,
)
from shared.enums import ProximityPreference, RoomStatus, RoomType
from shared.models import Booking, BookingPreference, Room, RoomServiceOrder


def _make_room(number: int, floor: int, rtype: RoomType, status: RoomStatus,
               near_lift: bool = False, near_stairs: bool = False,
               cleaned_minutes_ago: int = 60) -> Room:
    """Test xonasini tezda yaratish uchun yordamchi."""
    return Room(
        number=number,
        floor=floor,
        room_type=rtype,
        status=status,
        near_lift=near_lift,
        near_stairs=near_stairs,
        nightly_rate=Decimal("100.00"),
        status_changed_at=datetime.now(timezone.utc) - timedelta(minutes=cleaned_minutes_ago),
    )


# === assign_room testlari ===

class TestAssignRoom:
    def test_basic_match_returns_correct_type(self):
        rooms = [
            _make_room(101, 1, RoomType.SINGLE, RoomStatus.CLEAN),
            _make_room(102, 1, RoomType.DOUBLE, RoomStatus.CLEAN),
        ]
        result = assign_room(rooms, RoomType.DOUBLE)
        assert result.room_number == 102

    def test_dirty_rooms_are_excluded(self):
        rooms = [
            _make_room(101, 1, RoomType.SINGLE, RoomStatus.DIRTY),
            _make_room(102, 1, RoomType.SINGLE, RoomStatus.CLEAN),
        ]
        result = assign_room(rooms, RoomType.SINGLE)
        assert result.room_number == 102

    def test_longest_clean_wins_when_tied(self):
        rooms = [
            _make_room(101, 1, RoomType.SINGLE, RoomStatus.CLEAN, cleaned_minutes_ago=30),
            _make_room(102, 1, RoomType.SINGLE, RoomStatus.CLEAN, cleaned_minutes_ago=120),
            _make_room(103, 1, RoomType.SINGLE, RoomStatus.CLEAN, cleaned_minutes_ago=60),
        ]
        result = assign_room(rooms, RoomType.SINGLE)
        # 102 eng uzoq vaqt toza turibdi -> birinchi
        assert result.room_number == 102

    def test_floor_preference_is_honored_when_available(self):
        rooms = [
            _make_room(101, 1, RoomType.DOUBLE, RoomStatus.CLEAN, cleaned_minutes_ago=180),
            _make_room(304, 3, RoomType.DOUBLE, RoomStatus.CLEAN, cleaned_minutes_ago=60),
        ]
        result = assign_room(rooms, RoomType.DOUBLE, preferred_floor=3)
        assert result.room_number == 304

    def test_floor_preference_falls_back_to_any_floor(self):
        rooms = [
            _make_room(101, 1, RoomType.DOUBLE, RoomStatus.CLEAN),
            _make_room(205, 2, RoomType.DOUBLE, RoomStatus.CLEAN, cleaned_minutes_ago=200),
        ]
        result = assign_room(rooms, RoomType.DOUBLE, preferred_floor=3)
        # 3-qavatda yo'q -> eng uzoq toza (205) tushadi
        assert result.room_number == 205

    def test_proximity_lift_chooses_lift_adjacent(self):
        rooms = [
            _make_room(101, 1, RoomType.SUITE, RoomStatus.CLEAN, near_lift=False, cleaned_minutes_ago=180),
            _make_room(102, 1, RoomType.SUITE, RoomStatus.CLEAN, near_lift=True, cleaned_minutes_ago=60),
        ]
        result = assign_room(rooms, RoomType.SUITE, proximity=ProximityPreference.LIFT)
        # Yaqinlik yakuniy hal qiluvchi: liftga yaqin xona tanlandi
        assert result.room_number == 102

    def test_no_clean_room_raises(self):
        rooms = [_make_room(101, 1, RoomType.SINGLE, RoomStatus.DIRTY)]
        with pytest.raises(NoRoomAvailableError):
            assign_room(rooms, RoomType.SINGLE)

    def test_no_matching_type_raises(self):
        rooms = [_make_room(101, 1, RoomType.SINGLE, RoomStatus.CLEAN)]
        with pytest.raises(NoRoomAvailableError):
            assign_room(rooms, RoomType.SUITE)

    def test_reasoning_contains_all_criteria(self):
        rooms = [_make_room(101, 1, RoomType.SINGLE, RoomStatus.CLEAN)]
        result = assign_room(rooms, RoomType.SINGLE, preferred_floor=1, proximity=ProximityPreference.NONE)
        joined = " ".join(result.reasoning)
        for token in ("Mezon-1", "Mezon-2", "Mezon-3", "Mezon-4", "TANLANDI"):
            assert token in joined


# === calculate_bill testlari ===

class TestCalculateBill:
    def _booking(self, nights: int = 3) -> Booking:
        return Booking(
            guest_id="GST-test",
            room_number=204,
            requested_room_type=RoomType.DOUBLE,
            preference=BookingPreference(),
            check_in_at=datetime(2026, 5, 14, 14, 0, tzinfo=timezone.utc),
            nights=nights,
            nightly_rate_locked=Decimal("125.00"),
        )

    def test_basic_total_no_extras(self):
        bill = calculate_bill(self._booking(nights=3), room_service_orders=[])
        assert bill["room_subtotal"] == "375.00"
        assert bill["net_total"] == "375.00"

    def test_room_service_added(self):
        order = RoomServiceOrder(
            room_number=204,
            items=[{"name": "Qahva", "qty": 2, "price": 4.50}],
            total=Decimal("9.00"),
        )
        bill = calculate_bill(self._booking(3), room_service_orders=[order])
        assert bill["room_service_subtotal"] == "9.00"
        assert bill["net_total"] == "384.00"

    def test_minibar_and_late_checkout(self):
        bill = calculate_bill(
            self._booking(2),
            room_service_orders=[],
            minibar_charge=Decimal("15.00"),
            late_checkout=True,
        )
        # 250 (xona) + 15 (minibar) + 25 (kech check-out) = 290
        assert bill["net_total"] == "290.00"

    def test_discount_applied(self):
        bill = calculate_bill(
            self._booking(4),
            room_service_orders=[],
            discount_percent=Decimal("10"),
        )
        # 500 * 0.10 = 50 chegirma -> 450
        assert bill["discount_amount"] == "50.00"
        assert bill["net_total"] == "450.00"

    def test_early_checkout_reduces_nights(self):
        booking = self._booking(nights=5)
        actual = booking.check_in_at + timedelta(days=2)
        bill = calculate_bill(booking, room_service_orders=[], actual_checkout=actual)
        assert bill["nights_charged"] == 2
        assert bill["net_total"] == "250.00"
