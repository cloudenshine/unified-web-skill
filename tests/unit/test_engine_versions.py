from unittest.mock import AsyncMock

import pytest

from app.engines.bb_browser import BBBrowserEngine
from app.engines.clibrowser import CLIBrowserEngine
from app.engines.opencli import OpenCLIEngine
from app.engines.scrapling_engine import ScraplingEngine


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("engine_cls", "expected_cmd"),
    [
        (BBBrowserEngine, ["bb-browser", "--version"]),
        (OpenCLIEngine, ["opencli", "--version"]),
        (CLIBrowserEngine, ["clibrowser", "--version"]),
    ],
)
async def test_cli_engine_version_info_uses_version_command(engine_cls, expected_cmd):
    engine = engine_cls()
    engine._version_from_command = AsyncMock(  # type: ignore[method-assign]
        return_value={"ok": True, "version": "tool 1.0.0", "error": ""}
    )

    info = await engine.version_info()

    assert info["ok"] is True
    engine._version_from_command.assert_awaited_once_with(
        expected_cmd,
        provider=engine.name,
        timeout=5,
    )


@pytest.mark.asyncio
async def test_scrapling_version_info_uses_installed_package_metadata():
    engine = ScraplingEngine()

    info = await engine.version_info()

    assert set(info) == {"ok", "version", "error"}
    assert isinstance(info["ok"], bool)
