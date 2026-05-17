#!/usr/bin/env python3
"""
HotelOS algoritmlari namoyishi — tashqi paketsiz (faqat stdlib).

Ushbu skript algoritmlarning haqiqiy ishlashini ko'rsatadi va kirish/chiqishni
hisobotda ko'rsatish uchun toza chiqish hosil qiladi. Ishlab chiqarish kodi
reception_service/algorithms.py va maintenance_service/priority_queue.py
fayllarida joylashgan; bu yerda algoritm mantig'i namoyish maqsadida qayta
ishlatilgan.

Ishga tushirish:
    python3 scripts/demo_algorithms.py
"""

from __future__ import annotations

import heapq
import itertools
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from pathlib import Path
from typing import Optional


# === Enum'lar (production kodidagi shared/enums.py bilan bir xil) ===

class RoomType(str, Enum):
    SINGLE = "single"
    DOUBLE = "double"
    SUITE = "suite"
    ACCESSIBLE = "accessible"


class RoomStatus(str, Enum):
    CLEAN = "clean"
    OCCUPIED = "occupied"
    DIRTY = "dirty"
    CLEANING = "cleaning"
    MAINTENANCE = "maintenance"


class ProximityPreference(str, Enum):
    LIFT = "lift"
    STAIRS = "stairs"
    NONE = "none"


