"""tests/test_research_models.py"""
import pytest
from pydantic import ValidationError
from app.research_models import (
    ResearchTask,
    ResearchRecord,
    ResearchResult,
    ResearchStats,
    Candidate,
)


class TestResearchTask:
    def test_minimal_valid(self):
        task = ResearchTask(query="test")
        assert task.query == "test"
        assert task.language == "zh"
        assert task.max_sources == 20
        assert task.task_id is not None  # auto-generated

    def test_task_id_auto_generated(self):
        t1 = ResearchTask(query="a")
        t2 = ResearchTask(query="b")
        assert t1.task_id != t2.task_id

    def test_task_id_preserved_if_given(self):
        task = ResearchTask(query="test", task_id="my-custom-id")
        assert task.task_id == "my-custom-id"

    def test_defaults(self):
        task = ResearchTask(query="test")
        assert task.max_pages == 20
        assert task.max_depth == 2
        assert task.trusted_mode is True
        assert task.min_credibility == 0.55
        assert task.output_format == "json"
        assert task.opencli_enabled is True
        assert task.opencli_fallback is True
        assert task.max_concurrency == 4

    def test_invalid_output_format(self):
        with pytest.raises(ValidationError):
            ResearchTask(query="test", output_format="xml")

    def test_max_sources_bounds(self):
        with pytest.raises(ValidationError):
            ResearchTask(query="test", max_sources=0)
        with pytest.raises(ValidationError):
            ResearchTask(query="test", max_sources=201)

    def test_credibility_bounds(self):
        with pytest.raises(ValidationError):
            ResearchTask(query="test", min_credibility=1.5)
        with pytest.raises(ValidationError):
            ResearchTask(query="test", min_credibility=-0.1)

    def test_list_defaults(self):
        task = ResearchTask(query="test")
        assert task.include_domains == []
        assert task.exclude_domains == []
        assert task.opencli_preferred_sites == []


class TestResearchRecord:
    def test_minimal_record(self):
        rec = ResearchRecord(url="https://example.com")
        assert rec.url == "https://example.com"
        assert rec.credibility == 0.5
        assert rec.text_length == 0

    def test_text_length_auto(self):
        rec = ResearchRecord(url="u", text="hello world")
        assert rec.text_length == 11

    def test_summary_auto(self):
        rec = ResearchRecord(url="u", text="sample text content")
        assert rec.summary == "sample text content"

    def test_serialization(self):
        rec = ResearchRecord(
            url="https://example.com",
            title="Test",
            text="Content",
            credibility=0.8,
            fetch_mode="scrapling:http",
            source_type="scrapling",
            language_detected="en",
        )
        data = rec.model_dump()
        assert data["url"] == "https://example.com"
        assert data["credibility"] == 0.8
        assert data["language_detected"] == "en"
        assert "tool_chain" in data
        assert "attempts" in data


class TestResearchResult:
    def test_minimal_result(self):
        result = ResearchResult(task_id="test-123")
        assert result.task_id == "test-123"
        assert result.collected == []
        assert result.stats.discovered == 0

    def test_with_records(self):
        record = ResearchRecord(url="https://example.com", text="content")
        result = ResearchResult(task_id="test", collected=[record])
        assert len(result.collected) == 1
        assert result.collected[0].url == "https://example.com"


class TestCandidate:
    def test_canonical_url_auto(self):
        c = Candidate(url="https://example.com/page/")
        assert c.canonical_url == "https://example.com/page"

    def test_canonical_strips_fragment(self):
        c = Candidate(url="https://example.com/page#section")
        assert "#" not in c.canonical_url

    def test_default_score(self):
        c = Candidate(url="https://example.com")
        assert c.score == 0.5


class TestResearchStats:
    def test_defaults(self):
        stats = ResearchStats()
        assert stats.discovered == 0
        assert stats.collected == 0
        assert stats.tool_chain_counter == {}
        assert stats.rate_limited_domains == []
