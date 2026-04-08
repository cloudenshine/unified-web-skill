"""Common fixtures for unit tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.engines.base import Capability, FetchResult, SearchResult, InteractResult, BaseEngine


class StubEngine(BaseEngine):
    """Minimal concrete engine for testing."""

    def __init__(self, name: str = "stub", caps: set[Capability] | None = None):
        self._name = name
        self._caps = caps or {Capability.FETCH}
        super().__init__()

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> set[Capability]:
        return self._caps

    async def fetch(self, url, *, timeout=30, **opts):
        return FetchResult(ok=True, url=url, text="stub content", engine=self._name)

    async def search(self, query, *, max_results=10, language="zh", **opts):
        return [SearchResult(url=f"https://example.com/{i}", title=f"Result {i}", source=self._name) for i in range(min(3, max_results))]

    async def interact(self, url, actions, *, timeout=60, **opts):
        return InteractResult(ok=True, url=url, engine=self._name, text="interacted")


class FailingEngine(BaseEngine):
    """Engine that always fails."""

    def __init__(self, name: str = "failing"):
        self._name = name
        super().__init__()

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> set[Capability]:
        return {Capability.FETCH, Capability.SEARCH}

    async def fetch(self, url, *, timeout=30, **opts):
        return FetchResult(ok=False, url=url, engine=self._name, error="always fails")

    async def search(self, query, *, max_results=10, language="zh", **opts):
        raise RuntimeError("search always fails")


@pytest.fixture
def stub_engine():
    return StubEngine()


@pytest.fixture
def failing_engine():
    return FailingEngine()


@pytest.fixture
def fetch_engine():
    return StubEngine("fetcher", {Capability.FETCH})


@pytest.fixture
def search_engine():
    return StubEngine("searcher", {Capability.FETCH, Capability.SEARCH})


@pytest.fixture
def interact_engine():
    return StubEngine("interactor", {Capability.FETCH, Capability.INTERACT})
