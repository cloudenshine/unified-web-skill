"""Tests for app.discovery.query_planner — QueryPlanner."""

import pytest
from app.discovery.query_planner import QueryPlanner
from app.discovery.intent_classifier import IntentClassifier, QueryIntent


@pytest.fixture
def planner():
    return QueryPlanner()


class TestExpandBasic:
    def test_original_always_first(self, planner):
        result = planner.expand("test query")
        assert result[0] == "test query"

    def test_empty_query(self, planner):
        assert planner.expand("") == []
        assert planner.expand("   ") == []

    def test_returns_multiple_variants(self, planner):
        result = planner.expand("machine learning")
        assert len(result) >= 2

    def test_max_queries_limit(self, planner):
        result = planner.expand("test", max_queries=3)
        assert len(result) <= 3

    def test_no_duplicates(self, planner):
        result = planner.expand("Python tutorial")
        assert len(result) == len(set(result))


class TestExpandByIntent:
    def test_informational_zh(self, planner):
        result = planner.expand("机器学习", language="zh", intent=QueryIntent.INFORMATIONAL)
        assert any("是什么" in q for q in result)
        assert any("教程" in q or "详解" in q for q in result)

    def test_informational_en(self, planner):
        result = planner.expand("machine learning", language="en", intent=QueryIntent.INFORMATIONAL)
        assert any("what is" in q.lower() for q in result)

    def test_news_zh(self, planner):
        result = planner.expand("AI", language="zh", intent=QueryIntent.NEWS)
        assert any("最新" in q or "新闻" in q for q in result)

    def test_news_en(self, planner):
        result = planner.expand("AI", language="en", intent=QueryIntent.NEWS)
        assert any("latest" in q.lower() or "news" in q.lower() for q in result)

    def test_academic_zh(self, planner):
        result = planner.expand("transformer", language="zh", intent=QueryIntent.ACADEMIC)
        assert any("论文" in q or "研究" in q for q in result)

    def test_academic_en(self, planner):
        result = planner.expand("transformer", language="en", intent=QueryIntent.ACADEMIC)
        assert any("paper" in q.lower() or "research" in q.lower() for q in result)

    def test_code_zh(self, planner):
        result = planner.expand("Python排序", language="zh", intent=QueryIntent.CODE)
        assert any("代码" in q or "github" in q for q in result)

    def test_code_en(self, planner):
        result = planner.expand("python sort", language="en", intent=QueryIntent.CODE)
        assert any("github" in q.lower() or "example" in q.lower() for q in result)

    def test_finance_zh(self, planner):
        result = planner.expand("贵州茅台", language="zh", intent=QueryIntent.FINANCE)
        assert any("行情" in q or "分析" in q for q in result)

    def test_finance_en(self, planner):
        result = planner.expand("AAPL", language="en", intent=QueryIntent.FINANCE)
        assert any("stock" in q.lower() or "market" in q.lower() for q in result)

    def test_social_zh(self, planner):
        result = planner.expand("ChatGPT", language="zh", intent=QueryIntent.SOCIAL)
        assert any("讨论" in q or "评价" in q for q in result)

    def test_social_en(self, planner):
        result = planner.expand("ChatGPT", language="en", intent=QueryIntent.SOCIAL)
        assert any("discussion" in q.lower() or "reddit" in q.lower() for q in result)

    def test_transactional_zh(self, planner):
        result = planner.expand("iPhone", language="zh", intent=QueryIntent.TRANSACTIONAL)
        assert any("价格" in q or "购买" in q for q in result)

    def test_transactional_en(self, planner):
        result = planner.expand("iPhone", language="en", intent=QueryIntent.TRANSACTIONAL)
        assert any("price" in q.lower() or "buy" in q.lower() for q in result)

    def test_navigational_zh(self, planner):
        result = planner.expand("淘宝", language="zh", intent=QueryIntent.NAVIGATIONAL)
        assert any("官网" in q or "登录" in q for q in result)

    def test_navigational_en(self, planner):
        result = planner.expand("Amazon", language="en", intent=QueryIntent.NAVIGATIONAL)
        assert any("official" in q.lower() or "login" in q.lower() for q in result)

    def test_local_zh(self, planner):
        result = planner.expand("火锅", language="zh", intent=QueryIntent.LOCAL)
        assert any("推荐" in q or "攻略" in q for q in result)

    def test_local_en(self, planner):
        result = planner.expand("sushi", language="en", intent=QueryIntent.LOCAL)
        assert any("near me" in q.lower() or "best" in q.lower() for q in result)


class TestAutoDetect:
    def test_auto_detects_chinese(self, planner):
        result = planner.expand("最新AI新闻", language="auto")
        assert len(result) >= 2
        # Should include Chinese variants
        assert any(any(ord(c) > 0x4E00 for c in q) for q in result[1:])

    def test_auto_detects_english(self, planner):
        result = planner.expand("latest AI news", language="auto")
        assert len(result) >= 2


class TestExpansionCount:
    def test_default_within_limit(self, planner):
        result = planner.expand("test query")
        assert len(result) <= 8  # default max_queries

    def test_custom_max(self, planner):
        result = planner.expand("test", max_queries=5)
        assert len(result) <= 5

    def test_max_one_returns_original(self, planner):
        result = planner.expand("test", max_queries=1)
        assert result == ["test"]
