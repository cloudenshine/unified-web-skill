import pytest

from app.engines.bb_browser import _build_fetch_command


class _ProbeEngine:
    def __init__(self, responses):
        self.responses = list(responses)

    async def _run_subprocess(self, cmd, *, timeout=30):
        return self.responses.pop(0)


def test_build_fetch_command_uses_generic_fetch_without_site_command():
    cmd = _build_fetch_command("bb-browser", "https://www.youtube.com/watch?v=abc", {})

    assert cmd == ["bb-browser", "fetch", "https://www.youtube.com/watch?v=abc"]


def test_build_fetch_command_uses_site_adapter_with_explicit_command():
    cmd = _build_fetch_command(
        "bb-browser",
        "https://www.youtube.com/watch?v=abc",
        {"command": "search", "args": ["python"]},
    )

    assert cmd == ["bb-browser", "site", "youtube/search", "python", "--json"]


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
