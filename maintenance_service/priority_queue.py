"""
Texnik xizmat ustuvorlik navbati.

`heapq` (min-heap) asosida amalga oshirilgan. Heap kalit:
    (priority_value, sequence_number, issue_id)

`priority_value` — IssueUrgency.priority_value() (past raqam = yuqori ustuvorlik).
`sequence_number` — submission tartibi (bir xil ustuvorlikda FIFO tiebreaker uchun
zarur, brief talabi: "bir xil shoshilinchlikda avval topshirilgani ustunlik").
`issue_id` — yakuniy aniq tartiblash uchun (deterministik chiqish).

Murakkablik:
    push   — O(log n)
    pop    — O(log n)
    peek   — O(1)
"""

from __future__ import annotations

import heapq
import itertools
import threading
from dataclasses import dataclass, field
from typing import Optional

from shared.enums import IssueUrgency


@dataclass(order=True)
class _HeapEntry:
    """Ichki heap yozuvi — solishtirish uchun tartibga rioya qiladi.

    `field(compare=False)` issue_data ni solishtirishdan chiqaradi —
    faqat ustuvorlik va ketma-ketlik solishtiriladi.
    """

    priority: int
    sequence: int
    issue_id: str
    issue_data: dict = field(compare=False)


class IssuePriorityQueue:
    """Texnik xizmat so'rovlari uchun thread-safe ustuvorlik navbati."""

    def __init__(self) -> None:
        self._heap: list[_HeapEntry] = []
        self._counter = itertools.count()
        self._lock = threading.RLock()
        self._removed: set[str] = set()  # "lazy delete" qilingan ID lar

    def push(self, issue_id: str, urgency: IssueUrgency, issue_data: dict) -> None:
        """Yangi so'rovni navbatga qo'shadi."""
        entry = _HeapEntry(
            priority=urgency.priority_value(),
            sequence=next(self._counter),
            issue_id=issue_id,
            issue_data=issue_data,
        )
        with self._lock:
            heapq.heappush(self._heap, entry)

    def pop(self) -> Optional[dict]:
        """Eng yuqori ustuvorlikdagi so'rovni oladi va heap'dan olib tashlaydi.

        Bir xil ustuvorlikda eng erta topshirilgan birinchi keladi (FIFO).
        """
        with self._lock:
            while self._heap:
                entry = heapq.heappop(self._heap)
                if entry.issue_id in self._removed:
                    self._removed.discard(entry.issue_id)
                    continue
                return entry.issue_data
            return None

    def peek(self) -> Optional[dict]:
        """Eng yuqori ustuvorlikdagi so'rovni olib tashlamasdan ko'rsatadi."""
        with self._lock:
            while self._heap:
                top = self._heap[0]
                if top.issue_id in self._removed:
                    heapq.heappop(self._heap)
                    self._removed.discard(top.issue_id)
                    continue
                return top.issue_data
            return None

    def cancel(self, issue_id: str) -> bool:
        """So'rovni "lazy delete" qiladi — chiqarganda o'tkazib yuboriladi."""
        with self._lock:
            self._removed.add(issue_id)
            return True

    def snapshot(self) -> list[dict]:
        """Navbat holatini ustuvorlik tartibida nusxa sifatida qaytaradi."""
        with self._lock:
            valid = [e for e in sorted(self._heap) if e.issue_id not in self._removed]
            return [e.issue_data for e in valid]

    def __len__(self) -> int:
        with self._lock:
            return sum(1 for e in self._heap if e.issue_id not in self._removed)
