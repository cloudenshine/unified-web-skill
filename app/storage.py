"""storage.py — 研究结果落盘（json / ndjson / md）"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _record_to_md(record: dict) -> str:
    lines = [
        f"## {record.get('title') or record.get('url', 'Untitled')}",
        f"- URL: {record.get('url', '')}",
        f"- Credibility: {record.get('credibility', 0.5):.2f}",
        f"- Published: {record.get('published_at') or 'unknown'}",
        f"- Language: {record.get('language_detected', 'unknown')}",
        "",
        record.get("text", ""),
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def save_research(
    result: object,
    output_path: str = "outputs/research",
    output_format: str = "json",
    task_id: str | None = None,
) -> dict:
    """
    将 ResearchResult 持久化到磁盘。
    支持 json / ndjson / md 三种格式。
    返回 {"manifest_path": str, "saved": [str, ...]}
    """
    from .research_models import ResearchResult

    if isinstance(result, ResearchResult):
        result_dict = result.model_dump()
        records = [r.model_dump() if hasattr(r, "model_dump") else r
                   for r in result.collected]
        tid = task_id or result.task_id
    else:
        result_dict = result if isinstance(result, dict) else {}
        records = result_dict.get("collected", [])
        tid = task_id or result_dict.get("task_id", "unknown")

    _ensure_dir(output_path)
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base_name = f"{tid}_{now_str}"
    saved: list[str] = []

    # 主数据文件
    if output_format == "json":
        data_path = os.path.join(output_path, f"{base_name}.json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        saved.append(data_path)

    elif output_format == "ndjson":
        data_path = os.path.join(output_path, f"{base_name}.ndjson")
        with open(data_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        saved.append(data_path)

    elif output_format == "md":
        data_path = os.path.join(output_path, f"{base_name}.md")
        with open(data_path, "w", encoding="utf-8") as f:
            f.write(f"# Research: {result_dict.get('task_id', tid)}\n\n")
            for rec in records:
                r = rec if isinstance(rec, dict) else rec
                f.write(_record_to_md(r))
        saved.append(data_path)

    # Manifest
    manifest: dict = {
        "task_id": tid,
        "created_at": now_str,
        "format": output_format,
        "record_count": len(records),
        "stats": result_dict.get("stats", {}),
        "expanded_queries": result_dict.get("expanded_queries", []),
        "files": saved,
    }
    manifest_path = os.path.join(output_path, f"{tid}_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    saved.append(manifest_path)

    return {"manifest_path": manifest_path, "saved": saved}
