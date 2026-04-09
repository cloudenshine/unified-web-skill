"""Engine protocol, data models, and base class for unified-web-skill v3.0.

This module defines the contract every engine adapter must satisfy, the
shared data-transfer objects returned by engine operations, and a
convenience ``BaseEngine`` ABC that supplies default (raising)
implementations so concrete adapters only override what they support.

No external dependencies — stdlib only.
"""

from __future__ import annotations

import abc
import asyncio
import contextlib
import enum
import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Capability enum
# ---------------------------------------------------------------------------

class Capability(enum.Enum):
    """Advertised capabilities an engine may support."""

    FETCH = "fetch"            # Can fetch a URL and return content
    SEARCH = "search"          # Can search by query
    INTERACT = "interact"      # Can do browser interactions (click, fill, login)
    CRAWL = "crawl"            # Can crawl multiple pages
    STRUCTURED = "structured"  # Returns structured/JSON data natively


# ---------------------------------------------------------------------------
# Data-transfer objects
# ---------------------------------------------------------------------------

@dataclass
class FetchResult:
    """Outcome of fetching a single URL."""

    ok: bool
    url: str
    status: int = 0
    text: str = ""
    html: str = ""
    title: str = ""
    engine: str = ""
    route: str = ""              # e.g. "opencli:bilibili/hot"
    duration_ms: float = 0.0
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""

    def compute_hash(self) -> str:
        """Compute and cache a SHA-256 hex digest of *text*."""
        self.content_hash = hashlib.sha256(self.text.encode()).hexdigest()
        return self.content_hash


@dataclass
class SearchResult:
    """A single hit returned by a search engine."""

    url: str
    title: str
    snippet: str = ""
    source: str = ""             # search engine name
    rank: int = 0
    credibility: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class InteractResult:
    """Outcome of a browser-interaction session."""

    ok: bool
    url: str
    engine: str = ""
    text: str = ""
    snapshot: str = ""           # base64 screenshot if available
    instance_id: str = ""        # for session reuse
    error: str = ""
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Engine protocol (structural typing)
# ---------------------------------------------------------------------------

@runtime_checkable
class Engine(Protocol):
    """Structural protocol every engine adapter must satisfy.

    Concrete classes do **not** need to inherit from this protocol; they
    only need to expose the same attributes and method signatures.  Use
    ``isinstance(obj, Engine)`` at runtime to verify conformance.
    """

    @property
    def name(self) -> str:
        """Unique, lowercase identifier for this engine (e.g. ``"scrapling"``)."""
        ...

    @property
    def capabilities(self) -> set[Capability]:
        """Set of :class:`Capability` values this engine supports."""
        ...

    async def health_check(self) -> bool:
        """Return ``True`` if the engine is available and ready."""
        ...

    async def fetch(
        self,
        url: str,
        *,
        timeout: int = 30,
        **opts: Any,
    ) -> FetchResult:
        """Fetch content from *url*."""
        ...

    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        language: str = "zh",
        **opts: Any,
    ) -> list[SearchResult]:
        """Search by *query*.  Raise ``NotImplementedError`` if unsupported."""
        ...

    async def interact(
        self,
        url: str,
        actions: list[dict[str, Any]],
        *,
        timeout: int = 60,
        **opts: Any,
    ) -> InteractResult:
        """Perform browser interactions.  Raise ``NotImplementedError`` if unsupported."""
        ...


# ---------------------------------------------------------------------------
# Timing helper
# ---------------------------------------------------------------------------

@contextlib.asynccontextmanager
async def _timed():
    """Async context manager that yields a callable returning elapsed ms.

    Usage::

        async with _timed() as elapsed:
            ...  # do work
        print(elapsed())  # milliseconds as float
    """
    t0 = time.perf_counter()
    container: list[float] = [0.0]

    def _elapsed() -> float:
        return container[0]

    try:
        yield _elapsed
    finally:
        container[0] = (time.perf_counter() - t0) * 1000.0


# ---------------------------------------------------------------------------
# BaseEngine ABC — convenience base class
# ---------------------------------------------------------------------------

class BaseEngine(abc.ABC):
    """Abstract base class providing default (raising) implementations.

    Concrete adapters should subclass this and override only the methods
    matching their declared :pyattr:`capabilities`.  The timing context
    manager :meth:`_timed` is available for convenience.
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(f"engine.{self.name}")

    # -- abstract properties -------------------------------------------------

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique lowercase identifier."""

    @property
    @abc.abstractmethod
    def capabilities(self) -> set[Capability]:
        """Capabilities this engine supports."""

    # -- default implementations ---------------------------------------------

    async def health_check(self) -> bool:
        """Optimistic default — override with real connectivity checks."""
        return True

    async def fetch(
        self,
        url: str,
        *,
        timeout: int = 30,
        **opts: Any,
    ) -> FetchResult:
        """Default: return an error result for engines that don't support fetch."""
        if Capability.FETCH not in self.capabilities:
            return FetchResult(
                ok=False,
                url=url,
                engine=self.name,
                error=f"Engine '{self.name}' does not support FETCH",
            )
        raise NotImplementedError(
            f"{self.__class__.__name__}.fetch() not implemented"
        )

    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        language: str = "zh",
        **opts: Any,
    ) -> list[SearchResult]:
        """Default: raise for engines that don't support search."""
        raise NotImplementedError(
            f"Engine '{self.name}' does not support SEARCH"
        )

    async def interact(
        self,
        url: str,
        actions: list[dict[str, Any]],
        *,
        timeout: int = 60,
        **opts: Any,
    ) -> InteractResult:
        """Default: return an error result for engines that don't support interact."""
        if Capability.INTERACT not in self.capabilities:
            return InteractResult(
                ok=False,
                url=url,
                engine=self.name,
                error=f"Engine '{self.name}' does not support INTERACT",
            )
        raise NotImplementedError(
            f"{self.__class__.__name__}.interact() not implemented"
        )

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _timed():
        """Return the async timing context manager.

        Usage inside a concrete adapter::

            async with self._timed() as elapsed:
                result = await self._do_work(url)
            result.duration_ms = elapsed()
        """
        return _timed()

    async def _run_subprocess(
        self, cmd: list[str], *, timeout: int = 30
    ) -> tuple[int, str, str]:
        """Run a subprocess with timeout protection. Returns (returncode, stdout, stderr).

        On Windows, automatically resolves npm-style `.cmd` wrappers when a bare
        binary name is supplied (e.g. ``bb-browser`` → ``bb-browser.cmd``).
        """
        import shutil
        import sys

        resolved_cmd = list(cmd)
        binary = resolved_cmd[0]

        # On Windows, bare binary names from npm need .cmd extension
        if sys.platform == "win32" and not os.path.isabs(binary):
            # Try to find the .cmd wrapper
            for ext in (".cmd", ".bat", ".exe", ""):
                found = shutil.which(binary + ext)
                if found:
                    resolved_cmd[0] = found
                    break

        proc: asyncio.subprocess.Process | None = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *resolved_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return (
                proc.returncode or 0,
                stdout.decode("utf-8", errors="replace"),
                stderr.decode("utf-8", errors="replace"),
            )
        except asyncio.TimeoutError:
            if proc:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
            return 75, "", "timeout"
        except FileNotFoundError:
            return 78, "", f"binary not found: {cmd[0]}"
        except Exception as exc:
            return 1, "", str(exc)

    def __repr__(self) -> str:
        caps = ", ".join(sorted(c.value for c in self.capabilities))
        return f"<{self.__class__.__name__} name={self.name!r} caps=[{caps}]>"
