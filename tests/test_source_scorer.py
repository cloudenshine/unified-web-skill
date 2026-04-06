"""tests/test_source_scorer.py"""
import pytest
from app.source_scorer import score_credibility


class TestScoreCredibility:
    def test_gov_domain_high_score(self):
        score = score_credibility("https://www.gov.cn/article", trusted_mode=True)
        assert score >= 0.7

    def test_edu_domain_high_score(self):
        score = score_credibility("https://university.edu/paper", trusted_mode=True)
        assert score >= 0.7

    def test_org_domain_higher(self):
        score = score_credibility("https://wikipedia.org/wiki/Python", trusted_mode=True)
        assert score >= 0.8

    def test_http_lower_than_https(self):
        https_score = score_credibility("https://example.com/page", trusted_mode=False)
        http_score = score_credibility("http://example.com/page", trusted_mode=False)
        assert https_score > http_score

    def test_known_academic_high(self):
        score = score_credibility("https://arxiv.org/abs/2301.00001", trusted_mode=True)
        assert score >= 0.9

    def test_known_news_medium(self):
        score = score_credibility("https://reuters.com/article/xyz", trusted_mode=True)
        assert score >= 0.8

    def test_random_com_baseline(self):
        score = score_credibility("https://randomsite123.com/page", trusted_mode=False)
        assert 0.3 <= score <= 0.8

    def test_exclude_domains(self):
        score = score_credibility(
            "https://spam.com/page",
            trusted_mode=True,
            exclude_domains=["spam.com"]
        )
        assert score == 0.0

    def test_include_domains_max_score(self):
        score = score_credibility(
            "https://mysite.com/page",
            trusted_mode=True,
            include_domains=["mysite.com"]
        )
        assert score == 1.0

    def test_empty_url(self):
        score = score_credibility("", trusted_mode=True)
        assert score >= 0.0

    def test_trusted_mode_lowers_low_score(self):
        # trusted_mode=True should penalize low-credibility sites
        score_trust = score_credibility("http://obscure-site.xyz/", trusted_mode=True)
        score_notrust = score_credibility("http://obscure-site.xyz/", trusted_mode=False)
        assert score_trust <= score_notrust

    def test_subdomain_of_gov(self):
        score = score_credibility("https://data.stats.gov.cn/easyquery", trusted_mode=True)
        assert score >= 0.7

    def test_score_in_range(self):
        """All scores must be in [0, 1]"""
        urls = [
            "https://example.com",
            "http://test.org",
            "https://uni.edu",
            "https://news.gov",
            "ftp://old.net",
            "",
        ]
        for url in urls:
            s = score_credibility(url)
            assert 0.0 <= s <= 1.0, f"Score out of range for {url}: {s}"
