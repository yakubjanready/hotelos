"""
HotelOS asosiy biznes algoritmlari.

Bu modulda HotelOS yuragi joylashgan:
1. assign_room()    — ko'p mezonli xona tayinlash algoritmi (LO1, P1, D1)
2. calculate_bill() — check-out hisob-kitobi algoritmi
3. validate_assignment_inputs() — boshlang'ich tekshiruvlar

Algoritmlar SOF (pure) funksiyalardir — kirish bo'yicha aniq chiqish hosil
qiladi, hech qanday yon ta'sirsiz. Bu ularni izolyatsiya qilingan tarzda test
qilishni osonlashtiradi (Hunt va Thomas, 2000).

Algoritm dizayni 1.1-bo'limda hujjatlashtirilgan va docs/algorithms.md da
blok-sxema bilan birga keltirilgan.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Optional

from shared.enums import ProximityPreference, RoomStatus, RoomType
from shared.models import Booking, Room, RoomServiceOrder

logger = logging.getLogger("hotelos.algorithms")

# Maxsus konstantalar — sehrli raqamlar emas.
LATE_CHECKOUT_FEE = Decimal("25.00")
MINIBAR_DEFAULT_CHARGE = Decimal("0.00")
DISCOUNT_MIN_PERCENT = Decimal("0")
DISCOUNT_MAX_PERCENT = Decimal("100")
ROUNDING_PLACES = Decimal("0.01")


# === Xato turi: barcha algoritm xatolari uchun yagona klass ===

class NoRoomAvailableError(Exception):
    """So'ralgan mezonlar bo'yicha xona topilmaganida ko'tariladi."""


# === Algoritm natijasi konteyneri ===

@dataclass(frozen=True)
class RoomAssignment:
    """Tayinlash natijasi va undan kelib chiqqan asoslash.

    `reasoning` — qaror nima uchun shu xona uchun qabul qilinganini
    odam o'qiy oladigan tarzda tushuntiradi (audit/debug uchun).
    """

    room_number: int
    reasoning: list[str]


# === ASOSIY ALGORITM: Xona tayinlash ===
#
# Bu funksiya 1.1-bo'limdagi dizaynni amalga oshiradi. Bosqichlar:
#
#   1. Mezon-1: room_type mos kelishi (qattiq filtr — sig'ish shart).
#   2. Mezon-2: status == CLEAN bo'lishi (faqat tozalar).
#   3. Eng uzoq toza tartiblash: status_changed_at eng eski birinchi.
#   4. Mezon-3: agar preferred_floor berilgan bo'lsa — birinchi navbatda
#      shu qavat. Agar topilmasa, boshqa qavatlarga fallback.
#   5. Mezon-4: proximity (lift/stairs) — yakuniy hal qiluvchi omil
#      tiebreaker sifatida (oxirgi qadam).
#   6. Bo'sh natija bo'lsa → NoRoomAvailableError.
#
# Murakkablik: O(n) — bir marta ro'yxat bo'ylab o'tiladi, keyin tartiblash
# kerak bo'lsa O(k log k) bu yerda k qoniqarli xonalar soni.
#
def assign_room(
    inventory: Iterable[Room],
    requested_type: RoomType,
    preferred_floor: Optional[int] = None,
    proximity: ProximityPreference = ProximityPreference.NONE,
) -> RoomAssignment:
    """Ko'p mezonli xona tayinlash algoritmini ishga tushiradi.

    Parametrlar:
        inventory: barcha xonalar ro'yxati (iteratsiya qilinadi).
        requested_type: mehmon bron qilgan xona turi.
        preferred_floor: ixtiyoriy afzal qavat (1..6).
        proximity: lift/zinapoyaga yaqinlik afzalligi.

    Qaytaradi:
        RoomAssignment — tanlangan xona raqami va qaror izi.

    Istisno:
        NoRoomAvailableError — mos xona topilmasa.
    """
    reasoning: list[str] = []

    # --- Mezon-1: xona turi mosligi ---
    by_type = [room for room in inventory if room.room_type == requested_type]
    reasoning.append(f"Mezon-1 (turi): '{requested_type.value}' bo'yicha {len(by_type)} xona topildi")
    if not by_type:
        raise NoRoomAvailableError(
            f"'{requested_type.value}' turidagi xona umuman mavjud emas"
        )

    # --- Mezon-2: faqat toza xonalar ---
    clean_rooms = [room for room in by_type if room.status == RoomStatus.CLEAN]
    reasoning.append(
        f"Mezon-2 (tozalik): {len(clean_rooms)} ta toza xona "
        f"({len(by_type) - len(clean_rooms)} ta band/iflos/tozalanmoqda chiqarib tashlandi)"
    )
    if not clean_rooms:
        raise NoRoomAvailableError(
            f"'{requested_type.value}' turida toza xona mavjud emas"
        )

    # --- Mezon-3: qavat afzalligi (ikkinchi darajali filtr) ---
    floor_filtered: list[Room]
    if preferred_floor is not None:
        on_floor = [room for room in clean_rooms if room.floor == preferred_floor]
        if on_floor:
            floor_filtered = on_floor
            reasoning.append(
                f"Mezon-3 (qavat): {preferred_floor}-qavatda {len(on_floor)} mos xona — qo'llanildi"
            )
        else:
            floor_filtered = clean_rooms
            reasoning.append(
                f"Mezon-3 (qavat): {preferred_floor}-qavatda yo'q — istalgan qavatga fallback"
            )
    else:
        floor_filtered = clean_rooms
        reasoning.append("Mezon-3 (qavat): mehmon afzalligi berilmagan — o'tkazib yuborildi")

    # --- Birlamchi tartib: eng uzoq toza (eski status_changed_at birinchi) ---
    # Bu xonalar ishlatilishini tekis aylantirish uchun.
    floor_filtered.sort(key=lambda r: r.status_changed_at)
    reasoning.append("Eng uzoq toza bo'yicha o'sib boruvchi tartibda tartiblandi")

    # --- Mezon-4: proximity (lift/stairs) — yakuniy hal qiluvchi ---
    if proximity == ProximityPreference.LIFT:
        near = [r for r in floor_filtered if r.near_lift]
        if near:
            chosen = near[0]
            reasoning.append(
                f"Mezon-4 (yaqinlik=lift): liftga yaqin {len(near)} xona; eng uzoq toza tanlandi"
            )
        else:
            chosen = floor_filtered[0]
            reasoning.append("Mezon-4 (yaqinlik=lift): liftga yaqin xona yo'q — birinchi mos xona")
    elif proximity == ProximityPreference.STAIRS:
        near = [r for r in floor_filtered if r.near_stairs]
        if near:
            chosen = near[0]
            reasoning.append(
                f"Mezon-4 (yaqinlik=stairs): zinaga yaqin {len(near)} xona; eng uzoq toza tanlandi"
            )
        else:
            chosen = floor_filtered[0]
            reasoning.append("Mezon-4 (yaqinlik=stairs): zinaga yaqin xona yo'q — birinchi mos xona")
    else:
        chosen = floor_filtered[0]
        reasoning.append("Mezon-4 (yaqinlik): afzallik yo'q — eng uzoq toza tanlandi")

    reasoning.append(f"TANLANDI: xona #{chosen.number} (qavat {chosen.floor})")
    logger.info("Xona tayinlandi: %s — %s", chosen.number, " | ".join(reasoning))
    return RoomAssignment(room_number=chosen.number, reasoning=reasoning)


