"""Tests for app.config — configuration from environment variables."""

import os
import pytest
from unittest.mock import patch


class TestConfigDefaults:
    def test_default_values(self):
        # Re-import with clean env to test defaults
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)

            assert cfg.MCP_HOST == "0.0.0.0"
            assert cfg.MCP_PORT == 8000
            assert cfg.OPENCLI_BIN == "opencli"
            assert cfg.OPENCLI_TIMEOUT == 30
            assert cfg.DEFAULT_LANGUAGE == "zh"
            assert cfg.DEFAULT_MAX_SOURCES == 30
            assert cfg.DEFAULT_MAX_PAGES == 20
            assert cfg.OUTPUT_DIR == "outputs"

    def test_opencli_enabled_default(self):
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert cfg.OPENCLI_ENABLED is True

    def test_lp_cdp_url_default(self):
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert cfg.LP_CDP_URL == "ws://127.0.0.1:9222"

    def test_optional_browser_providers_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert cfg.LP_ENABLED is False
            assert cfg.CLIBROWSER_ENABLED is False


class TestConfigFromEnv:
    def test_mcp_port_from_env(self):
        with patch.dict(os.environ, {"MCP_PORT": "9999"}, clear=True):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert cfg.MCP_PORT == 9999

    def test_opencli_disabled(self):
        with patch.dict(os.environ, {"RESEARCH_OPENCLI_ENABLED": "false"}, clear=True):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert cfg.OPENCLI_ENABLED is False

    def test_optional_browser_providers_can_be_enabled(self):
        with patch.dict(
            os.environ,
            {"LP_ENABLED": "true", "CLIBROWSER_ENABLED": "true"},
            clear=True,
        ):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert cfg.LP_ENABLED is True
            assert cfg.CLIBROWSER_ENABLED is True

    def test_custom_output_dir(self):
        with patch.dict(os.environ, {"OUTPUT_DIR": "custom_outputs"}, clear=True):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert cfg.OUTPUT_DIR == "custom_outputs"

    def test_default_qps_from_env(self):
        with patch.dict(os.environ, {"DEFAULT_QPS": "5.0"}, clear=True):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert cfg.DEFAULT_QPS == 5.0

    def test_engine_priority_from_env(self):
        with patch.dict(os.environ, {"ENGINE_PRIORITY": "a,b,c"}, clear=True):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert cfg.ENGINE_PRIORITY == ["a", "b", "c"]
