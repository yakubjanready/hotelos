"""
HotelOS hodisalar lug'ati.

Barcha mavzu (topic) nomlari va yuk (payload) sxemalari shu yerda
markazlashtirilgan — bu yangi servis qo'shilganda integratsiyani osonlashtiradi
va yozuv xatolarini oldini oladi.

Hodisa nomi konventsiyasi: "<sub'ekt>.<harakat>" (masalan, "room.vacated").
"""

from __future__ import annotations

# === Mavzular (kanallar) ===

# Reception tomonidan nashr etiladi
EVT_ROOM_OCCUPIED = "room.occupied"
EVT_ROOM_VACATED = "room.vacated"
EVT_GUEST_CHECKED_IN = "guest.checked_in"
EVT_GUEST_CHECKED_OUT = "guest.checked_out"

# Housekeeping tomonidan nashr etiladi
EVT_ROOM_CLEANING_STARTED = "room.cleaning_started"
EVT_ROOM_CLEANED = "room.cleaned"

# Room Service tomonidan nashr etiladi
EVT_ORDER_RECEIVED = "order.received"
EVT_ORDER_PREPARING = "order.preparing"
EVT_ORDER_DELIVERING = "order.delivering"
EVT_ORDER_DELIVERED = "order.delivered"

# Maintenance tomonidan nashr etiladi
EVT_ISSUE_REPORTED = "issue.reported"
EVT_ISSUE_ASSIGNED = "issue.assigned"
EVT_ISSUE_RESOLVED = "issue.resolved"

# Panel uchun yig'ma broadcast kanali
EVT_DASHBOARD_STATE = "dashboard.state"


ALL_EVENTS: tuple[str, ...] = (
    EVT_ROOM_OCCUPIED,
    EVT_ROOM_VACATED,
    EVT_GUEST_CHECKED_IN,
    EVT_GUEST_CHECKED_OUT,
    EVT_ROOM_CLEANING_STARTED,
    EVT_ROOM_CLEANED,
    EVT_ORDER_RECEIVED,
    EVT_ORDER_PREPARING,
    EVT_ORDER_DELIVERING,
    EVT_ORDER_DELIVERED,
    EVT_ISSUE_REPORTED,
    EVT_ISSUE_ASSIGNED,
    EVT_ISSUE_RESOLVED,
)
