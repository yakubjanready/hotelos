"""
HotelOS Terminal Monitor.

`rich` kutubxonasi asosida terminalda jonli yangilanadigan ko'rinish. Dashboard
servisining REST `/state` endpointidan har 1 soniyada holatni so'raydi va
formatlangan jadvallarda chiqaradi.

Ishga tushirish:
    python -m terminal_monitor.monitor --token <JWT>

Yoki avtomatik login (developmnent):
    python -m terminal_monitor.monitor --login admin:admin123
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime

import httpx
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from shared.config import get_settings


def build_layout() -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )
    layout["body"].split_row(
        Layout(name="left", ratio=2),
        Layout(name="right", ratio=1),
    )
    layout["right"].split_column(
        Layout(name="orders"),
        Layout(name="issues"),
    )
    return layout


def render_rooms_table(rooms: list[dict]) -> Table:
    table = Table(title="Xonalar (qavat bo'yicha guruhlangan)", expand=True)
    table.add_column("Qavat", justify="center")
    table.add_column("Toza", justify="right", style="green")
    table.add_column("Band", justify="right", style="blue")
    table.add_column("Iflos", justify="right", style="yellow")
    table.add_column("Tozalanmoqda", justify="right", style="magenta")
    table.add_column("Texnik", justify="right", style="red")
    table.add_column("Jami", justify="right", style="bold")

    floors: dict[int, dict[str, int]] = {}
    for room in rooms:
        f = room.get("floor")
        st = room.get("status", "clean")
        floors.setdefault(f, {}).setdefault(st, 0)
        floors[f][st] += 1

    for floor in sorted(floors.keys(), reverse=True):
        counts = floors[floor]
        total = sum(counts.values())
        table.add_row(
            str(floor),
            str(counts.get("clean", 0)),
            str(counts.get("occupied", 0)),
            str(counts.get("dirty", 0)),
            str(counts.get("cleaning", 0)),
            str(counts.get("maintenance", 0)),
            str(total),
        )
    return table


def render_orders_table(orders: list[dict]) -> Table:
    table = Table(title="Faol buyurtmalar", expand=True)
    table.add_column("Buyurtma", style="cyan")
    table.add_column("Xona", justify="right")
    table.add_column("Holat")
    table.add_column("Jami", justify="right")
    if not orders:
        table.add_row("—", "—", "[dim]bo'sh[/dim]", "—")
        return table
    for o in orders[:10]:
        table.add_row(
            o.get("order_id", "")[:12],
            str(o.get("room_number", "")),
            o.get("status", ""),
            str(o.get("total", "")),
        )
    return table


def render_issues_table(issues: list[dict]) -> Table:
    table = Table(title="Texnik muammolar (ustuvorlik tartibida)", expand=True)
    table.add_column("Shoshilinch")
    table.add_column("Xona", justify="right")
    table.add_column("Tavsif", overflow="fold")
    table.add_column("Texnik")
    if not issues:
        table.add_row("—", "—", "[dim]ochiq muammo yo'q[/dim]", "—")
        return table
    urgency_style = {"critical": "bold red", "high": "yellow", "normal": "blue", "low": "dim"}
    for i in issues[:10]:
        u = i.get("urgency", "normal")
        table.add_row(
            Text(u.upper(), style=urgency_style.get(u, "white")),
            str(i.get("room_number", "")),
            i.get("description", ""),
            i.get("technician") or "—",
        )
    return table


async def login(client: httpx.AsyncClient, base_url: str, creds: str) -> str:
    user, pwd = creds.split(":", 1)
    resp = await client.post(f"{base_url}/login", json={"username": user, "password": pwd})
    resp.raise_for_status()
    return resp.json()["token"]


async def fetch_state(client: httpx.AsyncClient, base_url: str, token: str) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get(f"{base_url}/state", headers=headers)
    resp.raise_for_status()
    return resp.json()


async def run(token: str | None, login_creds: str | None) -> None:
    settings = get_settings()
    base = f"http://localhost:{settings.dashboard_port}"
    console = Console()
    layout = build_layout()

    async with httpx.AsyncClient(timeout=5.0) as client:
        if token is None and login_creds:
            token = await login(client, base, login_creds)
        if token is None:
            console.print("[red]Token kerak — --token yoki --login bilan bering[/red]")
            sys.exit(1)

        with Live(layout, console=console, refresh_per_second=2, screen=True) as live:
            while True:
                try:
                    snapshot = await fetch_state(client, base, token)
                except httpx.HTTPError as exc:
                    layout["footer"].update(Panel(Text(f"Xato: {exc}", style="red")))
                    await asyncio.sleep(1)
                    continue

                now = datetime.now().strftime("%H:%M:%S")
                layout["header"].update(
                    Panel(
                        Text(f"HotelOS Terminal Monitor — yangilangan {now}", style="bold cyan"),
                        border_style="cyan",
                    )
                )
                layout["left"].update(render_rooms_table(snapshot.get("rooms", [])))
                layout["orders"].update(render_orders_table(snapshot.get("orders", [])))
                layout["issues"].update(render_issues_table(snapshot.get("issues", [])))
                layout["footer"].update(
                    Panel(
                        Text(
                            f"Jami: {len(snapshot.get('rooms', []))} xona, "
                            f"{len(snapshot.get('orders', []))} buyurtma, "
                            f"{len(snapshot.get('issues', []))} muammo",
                            style="dim",
                        )
                    )
                )
                live.refresh()
                await asyncio.sleep(1.0)


def main() -> None:
    parser = argparse.ArgumentParser(description="HotelOS Terminal Monitor")
    parser.add_argument("--token", help="JWT token")
    parser.add_argument("--login", help="user:password (avtomatik login)")
    args = parser.parse_args()
    try:
        asyncio.run(run(args.token, args.login))
    except KeyboardInterrupt:
        print("\nMonitor to'xtatildi.")


if __name__ == "__main__":
    main()
