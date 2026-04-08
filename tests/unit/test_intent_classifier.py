"""Tests for app.discovery.intent_classifier — IntentClassifier."""

import pytest
from app.discovery.intent_classifier import IntentClassifier, QueryIntent


@pytest.fixture
def classifier():
    return IntentClassifier()


class TestClassifyIntents:
    def test_informational_zh(self, classifier):
        assert classifier.classify("什么是机器学习") == QueryIntent.INFORMATIONAL

    def test_informational_en(self, classifier):
        assert classifier.classify("what is machine learning") == QueryIntent.INFORMATIONAL

    def test_news_zh(self, classifier):
        assert classifier.classify("今日AI新闻") == QueryIntent.NEWS

    def test_news_en(self, classifier):
        assert classifier.classify("latest AI news today") == QueryIntent.NEWS

    def test_academic_zh(self, classifier):
        assert classifier.classify("大语言模型论文研究") == QueryIntent.ACADEMIC

    def test_academic_en(self, classifier):
        assert classifier.classify("transformer paper arxiv research") == QueryIntent.ACADEMIC

    def test_social_zh(self, classifier):
        assert classifier.classify("微博热搜关注") == QueryIntent.SOCIAL

    def test_social_en(self, classifier):
        assert classifier.classify("reddit thread viral") == QueryIntent.SOCIAL

    def test_code_zh(self, classifier):
        assert classifier.classify("Python代码报错bug") == QueryIntent.CODE

    def test_code_en(self, classifier):
        assert classifier.classify("python github api error debug") == QueryIntent.CODE

    def test_finance_zh(self, classifier):
        assert classifier.classify("A股大盘行情") == QueryIntent.FINANCE

    def test_finance_en(self, classifier):
        assert classifier.classify("stock market trading crypto bitcoin") == QueryIntent.FINANCE

    def test_transactional_zh(self, classifier):
        assert classifier.classify("购买下载优惠") == QueryIntent.TRANSACTIONAL

    def test_transactional_en(self, classifier):
        assert classifier.classify("buy discount deal price") == QueryIntent.TRANSACTIONAL

    def test_navigational_zh(self, classifier):
        assert classifier.classify("百度官网登录") == QueryIntent.NAVIGATIONAL

    def test_navigational_en(self, classifier):
        result = classifier.classify("google.com official site login")
        assert result == QueryIntent.NAVIGATIONAL

    def test_local_zh(self, classifier):
        assert classifier.classify("附近餐厅推荐") == QueryIntent.LOCAL

    def test_local_en(self, classifier):
        assert classifier.classify("restaurant near me directions") == QueryIntent.LOCAL

    def test_fallback_to_informational(self, classifier):
        # A generic query with no intent keywords
        result = classifier.classify("xyzzy foobar baz")
        assert result == QueryIntent.INFORMATIONAL


class TestLanguageDetection:
    def test_chinese_text(self, classifier):
        assert classifier.detect_language("这是一段中文测试文本") == "zh"

    def test_english_text(self, classifier):
        assert classifier.detect_language("This is an English test text") == "en"

    def test_mixed_text(self, classifier):
        # Mix of Chinese and English
        result = classifier.detect_language("Hello你好World世界Test测试")
        assert result in ("zh", "mixed")

    def test_empty_text(self, classifier):
        assert classifier.detect_language("") == "unknown"

    def test_whitespace_only(self, classifier):
        assert classifier.detect_language("   ") == "unknown"

    def test_numbers_only(self, classifier):
        assert classifier.detect_language("12345") == "unknown"


class TestAutoLanguage:
    def test_classify_auto_zh(self, classifier):
        # With auto language, should detect Chinese and still classify
        result = classifier.classify("什么是机器学习", language="auto")
        assert result == QueryIntent.INFORMATIONAL

    def test_classify_auto_en(self, classifier):
        result = classifier.classify("how to learn Python", language="auto")
        assert result == QueryIntent.INFORMATIONAL


class TestRecommendedSources:
    def test_zh_code_sources(self, classifier):
        sources = classifier.get_recommended_sources(QueryIntent.CODE, "zh")
        assert "github" in sources

    def test_en_news_sources(self, classifier):
        sources = classifier.get_recommended_sources(QueryIntent.NEWS, "en")
        assert "google" in sources

    def test_fallback_sources(self, classifier):
        # Unknown language falls back to en
        sources = classifier.get_recommended_sources(QueryIntent.CODE, "fr")
        assert len(sources) >= 1