# === IKKINCHI ALGORITM: Hisob-kitob ===
#
# Brief talab qiladi: tunlik narx × tunlar + xona xizmati to'lovlari +
# qo'shimcha to'lovlar (minibar, kech check-out). Chegirma qo'llash.
# Chegaraviy holatlar: erta check-out, nol to'lovlar.
#
def calculate_bill(
    booking: Booking,
    room_service_orders: Iterable[RoomServiceOrder],
    minibar_charge: Decimal = MINIBAR_DEFAULT_CHARGE,
    late_checkout: bool = False,
    discount_percent: Decimal = Decimal("0"),
    actual_checkout: Optional[datetime] = None,
) -> dict:
    """Mehmon check-outda umumiy to'lovni hisoblaydi.

    Erta check-out: agar `actual_checkout` berilgan bo'lsa, bron qilingan
    tunlar o'rniga haqiqiy tunlar hisoblanadi (lekin minimum 1 tun).

    Qaytaradi: yorliqlangan bo'limlarga ega lug'at — auditga oson.
    """
    if discount_percent < DISCOUNT_MIN_PERCENT or discount_percent > DISCOUNT_MAX_PERCENT:
        raise ValueError("Chegirma 0–100% oralig'ida bo'lishi kerak")

    # Haqiqiy tunlar sonini aniqlash (erta check-out qo'llab-quvvatlash)
    nights = booking.nights
    if actual_checkout and booking.check_in_at:
        actual_nights = max(1, (actual_checkout - booking.check_in_at).days)
        nights = min(nights, actual_nights)

    room_subtotal = booking.nightly_rate_locked * nights

    # Xona xizmati to'lovlari yig'indisi
    service_subtotal = sum(
        (order.total for order in room_service_orders),
        start=Decimal("0"),
    )

    # Qo'shimcha to'lovlar
    extras = booking.extra_charges + minibar_charge
    if late_checkout:
        extras += LATE_CHECKOUT_FEE

    gross_total = room_subtotal + service_subtotal + extras

    discount_amount = (gross_total * discount_percent / Decimal("100")).quantize(
        ROUNDING_PLACES, rounding=ROUND_HALF_UP
    )
    net_total = (gross_total - discount_amount).quantize(
        ROUNDING_PLACES, rounding=ROUND_HALF_UP
    )

    breakdown = {
        "booking_id": booking.booking_id,
        "room_number": booking.room_number,
        "nights_charged": nights,
        "nightly_rate": str(booking.nightly_rate_locked),
        "room_subtotal": str(room_subtotal.quantize(ROUNDING_PLACES)),
        "room_service_subtotal": str(service_subtotal.quantize(ROUNDING_PLACES)),
        "minibar_charge": str(minibar_charge.quantize(ROUNDING_PLACES)),
        "late_checkout_fee": str(LATE_CHECKOUT_FEE.quantize(ROUNDING_PLACES)) if late_checkout else "0.00",
        "gross_total": str(gross_total.quantize(ROUNDING_PLACES)),
        "discount_percent": str(discount_percent),
        "discount_amount": str(discount_amount),
        "net_total": str(net_total),
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("Hisob hisoblandi: %s -> %s", booking.booking_id, net_total)
    return breakdown
