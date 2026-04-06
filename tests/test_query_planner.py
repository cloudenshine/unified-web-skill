"""tests/test_query_planner.py"""
import pytest
from app.query_planner import expand_queries
import datetime


class TestExpandQueries:
    def test_returns_list(self):
        result = expand_queries("人工智能", max_queries=5)
        assert isinstance(result, list)

    def test_original_query_included(self):
        result = expand_queries("人工智能", max_queries=5)
        assert "人工智能" in result

    def test_respects_max_queries(self):
        result = expand_queries("test", max_queries=3)
        assert len(result) <= 3

    def test_no_duplicates(self):
        result = expand_queries("test query", max_queries=10)
        assert len(result) == len(set(result))

    def test_empty_query_returns_empty(self):
        result = expand_queries("", max_queries=5)
        assert result == []

    def test_whitespace_query_returns_empty(self):
        result = expand_queries("   ", max_queries=5)
        assert result == []

    def test_chinese_language_variants(self):
        result = expand_queries("中国贸易政策", max_queries=10, language="zh")
        # Should have year variant
        year = str(datetime.datetime.now(datetime.timezone.utc).year)
        assert any(year in q for q in result)
        # Should have 官方 variant
        assert any("官方" in q for q in result)

    def test_english_language_variants(self):
        result = expand_queries("AI regulation", max_queries=10, language="en")
        year = str(datetime.datetime.now(datetime.timezone.utc).year)
        assert any(year in q for q in result)
        assert any("latest" in q for q in result)

    def test_max_queries_one(self):
        result = expand_queries("test", max_queries=1)
        assert len(result) == 1
        assert result[0] == "test"

    def test_all_results_are_strings(self):
        result = expand_queries("climate change", max_queries=8, language="en")
        assert all(isinstance(q, str) for q in result)
        assert all(len(q) > 0 for q in result)
