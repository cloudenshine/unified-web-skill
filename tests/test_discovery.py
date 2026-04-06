"""tests/test_discovery.py — discovery module unit tests (all network calls mocked)"""
from __future__ import annotations

import unittest.mock as mock
import pytest
from app.discovery import discover_from_queries, _filter_url
from app.research_models import Candidate


class TestFilterUrl:
    def test_no_filters_accepts_all(self):
        assert _filter_url("https://example.com/page", [], []) is True

    def test_exclude_domain_rejected(self):
        assert _filter_url("https://spam.com/page", [], ["spam.com"]) is False

    def test_exclude_subdomain_rejected(self):
        assert _filter_url("https://bad.spam.com/page", [], ["spam.com"]) is False

    def test_include_domain_accepted(self):
        assert _filter_url("https://allowed.com/page", ["allowed.com"], []) is True

    def test_non_include_domain_rejected(self):
        assert _filter_url("https://other.com/page", ["allowed.com"], []) is False

    def test_invalid_url_rejected(self):
        assert _filter_url("not-a-url", [], []) is False


class TestDiscoverFromQueries:
    def test_returns_list(self):
        with mock.patch("app.discovery.DDGS") as mock_ddgs:
            mock_ddgs.return_value.__enter__.return_value.text.return_value = []
            result = discover_from_queries(["test query"])
        assert isinstance(result, list)

    def test_ddgs_not_installed_returns_empty(self):
        with mock.patch("app.discovery.DDGS", None):
            result = discover_from_queries(["test"])
        assert result == []

    def test_ddgs_failure_returns_empty(self):
        with mock.patch("app.discovery.DDGS") as mock_ddgs:
            mock_ddgs.return_value.__enter__.return_value.text.side_effect = Exception("network error")
            result = discover_from_queries(["test"])
        assert result == []

    def test_deduplication(self):
        fake_results = [
            {"href": "https://example.com/page"},
            {"href": "https://example.com/page"},  # duplicate
            {"href": "https://other.com/article"},
        ]
        with mock.patch("app.discovery.DDGS") as mock_ddgs:
            mock_ddgs.return_value.__enter__.return_value.text.return_value = fake_results
            result = discover_from_queries(["test query"], max_sources=10)
        urls = [c.canonical_url for c in result]
        assert len(urls) == len(set(urls))

    def test_max_sources_respected(self):
        fake_results = [{"href": f"https://site{i}.com/page"} for i in range(50)]
        with mock.patch("app.discovery.DDGS") as mock_ddgs:
            mock_ddgs.return_value.__enter__.return_value.text.return_value = fake_results
            result = discover_from_queries(["q1", "q2"], max_sources=5)
        assert len(result) <= 5

    def test_returns_candidate_objects(self):
        fake_results = [
            {"href": "https://example.com/article"},
        ]
        with mock.patch("app.discovery.DDGS") as mock_ddgs:
            mock_ddgs.return_value.__enter__.return_value.text.return_value = fake_results
            result = discover_from_queries(["test"])
        assert len(result) >= 1
        assert isinstance(result[0], Candidate)
        assert result[0].url == "https://example.com/article"

    def test_exclude_domains_filtered(self):
        fake_results = [
            {"href": "https://spam.com/page"},
            {"href": "https://good.com/article"},
        ]
        with mock.patch("app.discovery.DDGS") as mock_ddgs:
            mock_ddgs.return_value.__enter__.return_value.text.return_value = fake_results
            result = discover_from_queries(["test"], exclude_domains=["spam.com"])
        assert all("spam.com" not in c.url for c in result)

    def test_empty_queries_returns_empty(self):
        result = discover_from_queries([])
        assert result == []
