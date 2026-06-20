"""Video subtitle/metadata extraction engine using yt-dlp."""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any

from ..base import BaseEngine, Capability, FetchResult

logger = logging.getLogger(__name__)


class VideoExtractEngine(BaseEngine):
    """Extract subtitles, metadata, and description from video URLs.

    Uses yt-dlp (installed separately). Supports YouTube, Bilibili, 
    and other sites supported by yt-dlp.
    """

    name = "video-extract"
    capabilities = {Capability.FETCH}

    def __init__(self) -> None:
        super().__init__()
        self._ytdlp_bin = os.environ.get("YTDLP_BIN", "yt-dlp")

    async def fetch(self, url: str, *, timeout: int | None = None, **kwargs: Any) -> FetchResult:
        import asyncio, json

        cmd = [
            self._ytdlp_bin,
            "--skip-download",
            "--write-auto-subs",
            "--sub-lang", kwargs.get("lang", "en,zh,ja"),
            "--sub-format", "vtt/txt",
            "--convert-subs", "txt",
            "--print", "after_video:%(title)s",
            "--print", "after_video:%(description)s",
            "--print", "after_video:%(duration)s",
            "--print", "after_video:%(view_count)s",
            "--print", "after_video:%(like_count)s",
            "--no-warnings",
            url,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                timeout=timeout or 60,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout or 60)
            if proc.returncode != 0:
                return FetchResult(ok=False, url=url, engine=self.name, error=f"yt-dlp failed: {stderr.decode()[:300]}")

            lines = stdout.decode().strip().split("\n")
            if not lines:
                return FetchResult(ok=False, url=url, engine=self.name, error="No output from yt-dlp")

            metadata = {"title": lines[0] if len(lines) > 0 else ""}
            text_parts = []

            # Title
            if len(lines) > 0:
                text_parts.append(f"# {lines[0]}")
            # Description
            if len(lines) > 1 and lines[1]:
                text_parts.append(f"\n## Description\n{lines[1]}")
            # Stats
            if len(lines) > 2 and lines[2]:
                text_parts.append(f"\nDuration: {int(lines[2])//60}m {int(lines[2])%60}s")
            if len(lines) > 3 and lines[3]:
                text_parts.append(f"Views: {lines[3]}")
            if len(lines) > 4 and lines[4]:
                metadata["likes"] = lines[4]

            # Find subtitle files
            for fname in os.listdir("."):
                if fname.endswith(".txt") and url.split("/")[-1] in fname:
                    with open(fname, "r") as sf:
                        subs = sf.read()
                    if subs.strip():
                        text_parts.append(f"\n## Subtitles\n{subs[:10000]}")
                    os.unlink(fname)

            text = "\n".join(text_parts)
            return FetchResult(ok=True, url=url, engine=self.name, text=text, quality_score=0.8, metadata=metadata)

        except asyncio.TimeoutError:
            return FetchResult(ok=False, url=url, engine=self.name, error=f"yt-dlp timed out after {timeout or 60}s")
        except FileNotFoundError:
            return FetchResult(ok=False, url=url, engine=self.name, error=f"yt-dlp binary not found. Install: winget install yt-dlp or pip install yt-dlp")
        except Exception as exc:
            return FetchResult(ok=False, url=url, engine=self.name, error=f"Video extraction failed: {exc}")
