"""tests/test_heuristics.py"""
import pytest
from app.heuristics import (
    auto_route,
    body_blocked,
    is_interactive_text,
    url_js_hint,
    score_domain_trust,
    extract_domain,
)


class TestIsInteractiveText:
    def test_chinese_keywords(self):
        assert is_interactive_text("请点击这里登录") is True
        assert is_interactive_text("填写表单后提交") is True
        assert is_interactive_text("勾选同意条款") is True
        assert is_interactive_text("下一页查看更多") is True
        assert is_interactive_text("加载更多内容") is True
        assert is_interactive_text("输入验证码") is True

    def test_english_keywords(self):
        assert is_interactive_text("click the button") is True
        assert is_interactive_text("fill in the form") is True
        assert is_interactive_text("login to continue") is True
        assert is_interactive_text("submit the form") is True
        assert is_interactive_text("scroll down to load more") is True
        assert is_interactive_text("select an option from dropdown") is True
        assert is_interactive_text("captcha verification required") is True

    def test_non_interactive(self):
        assert is_interactive_text("今天天气不错") is False
        assert is_interactive_text("read this article") is False
        assert is_interactive_text("") is False
        assert is_interactive_text(None) is False  # type: ignore

    def test_case_insensitive(self):
        assert is_interactive_text("CLICK HERE") is True
        assert is_interactive_text("LOGIN REQUIRED") is True


class TestUrlJsHint:
    def test_js_framework_hints(self):
        assert url_js_hint("https://example.com/__next/static/") is True
        assert url_js_hint("https://app.com/react-app") is True
        assert url_js_hint("https://site.com/webpack.js") is True

    def test_no_js_hint(self):
        assert url_js_hint("https://example.com/article") is False
        assert url_js_hint("https://blog.com/post/123") is False
        assert url_js_hint("") is False


class TestAutoRoute:
    def test_interactive_task_returns_pinchtab(self):
        assert auto_route("https://example.com", "请点击登录") == "pinchtab"
        assert auto_route("https://example.com", "fill in the form") == "pinchtab"

    def test_js_url_returns_dynamic(self):
        assert auto_route("https://spa.com/__next/page", "fetch data") == "dynamic"

    def test_plain_returns_http(self):
        assert auto_route("https://example.com/article", "获取文章内容") == "http"

    def test_interactive_takes_priority_over_js(self):
        # interactive task should return pinchtab even if URL has JS hints
        result = auto_route("https://spa.com/__next/page", "click submit button")
        assert result == "pinchtab"


class TestBodyBlocked:
    def test_detects_cloudflare(self):
        assert body_blocked("just a moment... cloudflare ray id: abc123") is True
        assert body_blocked("ddos protection by cloudflare") is True

    def test_detects_captcha(self):
        assert body_blocked("please complete this captcha") is True

    def test_detects_bot_detection(self):
        assert body_blocked("you are detected as a bot") is True
        assert body_blocked("we detected you are a bot") is True

    def test_normal_content(self):
        assert body_blocked("This is a normal article about technology.") is False
        assert body_blocked("") is False

    def test_case_insensitive(self):
        assert body_blocked("ACCESS DENIED to this resource") is True


class TestScoreDomainTrust:
    def test_gov_domain(self):
        assert score_domain_trust("https://www.gov.cn/article") >= 0.8

    def test_edu_domain(self):
        assert score_domain_trust("https://example.edu/paper") >= 0.8

    def test_known_trusted(self):
        assert score_domain_trust("https://arxiv.org/abs/123") >= 0.9
        assert score_domain_trust("https://wikipedia.org/wiki/Python") >= 0.9

    def test_commercial_domain(self):
        score = score_domain_trust("https://randomsite.com/page")
        assert 0.4 <= score <= 0.7

    def test_extract_domain(self):
        assert extract_domain("https://www.example.com/path") == "example.com"
        assert extract_domain("https://sub.example.co.uk") == "sub.example.co.uk"
