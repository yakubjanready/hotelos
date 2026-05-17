"""
Maintenance Servisi — texnik xizmat so'rovlari va texniklar tayinlash.

Texniklar /claim endpointi orqali keyingi eng yuqori ustuvorlikdagi muammoni
oladi. Ichkarida `IssuePriorityQueue` ishlatiladi (heap asosli).
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from maintenance_service.priority_queue import IssuePriorityQueue
from shared.broker import MessageBroker, build_broker
from shared.config import get_settings
from shared.enums import IssueStatus, IssueUrgency
from shared.events import EVT_ISSUE_ASSIGNED, EVT_ISSUE_REPORTED, EVT_ISSUE_RESOLVED
from shared.models import MaintenanceIssue
from shared.security import InputValidator, ValidationError

logger = logging.getLogger("hotelos.maintenance")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


class IssueReportRequest(BaseModel):
    room_number: int = Field(..., ge=100, le=699)
    description: str = Field(..., min_length=3, max_length=500)
    urgency: IssueUrgency


class TechnicianPool:
    """Mavjud texniklar pulasi — round-robin tayinlash uchun."""

    def __init__(self, names: list[str]) -> None:
        if not names:
            raise ValueError("Texniklar ro'yxati bo'sh bo'lmasligi kerak")
        self._pool: deque[str] = deque(names)
        self._lock = threading.Lock()

    def next_available(self) -> str:
        with self._lock:
            tech = self._pool[0]
            self._pool.rotate(-1)
            return tech


queue = IssuePriorityQueue()
issues_by_id: dict[str, MaintenanceIssue] = {}
state_lock = threading.RLock()
tech_pool = TechnicianPool(["Aziz Karimov", "Dilshod Yusupov", "Sherzod Rakhimov"])
broker: MessageBroker | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global broker
    settings = get_settings()
    broker = build_broker(
        use_in_memory=settings.use_in_memory_broker,
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
    )
    await broker.connect()
    listener = asyncio.create_task(broker.start_listening())
    try:
        yield
    finally:
        listener.cancel()
        await broker.disconnect()


app = FastAPI(title="HotelOS Maintenance Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "maintenance", "open_issues": len(queue)}


@app.get("/issues")
async def list_issues() -> list[dict]:
    """Joriy ochiq muammolar — panel uchun ustuvorlik tartibida."""
    return queue.snapshot()


@app.post("/issues", status_code=201)
async def report_issue(req: IssueReportRequest) -> dict:
    """Yangi muammo qayd etish — priority queue ga qo'shiladi."""
    try:
        room_number = InputValidator.validate_room_number(req.room_number)
        description = InputValidator.validate_description(req.description)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    issue = MaintenanceIssue(
        room_number=room_number,
        description=description,
        urgency=req.urgency,
    )
    with state_lock:
        issues_by_id[issue.issue_id] = issue

    queue.push(
        issue_id=issue.issue_id,
        urgency=issue.urgency,
        issue_data={
            "issue_id": issue.issue_id,
            "room_number": issue.room_number,
            "description": issue.description,
            "urgency": issue.urgency.value,
            "status": issue.status.value,
            "reported_at": issue.reported_at.isoformat(),
        },
    )

    assert broker is not None
    await broker.publish(
        EVT_ISSUE_REPORTED,
        {
            "issue_id": issue.issue_id,
            "room_number": issue.room_number,
            "urgency": issue.urgency.value,
            "description": issue.description,
            "timestamp": issue.reported_at.isoformat(),
        },
    )
    return {"issue_id": issue.issue_id, "status": issue.status.value, "queued": True}


@app.post("/claim")
async def claim_next_issue() -> dict:
    """Keyingi texnik eng yuqori ustuvorlikdagi muammoni oladi."""
    next_issue = queue.pop()
    if next_issue is None:
        raise HTTPException(status_code=404, detail="Navbatda muammo yo'q")

    technician = tech_pool.next_available()
    issue_id = next_issue["issue_id"]
    with state_lock:
        issue = issues_by_id[issue_id]
        issue.status = IssueStatus.ASSIGNED
        issue.assigned_technician = technician

    assert broker is not None
    await broker.publish(
        EVT_ISSUE_ASSIGNED,
        {
            "issue_id": issue_id,
            "room_number": next_issue["room_number"],
            "urgency": next_issue["urgency"],
            "technician": technician,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {"issue_id": issue_id, "technician": technician, "status": IssueStatus.ASSIGNED.value}


@app.post("/issues/{issue_id}/resolve")
async def resolve_issue(issue_id: str) -> dict:
    """Texnik muammoni hal etilgan deb belgilaydi."""
    with state_lock:
        issue = issues_by_id.get(issue_id)
        if issue is None:
            raise HTTPException(status_code=404, detail="Muammo topilmadi")
        if issue.status == IssueStatus.RESOLVED:
            raise HTTPException(status_code=409, detail="Allaqachon hal etilgan")
        issue.status = IssueStatus.RESOLVED
        issue.resolved_at = datetime.now(timezone.utc)

    assert broker is not None
    await broker.publish(
        EVT_ISSUE_RESOLVED,
        {
            "issue_id": issue_id,
            "room_number": issue.room_number,
            "technician": issue.assigned_technician,
            "timestamp": issue.resolved_at.isoformat(),
        },
    )
    return {"issue_id": issue_id, "status": issue.status.value}


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "maintenance_service.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.maintenance_port,
        reload=False,
    )
