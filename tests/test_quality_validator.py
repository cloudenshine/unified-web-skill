"""tests/test_quality_validator.py"""
import datetime
import pytest
from app.quality_validator import detect_language, validate_content, deduplicate_by_hash


class TestValidateContent:
    def test_passes_long_text(self):
        text = "这是一段足够长的文章内容。" * 30
        ok, reason = validate_content(text, min_text_length=200)
        assert ok is True
        assert reason == ""

    def test_fails_short_text(self):
        ok, reason = validate_content("短文本", min_text_length=200)
        assert ok is False
        assert "text_too_short" in reason

    def test_passes_exact_length(self):
        text = "a" * 200
        ok, reason = validate_content(text, min_text_length=200)
        assert ok is True

    def test_fails_one_below_length(self):
        text = "a" * 199
        ok, reason = validate_content(text, min_text_length=200)
        assert ok is False

    def test_no_time_filter_when_zero(self):
        text = "x" * 300
        ok, reason = validate_content(text, published_at="2000-01-01", time_window_days=0)
        assert ok is True

    def test_fails_old_content(self):
        text = "x" * 300
        ok, reason = validate_content(text, published_at="2000-01-01", time_window_days=30)
        assert ok is False
        assert "too_old" in reason

    def test_passes_recent_content(self):
        from datetime import datetime, timedelta, timezone
        recent = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
        text = "x" * 300
        ok, reason = validate_content(text, published_at=recent, time_window_days=30)
        assert ok is True

    def test_skips_filter_on_unparseable_date(self):
        text = "x" * 300
        ok, reason = validate_content(text, published_at="not-a-date", time_window_days=30)
        assert ok is True  # unparseable date → skip filter

    def test_chinese_date_format(self):
        text = "x" * 300
        ok, reason = validate_content(text, published_at="2000年01月01日", time_window_days=30)
        assert ok is False
        assert "too_old" in reason

    def test_none_text(self):
        ok, reason = validate_content(None, min_text_length=200)  # type: ignore
        assert ok is False


class TestDetectLanguage:
    def test_chinese_text(self):
        text = "这是一段中文文章，包含很多汉字，用于测试语言检测功能。" * 5
        assert detect_language(text) == "zh"

    def test_english_text(self):
        text = "This is an English article with many words for testing language detection." * 3
        assert detect_language(text) == "en"

    def test_empty_text(self):
        assert detect_language("") == "unknown"
        assert detect_language(None) == "unknown"  # type: ignore

    def test_mixed_text(self):
        # Mostly Chinese
        text = "中文内容" * 20 + " some english"
        result = detect_language(text)
        assert result == "zh"

    def test_mostly_english(self):
        text = "Hello world this is a test " * 10 + "中"
        result = detect_language(text)
        assert result == "en"


class TestDeduplicateByHash:
    def test_removes_duplicates(self):
        records = [
            {"content_hash": "abc123", "text": "first"},
            {"content_hash": "abc123", "text": "duplicate"},
            {"content_hash": "def456", "text": "unique"},
        ]
        result = deduplicate_by_hash(records)
        assert len(result) == 2
        assert result[0]["text"] == "first"

    def test_empty_hash_kept(self):
        records = [
            {"content_hash": "", "text": "no hash 1"},
            {"content_hash": "", "text": "no hash 2"},
        ]
        result = deduplicate_by_hash(records)
        assert len(result) == 2  # both kept (no hash to dedup on)

    def test_preserves_order(self):
        records = [
            {"content_hash": "a", "text": "1"},
            {"content_hash": "b", "text": "2"},
            {"content_hash": "c", "text": "3"},
        ]
        result = deduplicate_by_hash(records)
        assert [r["text"] for r in result] == ["1", "2", "3"]
