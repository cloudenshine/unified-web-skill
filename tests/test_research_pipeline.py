"""tests/test_research_pipeline.py — 集成测试（全 mock）"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest.mock as mock
import pytest

from app.research_models import ResearchTask, ResearchResult
from app.research_pipeline import ResearchPipeline


def make_task(tmp_path: str, **kwargs) -> ResearchTask:
    defaults = dict(
        query="Python 异步编程",
        language="zh",
        max_sources=5,
        max_pages=3,
        max_queries=3,
        min_text_length=50,
        output_path=tmp_path,
        domain_qps=100.0,  # no rate limiting in tests
        max_concurrency=2,
        opencli_enabled=True,
        opencli_fallback=True,
    )
    defaults.update(kwargs)
    return ResearchTask(**defaults)


def _make_fetch_result(ok=True, html="<p>" + "content " * 50 + "</p>",
                       status=200, engine="scrapling-http", route="http"):
    from app.scrapling_engine import FetchResult
    return FetchResult(
        ok=ok, url="https://example.com", status=status,
        html=html, engine=engine, route=route, duration_ms=100.0
    )


class TestResearchPipelineEndToEnd:
    def test_normal_pipeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = make_task(tmp)

            candidates = [
                mock.MagicMock(
                    url=f"https://site{i}.com/page",
                    canonical_url=f"https://site{i}.com/page",
                    score=0.6 + i * 0.05,
                    model_dump=lambda: {"url": "u", "score": 0.6}
                )
                for i in range(3)
            ]
            # Patch model_dump properly
            for i, c in enumerate(candidates):
                c.model_dump.return_value = {
                    "url": f"https://site{i}.com/page",
                    "score": 0.6,
                }

            fetch_result = _make_fetch_result()

            with mock.patch("app.research_pipeline.discover_from_queries",
                            return_value=candidates), \
                 mock.patch("app.research_pipeline.fetch_with_fallback",
                            return_value=fetch_result), \
                 mock.patch("app.research_pipeline.run_opencli",
                            return_value={"ok": False, "exit_code": 78,
                                          "stdout": "", "stderr": "", "parsed": {}}):
                pipeline = ResearchPipeline()
                result = asyncio.run(pipeline.run(task))

            assert isinstance(result, ResearchResult)
            assert result.task_id is not None
            assert len(result.expanded_queries) > 0
            assert result.stats.discovered == 3

    def test_empty_discovery_returns_valid_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = make_task(tmp)

            with mock.patch("app.research_pipeline.discover_from_queries",
                            return_value=[]):
                pipeline = ResearchPipeline()
                result = asyncio.run(pipeline.run(task))

            assert isinstance(result, ResearchResult)
            assert result.stats.discovered == 0
            assert result.stats.collected == 0
            assert len(result.collected) == 0

    def test_opencli_success_skips_scrapling(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = make_task(tmp, opencli_enabled=True)

            candidate = mock.MagicMock(
                url="https://bilibili.com/video/123",
                canonical_url="https://bilibili.com/video/123",
                score=0.7,
            )
            candidate.model_dump.return_value = {"url": "https://bilibili.com/video/123", "score": 0.7}

            cli_result = {
                "ok": True,
                "exit_code": 0,
                "stdout": "视频标题：Python 教程。" + "内容 " * 30,
                "stderr": "",
                "parsed": {"title": "Python 教程"},
            }

            scrapling_called = []

            async def fake_scrapling(*args, **kwargs):
                scrapling_called.append(True)
                return _make_fetch_result()

            with mock.patch("app.research_pipeline.discover_from_queries",
                            return_value=[candidate]), \
                 mock.patch("app.research_pipeline.run_opencli",
                            return_value=cli_result), \
                 mock.patch("app.research_pipeline.fetch_with_fallback",
                            side_effect=fake_scrapling), \
                 mock.patch("app.research_pipeline.get_router") as mock_router:
                mock_router.return_value.get_opencli_command.return_value = ("bilibili", "hot")
                pipeline = ResearchPipeline()
                result = asyncio.run(pipeline.run(task))

            # Scrapling should not have been called since opencli succeeded
            assert len(scrapling_called) == 0
            assert result.stats.opencli_used >= 1

    def test_opencli_fallback_to_scrapling(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = make_task(tmp, opencli_enabled=True, opencli_fallback=True)

            candidate = mock.MagicMock(
                url="https://bilibili.com/video/123",
                canonical_url="https://bilibili.com/video/123",
                score=0.7,
            )
            candidate.model_dump.return_value = {"url": "u", "score": 0.7}

            cli_result = {
                "ok": False, "exit_code": 78,
                "stdout": "", "stderr": "not found", "parsed": {}
            }
            fetch_result = _make_fetch_result(
                html="<p>" + "fallback content " * 30 + "</p>"
            )

            with mock.patch("app.research_pipeline.discover_from_queries",
                            return_value=[candidate]), \
                 mock.patch("app.research_pipeline.run_opencli",
                            return_value=cli_result), \
                 mock.patch("app.research_pipeline.fetch_with_fallback",
                            return_value=fetch_result), \
                 mock.patch("app.research_pipeline.get_router") as mock_router:
                mock_router.return_value.get_opencli_command.return_value = ("bilibili", "hot")
                pipeline = ResearchPipeline()
                result = asyncio.run(pipeline.run(task))

            # Should have fallen back to scrapling
            assert result.stats.tool_chain_counter.get("scrapling", 0) >= 1

    def test_content_quality_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = make_task(tmp, min_text_length=500)

            candidate = mock.MagicMock(
                url="https://example.com/short",
                canonical_url="https://example.com/short",
                score=0.6,
            )
            candidate.model_dump.return_value = {"url": "u", "score": 0.6}

            # Very short content — should be filtered
            short_result = _make_fetch_result(html="<p>Short content</p>")

            with mock.patch("app.research_pipeline.discover_from_queries",
                            return_value=[candidate]), \
                 mock.patch("app.research_pipeline.fetch_with_fallback",
                            return_value=short_result), \
                 mock.patch("app.research_pipeline.run_opencli",
                            return_value={"ok": False, "exit_code": 78,
                                          "stdout": "", "stderr": "", "parsed": {}}):
                pipeline = ResearchPipeline()
                result = asyncio.run(pipeline.run(task))

            assert result.stats.skipped_low_quality >= 1
            assert len(result.collected) == 0

    def test_duplicate_content_filtered(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = make_task(tmp, min_text_length=10)

            same_html = "<p>" + "duplicate content " * 10 + "</p>"
            candidates = [
                mock.MagicMock(
                    url=f"https://site{i}.com/same",
                    canonical_url=f"https://site{i}.com/same-page",
                    score=0.6,
                )
                for i in range(2)
            ]
            for i, c in enumerate(candidates):
                c.model_dump.return_value = {"url": f"https://site{i}.com/same", "score": 0.6}

            fetch_result = _make_fetch_result(html=same_html)

            with mock.patch("app.research_pipeline.discover_from_queries",
                            return_value=candidates), \
                 mock.patch("app.research_pipeline.fetch_with_fallback",
                            return_value=fetch_result), \
                 mock.patch("app.research_pipeline.run_opencli",
                            return_value={"ok": False, "exit_code": 78,
                                          "stdout": "", "stderr": "", "parsed": {}}):
                pipeline = ResearchPipeline()
                result = asyncio.run(pipeline.run(task))

            # Two identical content → one deduplicated
            assert result.stats.skipped_duplicate >= 1
            assert len(result.collected) <= 1