class IssueUrgency(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"

    def priority_value(self) -> int:
        return {"critical": 0, "high": 1, "normal": 2, "low": 3}[self.value]


# === Stdlib Room modeli (production kodida Pydantic Room) ===

@dataclass
class Room:
    number: int
    floor: int
    room_type: RoomType
    status: RoomStatus
    near_lift: bool = False
    near_stairs: bool = False
    nightly_rate: Decimal = Decimal("100.00")
    status_changed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# === Xona tayinlash algoritmi (assign_room) — production bilan bir xil mantiq ===

class NoRoomAvailableError(Exception):
    pass


@dataclass(frozen=True)
class RoomAssignment:
    room_number: int
    reasoning: list[str]


def assign_room(inventory, requested_type, preferred_floor=None, proximity=ProximityPreference.NONE):
    reasoning: list[str] = []

    # Mezon-1: turi mosligi
    by_type = [r for r in inventory if r.room_type == requested_type]
    reasoning.append(f"Mezon-1 (turi): '{requested_type.value}' -> {len(by_type)} xona")
    if not by_type:
        raise NoRoomAvailableError(f"'{requested_type.value}' turi yo'q")

    # Mezon-2: faqat toza
    clean_rooms = [r for r in by_type if r.status == RoomStatus.CLEAN]
    reasoning.append(f"Mezon-2 (tozalik): {len(clean_rooms)} ta toza")
    if not clean_rooms:
        raise NoRoomAvailableError("toza xona yo'q")

    # Mezon-3: qavat afzalligi
    if preferred_floor is not None:
        on_floor = [r for r in clean_rooms if r.floor == preferred_floor]
        if on_floor:
            filtered = on_floor
            reasoning.append(f"Mezon-3 (qavat): {preferred_floor}-qavatda {len(on_floor)} xona")
        else:
            filtered = clean_rooms
            reasoning.append(f"Mezon-3 (qavat): {preferred_floor}-qavatda yo'q -> fallback")
    else:
        filtered = clean_rooms
        reasoning.append("Mezon-3 (qavat): afzallik yo'q")

    # Eng uzoq toza: status_changed_at o'sib boruvchi tartibda
    filtered.sort(key=lambda r: r.status_changed_at)
    reasoning.append("Eng uzoq toza bo'yicha tartiblandi")

    # Mezon-4: yaqinlik
    if proximity == ProximityPreference.LIFT:
        near = [r for r in filtered if r.near_lift]
        chosen = near[0] if near else filtered[0]
        reasoning.append(
            f"Mezon-4 (lift): {len(near)} ta liftga yaqin"
            if near else "Mezon-4 (lift): yaqin xona yo'q"
        )
    elif proximity == ProximityPreference.STAIRS:
        near = [r for r in filtered if r.near_stairs]
        chosen = near[0] if near else filtered[0]
        reasoning.append(
            f"Mezon-4 (stairs): {len(near)} ta zinaga yaqin"
            if near else "Mezon-4 (stairs): yaqin xona yo'q"
        )
    else:
        chosen = filtered[0]
        reasoning.append("Mezon-4: yaqinlik afzalligi yo'q")

    reasoning.append(f"TANLANDI: xona #{chosen.number} (qavat {chosen.floor})")
    return RoomAssignment(room_number=chosen.number, reasoning=reasoning)


# === Hisob-kitob algoritmi (calculate_bill) ===

LATE_CHECKOUT_FEE = Decimal("25.00")
ROUNDING = Decimal("0.01")


def calculate_bill(nightly_rate, nights, service_subtotal=Decimal("0"),
                   minibar=Decimal("0"), late_checkout=False, discount_pct=Decimal("0")):
    room_subtotal = nightly_rate * nights
    extras = minibar + (LATE_CHECKOUT_FEE if late_checkout else Decimal("0"))
    gross = room_subtotal + service_subtotal + extras
    discount = (gross * discount_pct / Decimal("100")).quantize(ROUNDING, rounding=ROUND_HALF_UP)
    net = (gross - discount).quantize(ROUNDING, rounding=ROUND_HALF_UP)
    return {
        "room_subtotal": str(room_subtotal.quantize(ROUNDING)),
        "service_subtotal": str(service_subtotal.quantize(ROUNDING)),
        "extras": str(extras.quantize(ROUNDING)),
        "gross": str(gross.quantize(ROUNDING)),
        "discount": str(discount),
        "net_total": str(net),
    }


# === Priority queue (priority_queue.py bilan bir xil mantiq) ===

@dataclass(order=True)
class _HeapEntry:
    priority: int
    sequence: int
    issue_id: str
    issue_data: dict = field(compare=False)


class IssuePriorityQueue:
    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def push(self, issue_id, urgency, data):
        heapq.heappush(self._heap, _HeapEntry(urgency.priority_value(), next(self._counter), issue_id, data))

    def pop(self):
        if not self._heap:
            return None
        return heapq.heappop(self._heap).issue_data


# === Inventarni yuklash ===

def load_inventory() -> list[Room]:
    path = Path(__file__).resolve().parent.parent / "data" / "rooms.json"
    raw = json.loads(path.read_text())
    rooms: list[Room] = []
    base = datetime.now(timezone.utc) - timedelta(hours=24)
    for i, r in enumerate(raw):
        rooms.append(Room(
            number=r["number"],
            floor=r["floor"],
            room_type=RoomType(r["room_type"]),
            status=RoomStatus(r["status"]),
            near_lift=r["near_lift"],
            near_stairs=r["near_stairs"],
            nightly_rate=Decimal(r["nightly_rate"]),
            # Test uchun har bir xona uchun farqli status_changed_at
            status_changed_at=base + timedelta(minutes=i),
        ))
    return rooms


# === Namoyish ===

def section(title: str) -> None:
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def demo_assign_room():
    section("DEMO 1: Xona tayinlash algoritmi — 120 ta xonali inventar")
    inv = load_inventory()
    print(f"Inventarda: {len(inv)} xona")

    # Demo 1.1: oddiy ikki kishilik, 3-qavatga
    print("\n[1.1] So'rov: ikki kishilik, 3-qavat afzal, yaqinlik=none")
    result = assign_room(inv, RoomType.DOUBLE, preferred_floor=3)
    print(f"  -> xona #{result.room_number}")
    for line in result.reasoning:
        print(f"     {line}")

    # Demo 1.2: lyuks, lift afzalligi
    print("\n[1.2] So'rov: lyuks, liftga yaqin")
    result = assign_room(inv, RoomType.SUITE, proximity=ProximityPreference.LIFT)
    print(f"  -> xona #{result.room_number}")
    for line in result.reasoning:
        print(f"     {line}")

    # Demo 1.3: nogironlarga moslashtirilgan
    print("\n[1.3] So'rov: nogironlarga moslashtirilgan, 5-qavat")
    result = assign_room(inv, RoomType.ACCESSIBLE, preferred_floor=5)
    print(f"  -> xona #{result.room_number}")
    for line in result.reasoning:
        print(f"     {line}")

    # Demo 1.4: imkonsiz holat (ataylab)
    print("\n[1.4] Imkonsiz so'rov: hech bir xona toza emas")
    for room in inv:
        room.status = RoomStatus.DIRTY
    try:
        assign_room(inv, RoomType.SINGLE)
    except NoRoomAvailableError as exc:
        print(f"  -> NoRoomAvailableError: {exc}")


def demo_bill():
    section("DEMO 2: Hisob-kitob algoritmi")

    print("\n[2.1] 3 tunlik ikki kishilik xona")
    bill = calculate_bill(Decimal("125.00"), 3)
    print(json.dumps(bill, indent=2, ensure_ascii=False))

    print("\n[2.2] 2 tun + minibar + kech check-out")
    bill = calculate_bill(Decimal("125.00"), 2, minibar=Decimal("15.00"), late_checkout=True)
    print(json.dumps(bill, indent=2, ensure_ascii=False))

    print("\n[2.3] 4 tun + xona xizmati 35.50 + 10% chegirma")
    bill = calculate_bill(
        Decimal("125.00"), 4,
        service_subtotal=Decimal("35.50"),
        discount_pct=Decimal("10"),
    )
    print(json.dumps(bill, indent=2, ensure_ascii=False))


def demo_priority_queue():
    section("DEMO 3: Texnik xizmat ustuvorlik navbati")

    q = IssuePriorityQueue()
    test_issues = [
        ("ISS-001", IssueUrgency.LOW, "yorug'lik miltillaydi (xona 220)"),
        ("ISS-002", IssueUrgency.HIGH, "konditsioner ishlamayapti (xona 415)"),
        ("ISS-003", IssueUrgency.CRITICAL, "suv qochmoqda (xona 115)"),
        ("ISS-004", IssueUrgency.NORMAL, "TV pulti yo'q (xona 308)"),
        ("ISS-005", IssueUrgency.HIGH, "minibar sovutmaydi (xona 622)"),
        ("ISS-006", IssueUrgency.CRITICAL, "elektr o'chgan (xona 119)"),
    ]
    print(f"\nKiritilgan tartib: {[i[0] for i in test_issues]}")
    for iid, urg, desc in test_issues:
        q.push(iid, urg, {"issue_id": iid, "urgency": urg.value, "desc": desc})

    print(f"\nNavbatdan chiqish tartibi (kutilgan: kritiklar FIFO, keyin yuqorilar FIFO, ...):")
    order: list[str] = []
    while True:
        item = q.pop()
        if item is None:
            break
        order.append(item["issue_id"])
        print(f"  -> {item['issue_id']} [{item['urgency']:8}] {item['desc']}")

    assert order == ["ISS-003", "ISS-006", "ISS-002", "ISS-005", "ISS-004", "ISS-001"]
    print("\n  ✓ Kutilgan tartib bilan mos keldi (Critical FIFO -> High FIFO -> Normal -> Low)")


def main():
    print("HotelOS algoritm namoyishi")
    print(f"Sana: {datetime.now().isoformat()}")
    demo_assign_room()
    demo_bill()
    demo_priority_queue()
    print()
    print("=" * 70)
    print("  Barcha demo'lar muvaffaqiyatli yakunlandi ✓")
    print("=" * 70)


if __name__ == "__main__":
    main()
