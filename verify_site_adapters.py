"""Run live verification for selected bb-browser site adapters."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from app.discovery.adapter_verifier import (
    DEFAULT_HARD_ADAPTER_TARGETS,
    AdapterTarget,
    verify_adapters,
)
from app.engines.bb_browser import BBBrowserEngine


def _parse_target(raw: str) -> AdapterTarget:
    adapter, _, query = raw.partition(":")
    if "/" not in adapter or not query:
        raise argparse.ArgumentTypeError(
            "target must use adapter/query format: site/command:query"
        )
    site, command = adapter.split("/", 1)
    return AdapterTarget(site=site.strip(), command=command.strip(), query=query.strip())


def _items_from_json(stdout: str) -> list[dict[str, Any]]:
    data = json.loads(stdout)
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        payload = data.get("data", data)
        if isinstance(payload, dict):
            items = (
                payload.get("items")
                or payload.get("results")
                or payload.get("videos")
                or payload.get("posts")
                or payload.get("papers")
                or []
            )
        elif isinstance(payload, list):
            items = payload
        else:
            items = []
    else:
        items = []
    return [item for item in items if isinstance(item, dict)]


def _adapter_error(rc: int, stdout: str, stderr: str) -> str:
    """Return the most useful adapter failure message."""
    if stderr.strip():
        return stderr.strip()
    try:
        data = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        data = None
    if isinstance(data, dict) and data.get("error"):
        return str(data["error"])
    return f"exit code {rc}"


def _summarize(results: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for result in results:
        status = result["quality_status"]
        counts[status] = counts.get(status, 0) + 1
    return {
        "total": len(results),
        "counts": counts,
        "verified": counts.get("verified", 0),
        "weak": counts.get("weak", 0),
        "failed": counts.get("failed", 0),
    }


async def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        action="append",
        type=_parse_target,
        default=[],
        help="Adapter target as site/command:query. Can be repeated.",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--min-results", type=int, default=1)
    parser.add_argument(
        "--output",
        default="outputs/source_adapter_verification.json",
        help="Output JSON file",
    )
    args = parser.parse_args()

    targets = args.target or list(DEFAULT_HARD_ADAPTER_TARGETS)
    engine = BBBrowserEngine()

    async def runner(site: str, command: str, query: str, *, timeout: int):
        adapter = f"{site}/{command}"
        rc, stdout, stderr = await engine._run_subprocess(
            [engine._bin, "site", adapter, query, "--json"],
            timeout=timeout,
        )
        if rc != 0:
            raise RuntimeError(_adapter_error(rc, stdout, stderr))
        return _items_from_json(stdout)

    results = await verify_adapters(
        targets,
        runner,
        limit=args.limit,
        timeout=args.timeout,
        min_results=args.min_results,
    )
    result_dicts = [result.to_dict() for result in results]
    payload = {
        "summary": _summarize(result_dicts),
        "results": result_dicts,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(f"Results saved to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
