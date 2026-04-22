"""Structured output and persistence — independent of fetch rings."""
from __future__ import annotations
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any


def _default_output_dir() -> Path:
    base = os.environ.get("OUTPUT_DIR", "")
    if base:
        return Path(base)
    # Relative to this file's project root
    return Path(__file__).parent.parent / "outputs"


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_json(data: Any, *, prefix: str = "result", output_dir: Path | None = None) -> str:
    """Save data as JSON. Returns the file path."""
    out_dir = _ensure_dir(output_dir or _default_output_dir())
    filename = f"{prefix}_{int(time.time())}_{uuid.uuid4().hex[:8]}.json"
    path = out_dir / filename
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def save_markdown(
    records: list[dict],
    *,
    query: str = "",
    prefix: str = "research",
    output_dir: Path | None = None,
) -> str:
    """Save records as structured Markdown. Returns the file path."""
    out_dir = _ensure_dir(output_dir or _default_output_dir())
    filename = f"{prefix}_{int(time.time())}_{uuid.uuid4().hex[:8]}.md"
    path = out_dir / filename

    lines: list[str] = []
    if query:
        lines += [f"# Research: {query}", "", f"*Generated: {_now_iso()}*", ""]
    for i, rec in enumerate(records, 1):
        title = rec.get("title", "Untitled")
        url = rec.get("url", "")
        text = rec.get("text", "").strip()
        quality = rec.get("quality", 0)
        engine = rec.get("engine", "")
        lines += [
            f"## {i}. {title}",
            f"**URL**: {url}  ",
            f"**Quality**: {quality:.2f}  **Engine**: {engine}",
            "",
            text[:3000] + ("..." if len(text) > 3000 else ""),
            "",
            "---",
            "",
        ]

    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def save_ndjson(records: list[dict], *, prefix: str = "stream",
                output_dir: Path | None = None) -> str:
    """Save records as NDJSON (one JSON per line). Returns file path."""
    out_dir = _ensure_dir(output_dir or _default_output_dir())
    filename = f"{prefix}_{int(time.time())}_{uuid.uuid4().hex[:8]}.ndjson"
    path = out_dir / filename
    lines = [json.dumps(r, ensure_ascii=False) for r in records]
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def save(
    data: Any,
    *,
    format: str = "json",
    prefix: str = "result",
    query: str = "",
    output_dir: Path | None = None,
) -> list[str]:
    """Save in one or more formats. Returns list of file paths."""
    paths: list[str] = []
    formats = [f.strip() for f in format.split(",")]

    for fmt in formats:
        if fmt == "json":
            if isinstance(data, dict):
                paths.append(save_json(data, prefix=prefix, output_dir=output_dir))
            elif isinstance(data, list):
                paths.append(save_json({"records": data}, prefix=prefix, output_dir=output_dir))
        elif fmt == "md" or fmt == "markdown":
            records = data if isinstance(data, list) else data.get("records", [data])
            paths.append(save_markdown(records, query=query, prefix=prefix, output_dir=output_dir))
        elif fmt == "ndjson":
            records = data if isinstance(data, list) else data.get("records", [data])
            paths.append(save_ndjson(records, prefix=prefix, output_dir=output_dir))

    return paths


def _now_iso() -> str:
    import datetime
    return datetime.datetime.now().isoformat(timespec="seconds")
