"""Tests for app.utils — rate_limiter, retry, heuristics, scoring."""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, patch

from app.utils.rate_limiter import DomainRateLimiter
from app.utils.retry import RetryPolicy, retry_with_backoff
from app.utils.heuristics import (
    is_interactive_task,
    is_blocked_response,
    is_js_heavy,
    suggest_fetch_mode,
    extract_domain,
)
from app.utils.scoring import score_credibility


# ── DomainRateLimiter ────────────────────────────────────────────────

class TestDomainRateLimiter:
    @pytest.mark.asyncio
    async def test_basic_acquire(self):
        rl = DomainRateLimiter(default_qps=100.0)
        await rl.acquire("example.com")  # should not block

    @pytest.mark.asyncio
    async def test_per_domain_isolation(self):
        rl = DomainRateLimiter(default_qps=100.0)
        await rl.acquire("a.com")
        await rl.acquire("b.com")  # different domain, no wait

    @pytest.mark.asyncio
    async def test_rate_limiting_delay(self):
        rl = DomainRateLimiter(default_qps=2.0)  # 0.5s interval
        await rl.acquire("slow.com")
        t0 = time.monotonic()
        await rl.acquire("slow.com")
        elapsed = time.monotonic() - t0
        assert elapsed >= 0.3  # should have waited ~0.5s (with some tolerance)

    @pytest.mark.asyncio
    async def test_custom_qps(self):
        rl = DomainRateLimiter(default_qps=1.0)
        await rl.acquire("fast.com", qps=1000.0)  # very high QPS
        t0 = time.monotonic()
        await rl.acquire("fast.com", qps=1000.0)
        elapsed = time.monotonic() - t0
        assert elapsed < 0.1  # should be nearly instant

    def test_reset_domain(self):
        rl = DomainRateLimiter()
        rl._last_request["a.com"] = time.monotonic()
        rl.reset("a.com")
        assert "a.com" not in rl._last_request

    def test_reset_all(self):
        rl = DomainRateLimiter()
        rl._last_request["a.com"] = time.monotonic()
        rl._last_request["b.com"] = time.monotonic()
        rl.reset()
        assert len(rl._last_request) == 0


# ── RetryPolicy ──────────────────────────────────────────────────────

class TestRetryPolicy:
    def test_defaults(self):
        p = RetryPolicy()
        assert p.max_attempts == 3
        assert p.base_delay == 1.0
        assert p.max_delay == 30.0
        assert p.jitter is True

    def test_delay_for_attempt_increases(self):
        p = RetryPolicy(base_delay=1.0, exponential_base=2.0, jitter=False)
        d0 = p.delay_for_attempt(0)
        d1 = p.delay_for_attempt(1)
        d2 = p.delay_for_attempt(2)
        assert d0 == 1.0
        assert d1 == 2.0
        assert d2 == 4.0

    def test_delay_capped_at_max(self):
        p = RetryPolicy(base_delay=1.0, exponential_base=2.0, max_delay=5.0, jitter=False)
        d10 = p.delay_for_attempt(10)
        assert d10 == 5.0

    def test_jitter_adds_randomness(self):
        p = RetryPolicy(base_delay=1.0, jitter=True)
        delays = {p.delay_for_attempt(0) for _ in range(20)}
        # With jitter, delays should vary
        assert len(delays) > 1


class TestRetryWithBackoff:
    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        fn = AsyncMock(return_value="ok")
        result = await retry_with_backoff(fn)
        assert result == "ok"
        assert fn.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_then_success(self):
        fn = AsyncMock(side_effect=[ValueError("fail"), ValueError("fail"), "ok"])
        policy = RetryPolicy(max_attempts=3, base_delay=0.01, jitter=False)
        result = await retry_with_backoff(fn, policy=policy)
        assert result == "ok"
        assert fn.call_count == 3

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        fn = AsyncMock(side_effect=ValueError("always fail"))
        policy = RetryPolicy(max_attempts=2, base_delay=0.01, jitter=False)
        with pytest.raises(ValueError, match="always fail"):
            await retry_with_backoff(fn, policy=policy)
        assert fn.call_count == 2

    @pytest.mark.asyncio
    async def test_non_retryable_error(self):
        fn = AsyncMock(side_effect=TypeError("type error"))
        policy = RetryPolicy(max_attempts=3, base_delay=0.01, retryable_errors=(ValueError,))
        with pytest.raises(TypeError):
            await retry_with_backoff(fn, policy=policy)
        assert fn.call_count == 1


