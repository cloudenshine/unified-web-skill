"""Tests for app.models — ResearchTask, ResearchRecord, ResearchResult, ResearchStats."""

import uuid
import pytest
from app.models import ResearchTask, ResearchRecord, ResearchResult, ResearchStats


class TestResearchTask:
    def test_creation_with_defaults(self):
        task = ResearchTask(query="test query")
        assert task.query == "test query"
        assert task.language == "zh"
        assert task.max_sources == 30
        assert task.max_pages == 20
        assert task.max_queries == 8
        assert task.max_concurrency == 5
        assert task.timeout_seconds == 30
        assert task.preferred_engines == []
        assert task.search_engines == []
        assert task.enable_site_adapters is True
        assert task.enable_stealth is False
        assert task.min_text_length == 100
        assert task.min_credibility == 0.3
        assert task.output_format == "json"
        assert task.output_dir == "outputs"
        # task_id auto-generated
        assert len(task.task_id) > 0
        uuid.UUID(task.task_id)  # should not raise

    def test_creation_with_custom_fields(self):
        task = ResearchTask(
            query="自定义查询",
            language="en",
            max_sources=50,
            max_pages=40,
            max_queries=15,
            max_concurrency=10,
            timeout_seconds=60,
            preferred_engines=["scrapling", "lightpanda"],
            search_engines=["google"],
            enable_stealth=True,
            min_text_length=200,
            min_credibility=0.5,
            trusted_mode=True,
            time_window_days=7,
            include_domains=["example.com"],
            exclude_domains=["bad.com"],
            output_format="md",
            output_dir="my_outputs",
        )
        assert task.language == "en"
        assert task.max_sources == 50
        assert task.enable_stealth is True
        assert task.trusted_mode is True
        assert task.time_window_days == 7
        assert task.include_domains == ["example.com"]
        assert task.output_format == "md"

    def test_validation_min_max(self):
        with pytest.raises(Exception):
            ResearchTask(query="q", max_sources=0)
        with pytest.raises(Exception):
            ResearchTask(query="q", max_sources=501)
        with pytest.raises(Exception):
            ResearchTask(query="q", min_credibility=1.5)


class TestResearchRecord:
    def test_creation(self):
        rec = ResearchRecord(url="https://example.com", title="Test", text="Hello world content here.")
        assert rec.url == "https://example.com"
        assert rec.title == "Test"
        assert rec.text_length == len("Hello world content here.")
        assert rec.summary == "Hello world content here."
        assert rec.credibility == 0.5
        assert rec.language == "unknown"

    def test_auto_text_length(self):
        rec = ResearchRecord(url="u", text="a" * 100)
        assert rec.text_length == 100

    def test_auto_summary(self):
        long_text = "x" * 500
        rec = ResearchRecord(url="u", text=long_text)
        assert len(rec.summary) == 300

    def test_no_auto_fill_when_provided(self):
        rec = ResearchRecord(url="u", text="hello", text_length=999, summary="custom")
        assert rec.text_length == 999
        assert rec.summary == "custom"

    def test_empty_text(self):
        rec = ResearchRecord(url="u")
        assert rec.text_length == 0
        assert rec.summary == ""


class TestResearchStats:
    def test_defaults(self):
        stats = ResearchStats()
        assert stats.total_discovered == 0
        assert stats.total_collected == 0
        assert stats.engines_used == {}
        assert stats.avg_fetch_ms == 0
        assert stats.total_duration_s == 0

    def test_custom_values(self):
        stats = ResearchStats(
            total_discovered=100,
            total_collected=80,
            skipped_quality=10,
            skipped_duplicate=5,
            skipped_blocked=5,
            engines_used={"scrapling": 50, "lightpanda": 30},
            fallback_count=3,
            avg_fetch_ms=150.0,
        )
        assert stats.total_discovered == 100
        assert stats.engines_used["scrapling"] == 50


class TestResearchResult:
    def test_creation(self):
        task = ResearchTask(query="test")
        result = ResearchResult(task=task)
        assert result.records == []
        assert result.queries_used == []
        assert result.output_files == []
        assert result.created_at is not None

    def test_creation_with_records(self):
        task = ResearchTask(query="test")
        records = [
            ResearchRecord(url="https://a.com", text="content a"),
            ResearchRecord(url="https://b.com", text="content b"),
        ]
        result = ResearchResult(task=task, records=records, queries_used=["test", "test 2"])
        assert len(result.records) == 2
        assert len(result.queries_used) == 2

    def test_stats_default(self):
        task = ResearchTask(query="test")
        result = ResearchResult(task=task)
        assert isinstance(result.stats, ResearchStats)
        assert result.stats.total_discovered == 0
