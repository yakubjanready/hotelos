#!/usr/bin/env python3
"""
HotelOS 120 ta xonali inventarini hosil qiluvchi skript.

6 qavat × 20 xona = 120 xona. Xona raqami konventsiyasi: <qavat><raqam>
(masalan, 2-qavatdagi 5-xona = 205).

Xona turlari taqsimoti har bir qavatda:
  - 10 single (.01..10)
  - 7 double (.11..17)
  - 2 suite (.18..19)
  - 1 accessible (.20)

Yaqinlik atributlari: lift xonalari .01..02 va .19..20; zinapoya .01 va .20.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

FLOORS = 6
ROOMS_PER_FLOOR = 20

NIGHTLY_RATES: dict[str, Decimal] = {
    "single": Decimal("85.00"),
    "double": Decimal("125.00"),
    "suite": Decimal("280.00"),
    "accessible": Decimal("110.00"),
}


def _room_type_for(slot: int) -> str:
    """Qavat ichida xona o'rni (1..20) bo'yicha turini qaytaradi."""
    if 1 <= slot <= 10:
        return "single"
    if 11 <= slot <= 17:
        return "double"
    if 18 <= slot <= 19:
        return "suite"
    return "accessible"  # slot == 20


def generate_rooms() -> list[dict[str, Any]]:
    """Barcha 120 xonani metama'lumotlar bilan hosil qiladi."""
    rooms: list[dict[str, Any]] = []
    for floor in range(1, FLOORS + 1):
        for slot in range(1, ROOMS_PER_FLOOR + 1):
            number = floor * 100 + slot
            rtype = _room_type_for(slot)
            rooms.append(
                {
                    "number": number,
                    "floor": floor,
                    "room_type": rtype,
                    "status": "clean",
                    "near_lift": slot in (1, 2, 19, 20),
                    "near_stairs": slot in (1, 20),
                    "nightly_rate": str(NIGHTLY_RATES[rtype]),
                    "status_changed_at": "2026-05-17T00:00:00+00:00",
                }
            )
    return rooms


def main() -> None:
    output = Path(__file__).resolve().parent.parent / "data" / "rooms.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    rooms = generate_rooms()
    output.write_text(json.dumps(rooms, indent=2, ensure_ascii=False))
    print(f"Yaratildi: {output} ({len(rooms)} xona)")


if __name__ == "__main__":
    main()
