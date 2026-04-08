"""Tests for app.pipeline.extractor — ContentExtractor."""

import hashlib
import pytest
from unittest.mock import patch
from types import SimpleNamespace

from app.pipeline.extractor import ContentExtractor


@pytest.fixture
def extractor():
    return ContentExtractor()


SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Page Title - SiteName</title>
    <meta property="og:title" content="OG Title Here">
    <meta name="article:published_time" content="2024-06-15T10:30:00Z">
</head>
<body>
    <article>
        <h1>Main Article Heading</h1>
        <p>This is a long paragraph of text content that should be extracted properly.
        It contains enough text to pass quality checks and demonstrates the extraction
        capabilities of the ContentExtractor class in our unified web skill.</p>
        <p>Second paragraph with more details about the topic being discussed.</p>
        <a href="/page1">Link 1</a>
        <a href="https://external.com/page2">Link 2</a>
        <a href="javascript:void(0)">JS Link</a>
        <a href="#anchor">Anchor</a>
        <a href="mailto:test@example.com">Email</a>
    </article>
    <script>var x = 1; console.log(x);</script>
    <style>.hidden { display: none; }</style>
</body>
</html>
"""

SAMPLE_HTML_CHINESE = """
<html>
<head><title>中文页面标题</title></head>
<body>
<p>这是一段中文测试内容，用于验证语言检测功能。</p>
<p>第二段中文内容，确保有足够的文本长度来进行各种测试。</p>
</body>
</html>
"""


class TestExtract:
    def test_extract_from_html(self, extractor):
        fr = SimpleNamespace(html=SAMPLE_HTML, text="", url="https://example.com", title="")
        result = extractor.extract(fr)
        assert result["text"]
        assert result["title"]
        assert result["content_hash"]
        assert result["language"] in ("en", "mixed", "unknown")

    def test_extract_from_text_only(self, extractor):
        fr = SimpleNamespace(html="", text="Plain text content here for testing", url="https://example.com", title="T")
        result = extractor.extract(fr)
        assert result["text"] == "Plain text content here for testing"
        assert result["title"] == "T"

    def test_extract_empty(self, extractor):
        fr = SimpleNamespace(html="", text="", url="", title="")
        result = extractor.extract(fr)
        assert result["text"] == ""
        assert result["content_hash"] == ""


class TestExtractTitle:
    def test_og_title_preferred(self, extractor):
        title = extractor.extract_title(SAMPLE_HTML)
        assert title == "OG Title Here"

    def test_fallback_to_title_tag(self, extractor):
        html = "<html><head><title>Fallback Title - Brand</title></head></html>"
        title = extractor.extract_title(html)
        assert title == "Fallback Title"

    def test_title_with_separator_stripped(self, extractor):
        html = "<html><head><title>My Article | SiteName</title></head></html>"
        title = extractor.extract_title(html)
        assert title == "My Article"

    def test_no_title(self, extractor):
        html = "<html><head></head><body>Hello</body></html>"
        assert extractor.extract_title(html) == ""

    def test_empty_html(self, extractor):
        assert extractor.extract_title("") == ""


class TestExtractLinks:
    def test_extracts_valid_links(self, extractor):
        links = extractor.extract_links(SAMPLE_HTML, base_url="https://example.com")
        urls = set(links)
        assert any("example.com/page1" in u for u in urls)
        assert "https://external.com/page2" in urls

    def test_skips_javascript_links(self, extractor):
        links = extractor.extract_links(SAMPLE_HTML, base_url="https://example.com")
        assert not any("javascript:" in l for l in links)

    def test_skips_anchors(self, extractor):
        links = extractor.extract_links(SAMPLE_HTML, base_url="https://example.com")
        assert not any(l == "#anchor" for l in links)

    def test_skips_mailto(self, extractor):
        links = extractor.extract_links(SAMPLE_HTML, base_url="https://example.com")
        assert not any("mailto:" in l for l in links)

    def test_resolves_relative_urls(self, extractor):
        links = extractor.extract_links(SAMPLE_HTML, base_url="https://example.com")
        assert any("https://example.com/page1" in l for l in links)

    def test_empty_html(self, extractor):
        assert extractor.extract_links("") == []

    def test_deduplication(self, extractor):
        html = '<a href="https://a.com">1</a><a href="https://a.com">2</a>'
        links = extractor.extract_links(html)
        assert len(links) == 1


class TestDetectLanguage:
    def test_chinese(self, extractor):
        assert extractor.detect_language("这是一段中文测试文本内容") == "zh"

    def test_english(self, extractor):
        assert extractor.detect_language("This is an English text") == "en"

    def test_mixed(self, extractor):
        result = extractor.detect_language("Hello你好World世界FooBar测试甲乙")
        assert result in ("zh", "mixed")

    def test_empty(self, extractor):
        assert extractor.detect_language("") == "unknown"

    def test_too_short(self, extractor):
        assert extractor.detect_language("ab") == "unknown"

    def test_numbers_only(self, extractor):
        assert extractor.detect_language("12345") == "unknown"


class TestContentHash:
    def test_hash_computation(self, extractor):
        h = extractor.content_hash("hello world")
        expected = hashlib.sha1(b"hello world").hexdigest()[:16]
        assert h == expected

    def test_hash_length(self, extractor):
        h = extractor.content_hash("test")
        assert len(h) == 16

    def test_different_inputs_different_hashes(self, extractor):
        h1 = extractor.content_hash("text a")
        h2 = extractor.content_hash("text b")
        assert h1 != h2


class TestExtractText:
    def test_strips_scripts(self, extractor):
        text = extractor.extract_text(SAMPLE_HTML)
        assert "console.log" not in text

    def test_strips_styles(self, extractor):
        text = extractor.extract_text(SAMPLE_HTML)
        assert ".hidden" not in text
        assert "display: none" not in text

    def test_preserves_content(self, extractor):
        # Use regex fallback directly to test content preservation
        text = extractor._regex_extract(SAMPLE_HTML, 10000)
        assert "paragraph" in text.lower() or "content" in text.lower()

    def test_empty_html(self, extractor):
        assert extractor.extract_text("") == ""

    def test_regex_fallback(self, extractor):
        html = "<p>Hello &amp; World</p>"
        text = extractor._regex_extract(html, 10000)
        assert "Hello & World" in text


class TestExtractDate:
    def test_meta_date(self, extractor):
        date = extractor.extract_date(SAMPLE_HTML)
        assert date is not None
        assert "2024-06-15" in date

    def test_chinese_date(self, extractor):
        html = '<html><body>发布于2024年3月15日</body></html>'
        date = extractor.extract_date(html)
        assert date == "2024-03-15"

    def test_no_date(self, extractor):
        html = "<html><body>No date here</body></html>"
        assert extractor.extract_date(html) is None

    def test_empty_html(self, extractor):
        assert extractor.extract_date("") is None
