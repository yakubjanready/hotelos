"""Ustuvorlik navbat algoritmi uchun testlar."""

from __future__ import annotations

from maintenance_service.priority_queue import IssuePriorityQueue
from shared.enums import IssueUrgency


def _push(q: IssuePriorityQueue, iid: str, urgency: IssueUrgency) -> None:
    q.push(iid, urgency, {"issue_id": iid, "urgency": urgency.value})


def test_critical_before_high():
    q = IssuePriorityQueue()
    _push(q, "I-1", IssueUrgency.HIGH)
    _push(q, "I-2", IssueUrgency.CRITICAL)
    _push(q, "I-3", IssueUrgency.NORMAL)
    assert q.pop()["issue_id"] == "I-2"
    assert q.pop()["issue_id"] == "I-1"
    assert q.pop()["issue_id"] == "I-3"


def test_fifo_within_same_urgency():
    """Brief talabi: bir xil shoshilinchlikda avval topshirilgani ustunlik oladi."""
    q = IssuePriorityQueue()
    _push(q, "I-1", IssueUrgency.NORMAL)
    _push(q, "I-2", IssueUrgency.NORMAL)
    _push(q, "I-3", IssueUrgency.NORMAL)
    assert q.pop()["issue_id"] == "I-1"
    assert q.pop()["issue_id"] == "I-2"
    assert q.pop()["issue_id"] == "I-3"


def test_empty_queue_returns_none():
    q = IssuePriorityQueue()
    assert q.pop() is None
    assert q.peek() is None


def test_cancel_removes_from_queue():
    q = IssuePriorityQueue()
    _push(q, "I-1", IssueUrgency.CRITICAL)
    _push(q, "I-2", IssueUrgency.HIGH)
    q.cancel("I-1")
    assert q.pop()["issue_id"] == "I-2"
    assert q.pop() is None


def test_mixed_priorities_complex_order():
    q = IssuePriorityQueue()
    _push(q, "A", IssueUrgency.LOW)
    _push(q, "B", IssueUrgency.HIGH)
    _push(q, "C", IssueUrgency.CRITICAL)
    _push(q, "D", IssueUrgency.HIGH)
    _push(q, "E", IssueUrgency.LOW)
    _push(q, "F", IssueUrgency.CRITICAL)
    # Kutilgan tartib: C, F (Critical FIFO), B, D (High FIFO), A, E (Low FIFO)
    order = [q.pop()["issue_id"] for _ in range(6)]
    assert order == ["C", "F", "B", "D", "A", "E"]
