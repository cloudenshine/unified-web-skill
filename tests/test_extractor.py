"""tests/test_extractor.py"""
import pytest
from app.extractor import (
    content_hash,
    extract_date,
    extract_links,
    extract_same_domain_links,
    extract_text,
    build_record,
)

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta name="date" content="2026-01-15">
  <title>Test Article</title>
</head>
<body>
  <nav>Navigation menu here</nav>
  <article>
    <h1>Main Title</h1>
    <p>This is the first paragraph with sufficient content for testing purposes.</p>
    <p>This is the second paragraph with more text content.</p>
  </article>
  <footer>Footer text</footer>
  <a href="/relative/path">Relative link</a>
  <a href="https://external.com/page">External link</a>
  <a href="#anchor">Anchor only</a>
</body>
</html>
"""


class TestExtractText:
    def test_extracts_paragraph_text(self):
        text = extract_text(SAMPLE_HTML)
        assert "first paragraph" in text or "Main Title" in text

    def test_respects_max_chars(self):
        long_html = "<p>" + "a" * 10000 + "</p>"
        text = extract_text(long_html, max_chars=500)
        assert len(text) <= 500

    def test_empty_html(self):
        text = extract_text("")
        assert text == ""

    def test_plain_string_fallback(self):
        text = extract_text("no html here just plain text" * 10)
        assert len(text) > 0

    def test_strips_script_content(self):
        html = "<script>var x = 'malicious';</script><p>Clean content</p>"
        text = extract_text(html)
        # Script content should not appear in text
        assert "malicious" not in text or "Clean content" in text


class TestExtractLinks:
    def test_extracts_absolute_links(self):
        links = extract_links(SAMPLE_HTML, "https://example.com")
        assert "https://external.com/page" in links

    def test_resolves_relative_links(self):
        links = extract_links(SAMPLE_HTML, "https://example.com")
        assert "https://example.com/relative/path" in links

    def test_excludes_anchor_only(self):
        links = extract_links(SAMPLE_HTML, "https://example.com")
        assert not any(link.endswith("#anchor") for link in links)

    def test_deduplication(self):
        html = '<a href="/page">1</a><a href="/page">2</a>'
        links = extract_links(html, "https://example.com")
        assert links.count("https://example.com/page") == 1

    def test_empty_html(self):
        assert extract_links("", "https://example.com") == []


class TestExtractSameDomainLinks:
    def test_filters_to_same_domain(self):
        links = extract_same_domain_links(SAMPLE_HTML, "https://example.com")
        assert all("example.com" in link for link in links)
        assert not any("external.com" in link for link in links)

    def test_www_stripped(self):
        html = '<a href="https://www.example.com/page">link</a>'
        links = extract_same_domain_links(html, "https://example.com")
        assert len(links) >= 1


class TestExtractDate:
    def test_meta_date_tag(self):
        date = extract_date(SAMPLE_HTML)
        assert date is not None
        assert "2026" in date

    def test_iso_date_in_body(self):
        html = "<p>Published on 2025-03-15 in our journal</p>"
        date = extract_date(html)
        assert date is not None
        assert "2025" in date

    def test_chinese_date(self):
        html = "<p>发布日期：2025年3月15日</p>"
        date = extract_date(html)
        assert date is not None

    def test_no_date(self):
        date = extract_date("<p>No date here</p>")
        assert date is None


class TestContentHash:
    def test_consistent_hash(self):
        h1 = content_hash("test text")
        h2 = content_hash("test text")
        assert h1 == h2

    def test_different_texts_different_hash(self):
        h1 = content_hash("text a")
        h2 = content_hash("text b")
        assert h1 != h2

    def test_hash_length(self):
        h = content_hash("hello world")
        assert len(h) == 16


class TestBuildRecord:
    def test_builds_correct_structure(self):
        rec = build_record(
            url="https://example.com/page",
            title="Test Title",
            text="This is a test article with sufficient text content.",
            published_at="2026-01-15",
            fetch_mode="scrapling:http",
            source_type="scrapling",
        )
        assert rec["url"] == "https://example.com/page"
        assert rec["title"] == "Test Title"
        assert rec["fetch_mode"] == "scrapling:http"
        assert rec["source_type"] == "scrapling"
        assert rec["published_at"] == "2026-01-15"
        assert "content_hash" in rec
        assert "language_detected" in rec

    def test_summary_truncated(self):
        long_text = "x" * 500
        rec = build_record("u", "t", long_text, None, "http", "web")
        assert len(rec["summary"]) <= 300

    def test_extra_credibility(self):
        rec = build_record("u", "t", "text", None, "http", "web",
                           extra={"credibility": 0.85})
        assert rec["credibility"] == 0.85