# ── Heuristics ───────────────────────────────────────────────────────

class TestIsInteractiveTask:
    def test_chinese_keywords(self):
        assert is_interactive_task("帮我点击登录按钮") is True
        assert is_interactive_task("帮我填写表单") is True

    def test_english_keywords(self):
        assert is_interactive_task("click the login button") is True
        assert is_interactive_task("scroll to bottom") is True

    def test_no_interactive(self):
        assert is_interactive_task("search for Python tutorials") is False


class TestIsBlockedResponse:
    def test_blocked_status_code(self):
        assert is_blocked_response(403) is True
        assert is_blocked_response(429) is True

    def test_ok_status_code(self):
        assert is_blocked_response(200) is False

    def test_blocked_body(self):
        assert is_blocked_response(200, "Access Denied - Please verify") is True
        assert is_blocked_response(200, "just a moment checking your browser") is True

    def test_clean_body(self):
        assert is_blocked_response(200, "Hello world, welcome to our site") is False


class TestIsJsHeavy:
    def test_react_in_html(self):
        assert is_js_heavy("https://example.com", "<div id='__next'>") is True

    def test_vue_in_html(self):
        assert is_js_heavy("https://example.com", "<div id='app' data-v>vue</div>") is True

    def test_plain_html(self):
        assert is_js_heavy("https://example.com", "<p>Hello world</p>") is False

    def test_framework_in_url(self):
        assert is_js_heavy("https://gatsby-site.com/page") is True


class TestSuggestFetchMode:
    def test_interactive_task(self):
        assert suggest_fetch_mode("https://a.com", task_text="click login") == "pinchtab"

    def test_chinese_site(self):
        assert suggest_fetch_mode("https://zhihu.com", is_chinese=True) == "dynamic"

    def test_js_heavy_url(self):
        assert suggest_fetch_mode("https://react-app.com") == "dynamic"

    def test_default_http(self):
        assert suggest_fetch_mode("https://example.com") == "http"


class TestExtractDomain:
    def test_full_url(self):
        assert extract_domain("https://www.example.com/path") == "www.example.com"

    def test_no_scheme(self):
        assert extract_domain("example.com/path") == "example.com"

    def test_empty(self):
        assert extract_domain("") == ""


# ── Scoring ──────────────────────────────────────────────────────────

class TestScoreCredibility:
    def test_https_bonus(self):
        http_score = score_credibility("http://example.com")
        https_score = score_credibility("https://example.com")
        assert https_score > http_score

    def test_trusted_domain_high(self):
        score = score_credibility("https://arxiv.org/abs/2301.00001")
        assert score >= 0.7

    def test_gov_domain(self):
        score = score_credibility("https://data.gov.cn/resource")
        assert score >= 0.7

    def test_known_media(self):
        score = score_credibility("https://nytimes.com/article")
        assert score >= 0.5

    def test_known_tech(self):
        score = score_credibility("https://github.com/user/repo")
        assert score >= 0.5

    def test_unknown_domain_baseline(self):
        score = score_credibility("http://random-site.xyz")
        assert 0.3 <= score <= 0.6

    def test_trusted_mode_penalty(self):
        normal = score_credibility("http://random.xyz")
        trusted = score_credibility("http://random.xyz", trusted_mode=True)
        # trusted mode should penalise low-score domains
        assert trusted <= normal

    def test_score_capped_at_one(self):
        # Even with all bonuses, should not exceed 1.0
        score = score_credibility("https://arxiv.org")
        assert score <= 1.0

    def test_empty_url(self):
        score = score_credibility("")
        assert isinstance(score, float)
