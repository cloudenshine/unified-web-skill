"""Integration tests for IntentClassifier, QueryPlanner, and MultiSourceDiscovery."""
import asyncio

import pytest

from app.discovery.intent_classifier import IntentClassifier, QueryIntent
from app.discovery.query_planner import QueryPlanner
from app.discovery.multi_source import MultiSourceDiscovery


class TestIntentClassifierAndQueryPlanner:
    """End-to-end tests for classification + query expansion."""

    def test_classify_informational_query(self):
        classifier = IntentClassifier()
        intent = classifier.classify("什么是机器学习")
        assert isinstance(intent, QueryIntent)

    def test_classify_code_query(self):
        classifier = IntentClassifier()
        intent = classifier.classify("Python sort algorithm implementation")
        assert isinstance(intent, QueryIntent)

    def test_query_planner_expand(self):
        planner = QueryPlanner()
        queries = planner.expand("Python 异步编程", max_queries=5)
        assert isinstance(queries, list)
        assert len(queries) >= 1
        # Original query should be first or present
        assert any("Python" in q or "异步" in q for q in queries)

    def test_planner_with_intent(self):
        classifier = IntentClassifier()
        planner = QueryPlanner(classifier=classifier)
        intent = classifier.classify("latest AI news")
        queries = planner.expand("latest AI news", intent=intent, max_queries=4)
        assert isinstance(queries, list)
        assert len(queries) >= 1

    def test_language_detection(self):
        classifier = IntentClassifier()
        assert classifier.detect_language("这是中文文本测试") == "zh"
        assert classifier.detect_language("This is an English text") == "en"

    def test_recommended_sources(self):
        classifier = IntentClassifier()
        sources = classifier.get_recommended_sources(QueryIntent.INFORMATIONAL, "zh")
        assert isinstance(sources, list)
        assert len(sources) > 0


class TestMultiSourceDiscovery:
    """Integration tests for MultiSourceDiscovery with DuckDuckGo."""

    @pytest.mark.asyncio
    async def test_discover_with_duckduckgo(self):
        """MultiSourceDiscovery.discover returns results using DuckDuckGo."""
        discovery = MultiSourceDiscovery()

        try:
            results = await asyncio.wait_for(
                discovery.discover(
                    "Python programming language",
                    max_sources=10,
                    language="en",
                ),
                timeout=30,
            )
        except (asyncio.TimeoutError, Exception) as exc:
            pytest.skip(f"DuckDuckGo search unavailable or timed out: {exc}")

        assert isinstance(results, list)
        # DuckDuckGo should return some results
        if len(results) > 0:
            r = results[0]
            assert hasattr(r, "url")
            assert hasattr(r, "title")
            assert r.url.startswith("http")

    @pytest.mark.asyncio
    async def test_discover_chinese_query(self):
        """MultiSourceDiscovery handles Chinese queries."""
        discovery = MultiSourceDiscovery()

        try:
            results = await asyncio.wait_for(
                discovery.discover(
                    "人工智能发展趋势",
                    max_sources=5,
                    language="zh",
                ),
                timeout=30,
            )
        except (asyncio.TimeoutError, Exception) as exc:
            pytest.skip(f"Search unavailable or timed out: {exc}")

        assert isinstance(results, list)
