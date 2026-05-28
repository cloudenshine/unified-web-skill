import time

import pytest

from app.engines.bb_browser import _build_fetch_command


class _ProbeEngine:
    def __init__(self, responses):
        self.responses = list(responses)

    async def _run_subprocess(self, cmd, *, timeout=30):
        return self.responses.pop(0)


def test_build_fetch_command_uses_generic_fetch_without_site_command():
    cmd = _build_fetch_command("bb-browser", "https://www.youtube.com/watch?v=abc", {})

    assert cmd == ["bb-browser", "open", "https://www.youtube.com/watch?v=abc", "--json"]


def test_build_fetch_command_uses_site_adapter_with_explicit_command():
    cmd = _build_fetch_command(
        "bb-browser",
        "https://www.youtube.com/watch?v=abc",
        {"command": "search", "args": ["python"]},
    )

    assert cmd == ["bb-browser", "site", "youtube/search", "python", "--json"]


def test_build_fetch_command_maps_youtube_search_url_to_site_adapter():
    cmd = _build_fetch_command(
        "bb-browser",
        "https://www.youtube.com/results?search_query=python+asyncio",
        {},
    )

    assert cmd == ["bb-browser", "site", "youtube/search", "python asyncio", "--json"]


def test_build_fetch_command_maps_reddit_subreddit_url_to_site_adapter():
    cmd = _build_fetch_command(
        "bb-browser",
        "https://www.reddit.com/r/programming/",
        {},
    )

    assert cmd == ["bb-browser", "site", "reddit/hot", "programming", "--json"]


def test_build_fetch_command_rejects_non_http_targets():
    with pytest.raises(ValueError, match="unsupported bb-browser target"):
        _build_fetch_command("bb-browser", "file:///etc/passwd", {})


def test_build_fetch_command_rejects_local_targets():
    with pytest.raises(ValueError, match="refusing local bb-browser target"):
        _build_fetch_command("bb-browser", "http://127.0.0.1:8000", {})


def test_build_fetch_command_rejects_unallowlisted_platform_command():
    with pytest.raises(ValueError, match="unsupported bb-browser command"):
        _build_fetch_command(
            "bb-browser",
            "https://www.youtube.com/watch?v=abc",
            {"command": "watch", "args": ["abc"]},
        )


@pytest.mark.asyncio
async def test_daemon_available_requires_running_status_text():
    from app.engines.bb_browser import BBBrowserEngine

    engine = BBBrowserEngine()
    probe = _ProbeEngine([(0, "Daemon not running", "")])
    engine._run_subprocess = probe._run_subprocess  # type: ignore[method-assign]

    assert await engine._daemon_available() is False


@pytest.mark.asyncio
async def test_health_check_requires_usable_daemon():
    from app.engines.bb_browser import BBBrowserEngine

    engine = BBBrowserEngine()
    probe = _ProbeEngine(
        [
            (0, "Daemon not running", ""),
            (0, "Daemon not running", ""),
        ]
    )
    engine._run_subprocess = probe._run_subprocess  # type: ignore[method-assign]

    assert await engine.health_check() is False


@pytest.mark.asyncio
async def test_fetch_uses_open_eval_close_for_generic_pages():
    from app.engines.bb_browser import BBBrowserEngine

    engine = BBBrowserEngine()
    probe = _ProbeEngine(
        [
            (0, '{"result":{"tabId":"TAB123","tab":"0123","seq":1}}', ""),
            (0, '{"result":{"result":"Example Domain\\nHello world","tab":"0123","seq":2}}', ""),
            (0, '{"result":{"result":"<html><body><h1>Example Domain</h1></body></html>","tab":"0123","seq":3}}', ""),
            (0, '{"result":{"tab":"0123","seq":4}}', ""),
        ]
    )
    engine._run_subprocess = probe._run_subprocess  # type: ignore[method-assign]

    result = await engine.fetch("https://example.com")

    assert result.ok is True
    assert result.text == "Example Domain\nHello world"
    assert result.html == "<html><body><h1>Example Domain</h1></body></html>"
    assert result.metadata == {"tabId": "TAB123"}


@pytest.mark.asyncio
async def test_fetch_rejects_local_targets_before_spawning_browser():
    from app.engines.bb_browser import BBBrowserEngine

    engine = BBBrowserEngine()
    called = False

    async def fake_run_subprocess(cmd, *, timeout=30):
        nonlocal called
        called = True
        return 0, "", ""

    engine._run_subprocess = fake_run_subprocess  # type: ignore[method-assign]

    result = await engine.fetch("http://localhost:3000")

    assert result.ok is False
    assert "refusing local bb-browser target" in result.error
    assert called is False


@pytest.mark.asyncio
async def test_wait_for_tab_text_caps_eval_timeout_to_remaining_budget():
    from app.engines.bb_browser import BBBrowserEngine

    engine = BBBrowserEngine()
    calls: list[int] = []

    async def fake_eval(tab_id, expression, *, timeout):
        calls.append(timeout)
        return ""

    engine._eval_tab = fake_eval  # type: ignore[method-assign]
    started = time.monotonic()

    result = await engine._wait_for_tab_text("TAB123", timeout=30)

    assert result == ""
    assert calls
    assert all(1 <= timeout <= 10 for timeout in calls)
    assert calls[0] <= 10
    assert time.monotonic() - started < 12
