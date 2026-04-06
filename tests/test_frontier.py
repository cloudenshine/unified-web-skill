"""tests/test_frontier.py"""
import pytest
from app.frontier import Candidate, Frontier


class TestFrontier:
    def test_push_pop_priority_order(self):
        frontier = Frontier()
        frontier.push(Candidate(url="https://low.com/", score=0.3))
        frontier.push(Candidate(url="https://high.com/", score=0.9))
        frontier.push(Candidate(url="https://mid.com/", score=0.6))

        first = frontier.pop()
        second = frontier.pop()
        third = frontier.pop()

        assert first.canonical_url == "https://high.com"
        assert second.canonical_url == "https://mid.com"
        assert third.canonical_url == "https://low.com"

    def test_empty_pop_returns_none(self):
        frontier = Frontier()
        assert frontier.pop() is None

    def test_is_empty(self):
        frontier = Frontier()
        assert frontier.is_empty() is True
        frontier.push(Candidate(url="https://example.com/", score=0.5))
        assert frontier.is_empty() is False

    def test_len(self):
        frontier = Frontier()
        assert len(frontier) == 0
        frontier.push(Candidate(url="https://a.com/", score=0.5))
        frontier.push(Candidate(url="https://b.com/", score=0.7))
        assert len(frontier) == 2

    def test_idempotent_dedup(self):
        frontier = Frontier()
        pushed1 = frontier.push(Candidate(url="https://example.com/page", score=0.5))
        pushed2 = frontier.push(Candidate(url="https://example.com/page", score=0.9))
        assert pushed1 is True
        assert pushed2 is False
        assert len(frontier) == 1

    def test_canonical_url_dedup(self):
        """URLs with trailing slash or fragment are deduplicated"""
        frontier = Frontier()
        frontier.push(Candidate(url="https://example.com/page/", score=0.5))
        pushed = frontier.push(Candidate(url="https://example.com/page", score=0.9))
        assert pushed is False

    def test_already_fetched_excluded(self):
        already = {"https://example.com/page"}
        frontier = Frontier(already_fetched=already)
        pushed = frontier.push(Candidate(url="https://example.com/page#fragment", score=0.9))
        assert pushed is False

    def test_already_fetched_does_not_block_new_urls(self):
        already = {"https://example.com/page"}
        frontier = Frontier(already_fetched=already)
        pushed = frontier.push(Candidate(url="https://example.com/other", score=0.5))
        assert pushed is True

    def test_seen_count(self):
        frontier = Frontier()
        frontier.push(Candidate(url="https://a.com/", score=0.5))
        frontier.push(Candidate(url="https://a.com/", score=0.6))  # dup
        frontier.push(Candidate(url="https://b.com/", score=0.4))
        assert frontier.seen_count() == 2

    def test_candidate_canonical_url(self):
        c = Candidate(url="https://example.com/page/#section")
        assert c.canonical_url == "https://example.com/page"
