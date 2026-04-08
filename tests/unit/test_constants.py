"""Tests for app.constants — constant values and integrity."""

import pytest
from app.constants import (
    BLOCK_MARKERS,
    BLOCKED_STATUS_CODES,
    CHINESE_DOMAINS,
    TRUSTED_DOMAINS,
    KNOWN_MEDIA,
    KNOWN_TECH,
    INTERACTIVE_KEYWORDS,
    INTERACTIVE_KEYWORDS_ZH,
    INTERACTIVE_KEYWORDS_EN,
    JS_FRAMEWORK_HINTS,
    FETCH_MODE_HTTP,
    FETCH_MODE_DYNAMIC,
    FETCH_MODE_STEALTH,
    FETCH_MODE_PINCHTAB,
)


class TestBlockMarkers:
    def test_non_empty(self):
        assert len(BLOCK_MARKERS) > 0

    def test_all_lowercase(self):
        for m in BLOCK_MARKERS:
            assert m == m.lower(), f"BLOCK_MARKER should be lowercase: {m}"

    def test_no_duplicates(self):
        assert len(BLOCK_MARKERS) == len(set(BLOCK_MARKERS))


class TestBlockedStatusCodes:
    def test_non_empty(self):
        assert len(BLOCKED_STATUS_CODES) > 0

    def test_contains_common_codes(self):
        assert 403 in BLOCKED_STATUS_CODES
        assert 429 in BLOCKED_STATUS_CODES

    def test_is_set(self):
        assert isinstance(BLOCKED_STATUS_CODES, set)


class TestChineseDomains:
    def test_non_empty(self):
        assert len(CHINESE_DOMAINS) > 0

    def test_no_duplicates(self):
        assert len(CHINESE_DOMAINS) == len(set(CHINESE_DOMAINS))

    def test_known_domains_present(self):
        assert "bilibili.com" in CHINESE_DOMAINS
        assert "zhihu.com" in CHINESE_DOMAINS
        assert "baidu.com" in CHINESE_DOMAINS


class TestTrustedDomains:
    def test_non_empty(self):
        assert len(TRUSTED_DOMAINS) > 0

    def test_is_set(self):
        assert isinstance(TRUSTED_DOMAINS, set)

    def test_contains_gov(self):
        assert "gov.cn" in TRUSTED_DOMAINS

    def test_no_duplicates(self):
        # Sets don't have duplicates inherently
        assert isinstance(TRUSTED_DOMAINS, set)


class TestKnownMedia:
    def test_non_empty(self):
        assert len(KNOWN_MEDIA) > 0

    def test_is_set(self):
        assert isinstance(KNOWN_MEDIA, set)


class TestKnownTech:
    def test_non_empty(self):
        assert len(KNOWN_TECH) > 0

    def test_contains_github(self):
        assert "github.com" in KNOWN_TECH


class TestInteractiveKeywords:
    def test_combined_length(self):
        assert len(INTERACTIVE_KEYWORDS) == len(INTERACTIVE_KEYWORDS_ZH) + len(INTERACTIVE_KEYWORDS_EN)

    def test_zh_non_empty(self):
        assert len(INTERACTIVE_KEYWORDS_ZH) > 0

    def test_en_non_empty(self):
        assert len(INTERACTIVE_KEYWORDS_EN) > 0


class TestJsFrameworkHints:
    def test_non_empty(self):
        assert len(JS_FRAMEWORK_HINTS) > 0

    def test_contains_react(self):
        assert "react" in JS_FRAMEWORK_HINTS


class TestFetchModes:
    def test_modes_are_strings(self):
        assert isinstance(FETCH_MODE_HTTP, str)
        assert isinstance(FETCH_MODE_DYNAMIC, str)
        assert isinstance(FETCH_MODE_STEALTH, str)
        assert isinstance(FETCH_MODE_PINCHTAB, str)

    def test_mode_values(self):
        assert FETCH_MODE_HTTP == "http"
        assert FETCH_MODE_DYNAMIC == "dynamic"
        assert FETCH_MODE_STEALTH == "stealth"
        assert FETCH_MODE_PINCHTAB == "pinchtab"
