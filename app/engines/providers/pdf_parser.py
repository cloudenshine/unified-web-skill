"""PDF parsing engine using pdfplumber."""

from __future__ import annotations

import logging
from typing import Any

from ..base import BaseEngine, Capability, FetchResult

logger = logging.getLogger(__name__)


class PDFParserEngine(BaseEngine):
    """Extract text content from PDF files."""

    name = "pdf-parser"
    capabilities = {Capability.FETCH}

    async def fetch(self, url: str, *, timeout: int | None = None, **kwargs: Any) -> FetchResult:
        try:
            import pdfplumber
        except ImportError:
            return FetchResult(ok=False, url=url, engine=self.name, error="pdfplumber not installed")

        import httpx, tempfile, os
        try:
            async with httpx.AsyncClient(timeout=timeout or 30, follow_redirects=True) as client:
                resp = await client.get(url)
            resp.raise_for_status()
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            try:
                tmp.write(resp.content)
                tmp.close()
                text_parts = []
                with pdfplumber.open(tmp.name) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            text_parts.append(t)
            finally:
                os.unlink(tmp.name)
            text = "\n\n".join(text_parts)
            if not text or len(text.strip()) < 20:
                return FetchResult(ok=False, url=url, engine=self.name, error="PDF appears empty or scanned (no extractable text)")
            return FetchResult(ok=True, url=url, engine=self.name, text=text, quality_score=0.75, metadata={"source": "pdf", "pages": len(text_parts)})
        except httpx.HTTPStatusError as exc:
            return FetchResult(ok=False, url=url, engine=self.name, error=f"HTTP {exc.response.status_code}: {exc.response.text[:200]}")
        except Exception as exc:
            return FetchResult(ok=False, url=url, engine=self.name, error=f"PDF extraction failed: {exc}")
