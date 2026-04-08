"""
Result persistence in JSON, NDJSON, and Markdown formats.

Uses atomic writes (write to .tmp, then rename) for safety.
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)


class ResultStorage:
    """Saves research results to structured output files."""

    async def save(
        self,
        result: Any,
        output_format: str = "json",
        output_dir: str = "outputs",
    ) -> list[str]:
        """Save research result to files.

        Returns list of output file paths.
        """
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_id = re.sub(r"[^\w\-]", "_", result.task.task_id)[:32]
        base_name = f"{safe_id}_{timestamp}"

        files: list[str] = []

        if output_format == "json":
            path = os.path.join(output_dir, f"{base_name}.json")
            self._write_json(path, result)
            files.append(path)
        elif output_format == "ndjson":
            path = os.path.join(output_dir, f"{base_name}.ndjson")
            self._write_ndjson(path, result)
            files.append(path)
        elif output_format == "md":
            path = os.path.join(output_dir, f"{base_name}.md")
            self._write_markdown(path, result)
            files.append(path)
        else:
            # Unknown format — default to JSON
            _logger.warning("Unknown output format '%s', defaulting to json", output_format)
            path = os.path.join(output_dir, f"{base_name}.json")
            self._write_json(path, result)
            files.append(path)

        # Always write manifest
        manifest_path = os.path.join(output_dir, f"{base_name}_manifest.json")
        self._write_manifest(manifest_path, result, files)
        files.append(manifest_path)

        _logger.info("Saved %d files to %s", len(files), output_dir)
        return files

    # ------------------------------------------------------------------
    # Writers
    # ------------------------------------------------------------------

    def _write_json(self, path: str, result: Any) -> None:
        """Write full result as pretty-printed JSON."""
        data = self._result_to_dict(result)
        self._atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2, default=str))

    def _write_ndjson(self, path: str, result: Any) -> None:
        """Write one JSON line per record (newline-delimited JSON)."""
        lines: list[str] = []
        for record in result.records:
            row = record.model_dump() if hasattr(record, "model_dump") else record.__dict__
            lines.append(json.dumps(row, ensure_ascii=False, default=str))
        self._atomic_write(path, "\n".join(lines) + "\n" if lines else "")

    def _write_markdown(self, path: str, result: Any) -> None:
        """Write a human-readable Markdown report."""
        parts: list[str] = []

        parts.append(f"# Research Report: {result.task.query}\n")
        parts.append(f"- **Task ID**: {result.task.task_id}")
        parts.append(f"- **Language**: {result.task.language}")
        parts.append(f"- **Created**: {result.created_at}")
        parts.append(f"- **Records**: {len(result.records)}")

        # Stats
        stats = result.stats
        parts.append("\n## Statistics\n")
        parts.append(f"| Metric | Value |")
        parts.append(f"|--------|-------|")
        parts.append(f"| Discovered | {stats.total_discovered} |")
        parts.append(f"| Collected | {stats.total_collected} |")
        parts.append(f"| Skipped (quality) | {stats.skipped_quality} |")
        parts.append(f"| Skipped (duplicate) | {stats.skipped_duplicate} |")
        parts.append(f"| Skipped (blocked) | {stats.skipped_blocked} |")
        parts.append(f"| Avg fetch (ms) | {stats.avg_fetch_ms:.0f} |")
        parts.append(f"| Total duration (s) | {stats.total_duration_s} |")

        if stats.engines_used:
            parts.append("\n### Engines Used\n")
            for eng, count in sorted(stats.engines_used.items()):
                parts.append(f"- **{eng}**: {count} fetches")

        # Queries
        if result.queries_used:
            parts.append("\n## Queries Expanded\n")
            for i, q in enumerate(result.queries_used, 1):
                parts.append(f"{i}. {q}")

        # Records
        parts.append("\n## Records\n")
        for i, rec in enumerate(result.records, 1):
            parts.append(f"### {i}. {rec.title or rec.url}\n")
            parts.append(f"- **URL**: {rec.url}")
            parts.append(f"- **Engine**: {rec.fetch_engine}")
            parts.append(f"- **Credibility**: {rec.credibility:.2f}")
            if rec.published_at:
                parts.append(f"- **Published**: {rec.published_at}")
            parts.append(f"- **Length**: {rec.text_length} chars")
            parts.append("")
            # Summary / excerpt
            if rec.summary:
                parts.append(f"> {rec.summary[:500]}")
            parts.append("")

        self._atomic_write(path, "\n".join(parts))

    def _write_manifest(self, path: str, result: Any, files: list[str]) -> None:
        """Write a manifest summarising the output."""
        manifest = {
            "task_id": result.task.task_id,
            "query": result.task.query,
            "created_at": result.created_at,
            "record_count": len(result.records),
            "output_files": files,
            "stats": result.stats.model_dump() if hasattr(result.stats, "model_dump") else {},
            "queries_used": result.queries_used,
        }
        self._atomic_write(path, json.dumps(manifest, ensure_ascii=False, indent=2, default=str))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _result_to_dict(result: Any) -> dict:
        """Convert a ResearchResult to a serialisable dict."""
        if hasattr(result, "model_dump"):
            return result.model_dump()
        # Fallback for non-pydantic objects
        return {
            "task": result.task.__dict__ if hasattr(result.task, "__dict__") else str(result.task),
            "records": [
                r.model_dump() if hasattr(r, "model_dump") else r.__dict__
                for r in result.records
            ],
            "stats": result.stats.model_dump() if hasattr(result.stats, "model_dump") else {},
            "queries_used": result.queries_used,
            "output_files": result.output_files,
            "created_at": getattr(result, "created_at", ""),
        }

    @staticmethod
    def _atomic_write(path: str, content: str) -> None:
        """Write content to a file atomically via temp-file + rename."""
        tmp_path = path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(content)
            # On Windows os.replace is atomic within the same volume
            os.replace(tmp_path, path)
        except OSError:
            # Fallback: direct write if rename fails (cross-device, etc.)
            _logger.debug("atomic rename failed for %s, writing directly", path)
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
