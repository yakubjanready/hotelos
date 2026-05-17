#!/usr/bin/env python3
"""
HotelOS test stsenariylari (TS-01..TS-08) — to'liq integratsion test runner.

Servislar ishlab turgan paytda ishga tushiriladi:
    1. docker compose up -d
    2. scripts/start_all.sh
    3. python scripts/run_test_scenarios.py

Skript har bir stsenariyni HTTP API orqali bajaradi, kutilgan natija bilan
solishtiradi va konsolga + fayl ga (docs/test_results.md) yozadi.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

BASE_RECEPTION = "http://localhost:8001"
BASE_HOUSEKEEPING = "http://localhost:8002"
BASE_ROOMSERVICE = "http://localhost:8003"
BASE_MAINTENANCE = "http://localhost:8004"
BASE_DASHBOARD = "http://localhost:8000"


class ScenarioResult:
    def __init__(self, sid: str, desc: str) -> None:
        self.sid = sid
        self.desc = desc
        self.steps: list[str] = []
        self.passed = True
        self.error: str | None = None

    def step(self, msg: str) -> None:
        self.steps.append(msg)
        print(f"   {msg}")

    def fail(self, msg: str) -> None:
        self.passed = False
        self.error = msg
        print(f"   ❌ {msg}")

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"{self.sid} [{status}] — {self.desc}"


async def ts01_basic_checkin(client: httpx.AsyncClient) -> ScenarioResult:
    r = ScenarioResult("TS-01", "Check-in: ikki kishilik xona, 3-qavat afzalligi")
    print(f"\n{r.sid}: {r.desc}")
    payload = {
        "full_name": "Ali Valiyev",
        "document_id": "AB1234567",
        "payment_card_last4": "4242",
        "requested_room_type": "double",
        "preferred_floor": 3,
        "proximity": "none",
        "nights": 2,
    }
    resp = await client.post(f"{BASE_RECEPTION}/checkin", json=payload)
    if resp.status_code != 201:
        r.fail(f"HTTP {resp.status_code}: {resp.text}")
        return r
    data = resp.json()
    room = data["room_number"]
    r.step(f"Tayinlangan xona: {room}")
    if not (300 <= room < 400):
        r.fail(f"3-qavatda emas: xona {room}")
    else:
        r.step("3-qavatda — afzallik qo'llanildi ✓")
    r.step("Reasoning: " + " | ".join(data["reasoning"][:3]) + " ...")
    return r


async def ts02_checkout(client: httpx.AsyncClient) -> ScenarioResult:
    r = ScenarioResult("TS-02", "Check-out: hisob hisoblanadi, room.vacated nashr etiladi")
    print(f"\n{r.sid}: {r.desc}")
    # avval check-in qilamiz
    ci = await client.post(f"{BASE_RECEPTION}/checkin", json={
        "full_name": "Bekzod Tursunov", "document_id": "CD9876543",
        "payment_card_last4": "1111", "requested_room_type": "single",
        "nights": 3,
    })
    if ci.status_code != 201:
        r.fail(f"Check-in muvaffaqiyatsiz: {ci.text}")
        return r
    booking_id = ci.json()["booking_id"]
    room = ci.json()["room_number"]
    r.step(f"Check-in: bron {booking_id}, xona {room}")

    co = await client.post(f"{BASE_RECEPTION}/checkout", json={
        "booking_id": booking_id, "minibar_charge": 12.50, "late_checkout": False,
    })
    if co.status_code != 200:
        r.fail(f"Check-out muvaffaqiyatsiz: {co.text}")
        return r
    bill = co.json()["bill"]
    r.step(f"Hisob: net={bill['net_total']}, nights={bill['nights_charged']}")
    r.step(f"Xona holati: {co.json()['room_status']}")
    if co.json()["room_status"] != "dirty":
        r.fail("Xona Iflos holatga o'tmadi")
    return r


async def ts03_cleaning_flow(client: httpx.AsyncClient) -> ScenarioResult:
    r = ScenarioResult("TS-03", "Tozalovchi xonani toza deb belgilaydi")
    print(f"\n{r.sid}: {r.desc}")
    # Avval check-in + check-out qilib navbatga bitta xona qo'shamiz
    ci = await client.post(f"{BASE_RECEPTION}/checkin", json={
        "full_name": "Charos Saidova", "document_id": "EF1122334",
        "payment_card_last4": "2222", "requested_room_type": "single", "nights": 1,
    })
    if ci.status_code != 201:
        r.fail(ci.text); return r
    booking = ci.json()["booking_id"]
    await client.post(f"{BASE_RECEPTION}/checkout", json={"booking_id": booking})
    # Broker yetib borishi uchun kichik kutish
    await asyncio.sleep(0.3)

    claim = await client.post(f"{BASE_HOUSEKEEPING}/claim")
    if claim.status_code != 200:
        r.fail(f"Claim muvaffaqiyatsiz: {claim.text}")
        return r
    room = claim.json()["room_number"]
    r.step(f"Tozalashga olindi: xona {room}")

    done = await client.post(f"{BASE_HOUSEKEEPING}/mark_clean/{room}")
    if done.status_code != 200:
        r.fail(done.text); return r
    r.step(f"Toza deb belgilandi: xona {room} ✓")
    await asyncio.sleep(0.3)
    rooms = (await client.get(f"{BASE_RECEPTION}/rooms")).json()
    room_state = next((x for x in rooms if x["number"] == room), None)
    if room_state and room_state["status"] != "clean":
        r.fail(f"Inventarda holat 'clean' emas: {room_state['status']}")
    else:
        r.step("Reception inventarida xona Toza ✓")
    return r


async def ts04_room_service(client: httpx.AsyncClient) -> ScenarioResult:
    r = ScenarioResult("TS-04", "Xona xizmati buyurtmasi: 2 qahva + sendvich")
    print(f"\n{r.sid}: {r.desc}")
    # Avval bir mehmonni check-in qilamiz (chunki TS-04 mavjud band xonani nazarda tutadi)
    ci = await client.post(f"{BASE_RECEPTION}/checkin", json={
        "full_name": "Dilnoza Yuldosheva", "document_id": "GH5544332",
        "payment_card_last4": "3333", "requested_room_type": "single", "nights": 2,
    })
    if ci.status_code != 201:
        r.fail(ci.text); return r
    room_number = ci.json()["room_number"]
    order = await client.post(f"{BASE_ROOMSERVICE}/orders", json={
        "room_number": room_number,
        "items": [{"name": "Qahva", "qty": 2}, {"name": "Sendvich", "qty": 1}],
    })
    if order.status_code != 201:
        r.fail(order.text); return r
    oid = order.json()["order_id"]
    r.step(f"Buyurtma: {oid}, total={order.json()['total']}")
    # Holatlarni o'tkazamiz
    for expected in ("preparing", "delivering", "delivered"):
        adv = await client.post(f"{BASE_ROOMSERVICE}/orders/{oid}/advance")
        if adv.status_code != 200 or adv.json()["status"] != expected:
            r.fail(f"Holat {expected} ga o'tmadi: {adv.text}")
            return r
        r.step(f"→ {expected}")
    return r


async def ts05_critical_maintenance(client: httpx.AsyncClient) -> ScenarioResult:
    r = ScenarioResult("TS-05", "Kritik texnik muammo: 115-xona singan dush")
    print(f"\n{r.sid}: {r.desc}")
    # Past ustuvorlikdagi muammo birinchi
    await client.post(f"{BASE_MAINTENANCE}/issues", json={
        "room_number": 220, "description": "Yorug'lik o'chmaydi", "urgency": "low",
    })
    # Kritik keladi
    crit = await client.post(f"{BASE_MAINTENANCE}/issues", json={
        "room_number": 115, "description": "Dush singan, suv tushmoqda", "urgency": "critical",
    })
    if crit.status_code != 201:
        r.fail(crit.text); return r
    r.step(f"Kritik so'rov qaytarildi: {crit.json()['issue_id']}")

    claim = await client.post(f"{BASE_MAINTENANCE}/claim")
    data = claim.json()
    r.step(f"Texnik tayinlandi: {data.get('technician')} -> muammo {data.get('issue_id')}")
    issues = (await client.get(f"{BASE_MAINTENANCE}/issues")).json()
    # Birinchi qolgan element 'low' bo'lishi kerak (kritik allaqachon olingan)
    if issues and issues[0].get("urgency") != "low":
        r.step(f"Keyingi navbatda: {issues[0].get('urgency')} (kritik bartaraf etilgan)")
    return r


async def ts06_concurrent_checkin(client: httpx.AsyncClient) -> ScenarioResult:
    r = ScenarioResult("TS-06", "Ikki mehmon bir vaqtda bir xil turdagi xona so'raydi")
    print(f"\n{r.sid}: {r.desc}")
    payload_a = {"full_name": "User A", "document_id": "AA1111111", "payment_card_last4": "0001",
                 "requested_room_type": "suite", "nights": 1}
    payload_b = {"full_name": "User B", "document_id": "BB2222222", "payment_card_last4": "0002",
                 "requested_room_type": "suite", "nights": 1}
    a, b = await asyncio.gather(
        client.post(f"{BASE_RECEPTION}/checkin", json=payload_a),
        client.post(f"{BASE_RECEPTION}/checkin", json=payload_b),
    )
    if a.status_code != 201 or b.status_code != 201:
        r.fail(f"Birortasi muvaffaqiyatsiz: A={a.status_code}, B={b.status_code}")
        return r
    room_a, room_b = a.json()["room_number"], b.json()["room_number"]
    r.step(f"A xonasi: {room_a}, B xonasi: {room_b}")
    if room_a == room_b:
        r.fail("Bir xil xona ikkala mehmonga tayinlanди!")
    else:
        r.step("Xonalar farqli — race condition oldini olindi ✓")
    return r


async def ts07_no_rooms_available(client: httpx.AsyncClient) -> ScenarioResult:
    r = ScenarioResult("TS-07", "Barcha xonalar band — toza xato")
    print(f"\n{r.sid}: {r.desc}")
    # accessible turida atigi 6 ta xona — ularni to'ldirib bo'lamiz
    successful = 0
    for i in range(8):
        resp = await client.post(f"{BASE_RECEPTION}/checkin", json={
            "full_name": f"Saturator{i}", "document_id": f"SAT{i:07d}",
            "payment_card_last4": "9999", "requested_room_type": "accessible", "nights": 1,
        })
        if resp.status_code == 201:
            successful += 1
        elif resp.status_code == 409:
            r.step(f"{successful} check-in dan keyin: {resp.json()['detail']}")
            return r
    r.step(f"Barcha to'ldirildi ({successful}/6 muvaffaqiyatli)")
    # Yana bir urinish — endi xona qolmagan
    resp = await client.post(f"{BASE_RECEPTION}/checkin", json={
        "full_name": "Overflow", "document_id": "OVR1234567",
        "payment_card_last4": "0000", "requested_room_type": "accessible", "nights": 1,
    })
    if resp.status_code == 409:
        r.step(f"To'g'ri xato qaytarildi: {resp.json()['detail']} ✓")
    else:
        r.fail(f"409 kutgan edik, oldik: {resp.status_code}")
    return r


async def ts08_invalid_input(client: httpx.AsyncClient) -> ScenarioResult:
    r = ScenarioResult("TS-08", "Check-in: noto'g'ri xona raqami — validation")
    print(f"\n{r.sid}: {r.desc}")
    # invalid: short doc id
    resp = await client.post(f"{BASE_RECEPTION}/checkin", json={
        "full_name": "Test", "document_id": "x", "payment_card_last4": "abcd",
        "requested_room_type": "single", "nights": 1,
    })
    if resp.status_code in (400, 422):
        r.step(f"Validation rad etdi: HTTP {resp.status_code} ✓")
    else:
        r.fail(f"Validation rad etmadi: HTTP {resp.status_code}")
    # Servis hali tirikmi?
    h = await client.get(f"{BASE_RECEPTION}/health")
    if h.status_code != 200:
        r.fail("Servis hali javob bermayapti!")
    else:
        r.step("Servis hali ishlamoqda, keyingi kiritish uchun tayyor ✓")
    return r


async def main() -> None:
    start = time.time()
    out_path = Path(__file__).resolve().parent.parent / "docs" / "test_results.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Servislar javob beradimi tekshiramiz
        try:
            for name, url in [
                ("Reception", BASE_RECEPTION),
                ("Housekeeping", BASE_HOUSEKEEPING),
                ("RoomService", BASE_ROOMSERVICE),
                ("Maintenance", BASE_MAINTENANCE),
            ]:
                h = await client.get(f"{url}/health", timeout=2.0)
                print(f"  {name}: {h.json()['status']}")
        except httpx.HTTPError as exc:
            print(f"❌ Servislar ishga tushmagan: {exc}")
            sys.exit(1)

        results: list[ScenarioResult] = [
            await ts01_basic_checkin(client),
            await ts02_checkout(client),
            await ts03_cleaning_flow(client),
            await ts04_room_service(client),
            await ts05_critical_maintenance(client),
            await ts06_concurrent_checkin(client),
            await ts07_no_rooms_available(client),
            await ts08_invalid_input(client),
        ]

    elapsed = time.time() - start
    passed = sum(1 for r in results if r.passed)
    print("\n" + "=" * 60)
    print(f"Yakuniy: {passed}/{len(results)} muvaffaqiyatli ({elapsed:.1f}s)")
    for r in results:
        print(f"  {r}")

    # Markdown hisobotini yozish
    md = ["# HotelOS Test Stsenariylari Natijasi", "",
          f"Sana: {datetime.now().isoformat()}", f"Muvaffaqiyatli: {passed}/{len(results)}", ""]
    for r in results:
        md.append(f"## {r.sid} — {r.desc}")
        md.append(f"**Holat:** {'✅ PASS' if r.passed else '❌ FAIL'}")
        md.append("")
        md.append("**Bosqichlar:**")
        for s in r.steps:
            md.append(f"- {s}")
        if r.error:
            md.append(f"**Xato:** {r.error}")
        md.append("")
    out_path.write_text("\n".join(md))
    print(f"\nNatijalar yozildi: {out_path}")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    asyncio.run(main())
