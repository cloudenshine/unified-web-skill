"""frontier.py — 优先队列 + 幂等去重"""
import heapq
import itertools
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Candidate:
    url: str
    score: float = 0.5
    depth: int = 0
    meta: dict = field(default_factory=dict)

    @property
    def canonical_url(self) -> str:
        # Strip fragment
        return self.url.split("#")[0].rstrip("/")


@dataclass(order=True)
class FrontierItem:
    priority: float        # negative score (min-heap → max score first)
    seq: int               # tiebreaker
    candidate: Any = field(compare=False)


class Frontier:
    def __init__(self, already_fetched: set[str] | None = None):
        self._heap: list[FrontierItem] = []
        self._counter = itertools.count()
        self._seen: set[str] = set(already_fetched or [])

    def push(self, candidate: Candidate) -> bool:
        """Add candidate. Returns False if already seen (idempotent)."""
        url = candidate.canonical_url
        if url in self._seen:
            return False
        self._seen.add(url)
        heapq.heappush(
            self._heap,
            FrontierItem(-candidate.score, next(self._counter), candidate)
        )
        return True

    def pop(self) -> Candidate | None:
        if not self._heap:
            return None
        return heapq.heappop(self._heap).candidate

    def __len__(self) -> int:
        return len(self._heap)

    def seen_count(self) -> int:
        return len(self._seen)

    def is_empty(self) -> bool:
        return len(self._heap) == 0
