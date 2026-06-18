"""Jina Reader API engine — hosted content extraction via HTTP API.

Uses https://r.jina.ai to fetch URL content in markdown format.
Free tier: 1,000 requests/month. Requires JINA_API_KEY environment variable.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from ..base import BaseEngine, Capability, FetchResult

logger = logging.getLogger(__name__)

API_KEY_ENV = "JINA_API_KEY"
BASE_URL = "https://r.jina.ai"
TIMEOUT = 60


class JinaReaderEngine(BaseEngine):
    """Engine wrapping the Jina Reader API (r.jina.ai) for content extraction."""

    name = "jina-reader"
    capabilities = {Capability.FETCH}

    def __init__(self) -> None:
        self._api_key = os.environ.get(API_KEY_ENV, "")

    # ── BaseEngine abstract methods ──────────────────────────────────

    def health_check(self) -> bool:
        """Return True if the API key is configured and the endpoint is reachable."""
        if not self._api_key:
            logger.debug("Jina Reader: no API key set")
            return False
        try:
            resp = httpx.get(f"{BASE_URL}/", timeout=10)
            return resp.status_code < 500
        except httpx.HTTPError:
            return False

    async def fetch(
        self,
        url: str,
        *,
        timeout: int | None = None,
        **kwargs: Any,
    ) -> FetchResult:
        if not self._api_key:
            return FetchResult(
                ok=False,
                url=url,
                text="",
                error=f"Jina Reader API key not set. Set {API_KEY_ENV} env var.",
            )

        target_url = f"{BASE_URL}/{url}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "text/plain",
            "X-Respond-With": "markdown",
        }

        try:
            async with httpx.AsyncClient(timeout=timeout or TIMEOUT) as client:
                resp = await client.get(target_url, headers=headers)
                resp.raise_for_status()
                text = resp.text
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            detail = exc.response.text[:200] if exc.response.text else ""
            return FetchResult(
                ok=False,
                url=url,
                text="",
                error=f"Jina Reader HTTP {status}: {detail}",
                status_code=status,
            )
        except httpx.RequestError as exc:
            return FetchResult(
                ok=False,
                url=url,
                text="",
                error=f"Jina Reader request failed: {exc}",
            )

        if not text or len(text.strip()) < 50:
            return FetchResult(
                ok=False,
                url=url,
                text=text or "",
                error="Jina Reader returned empty or too-short content",
            )

        return FetchResult(ok=True, url=url, text=text)

    def version_info(self) -> dict[str, str]:
        return {"engine": "jina-reader", "version": "1.0", "api": BASE_URL}
