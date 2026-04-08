"""Tests for app.exceptions — exception hierarchy."""

import pytest
from app.exceptions import (
    WebSkillError,
    EngineError,
    EngineNotAvailableError,
    EngineTimeoutError,
    AuthRequiredError,
    BlockedError,
    ConfigError,
    DiscoveryError,
    ExtractionError,
    StorageError,
)


class TestExceptionHierarchy:
    def test_webskillerror_is_exception(self):
        assert issubclass(WebSkillError, Exception)

    def test_engineerror_is_webskillerror(self):
        assert issubclass(EngineError, WebSkillError)

    def test_engine_not_available(self):
        assert issubclass(EngineNotAvailableError, EngineError)

    def test_engine_timeout(self):
        assert issubclass(EngineTimeoutError, EngineError)

    def test_auth_required(self):
        assert issubclass(AuthRequiredError, EngineError)

    def test_blocked(self):
        assert issubclass(BlockedError, EngineError)

    def test_config_error(self):
        assert issubclass(ConfigError, WebSkillError)

    def test_discovery_error(self):
        assert issubclass(DiscoveryError, WebSkillError)

    def test_extraction_error(self):
        assert issubclass(ExtractionError, WebSkillError)

    def test_storage_error(self):
        assert issubclass(StorageError, WebSkillError)


class TestEngineErrorFields:
    def test_engine_error_attributes(self):
        err = EngineError("scrapling", "connection refused", exit_code=1)
        assert err.engine == "scrapling"
        assert err.exit_code == 1
        assert "scrapling" in str(err)
        assert "connection refused" in str(err)

    def test_engine_error_default_exit_code(self):
        err = EngineError("eng", "msg")
        assert err.exit_code == 0


class TestExceptionsRaisable:
    def test_raise_webskillerror(self):
        with pytest.raises(WebSkillError):
            raise WebSkillError("generic error")

    def test_raise_engineerror(self):
        with pytest.raises(EngineError):
            raise EngineError("eng", "msg")

    def test_raise_engine_not_available(self):
        with pytest.raises(EngineNotAvailableError):
            raise EngineNotAvailableError("eng", "not installed")

    def test_raise_timeout(self):
        with pytest.raises(EngineTimeoutError):
            raise EngineTimeoutError("eng", "timed out")

    def test_raise_blocked(self):
        with pytest.raises(BlockedError):
            raise BlockedError("eng", "403 forbidden")

    def test_raise_config_error(self):
        with pytest.raises(ConfigError):
            raise ConfigError("missing key")

    def test_raise_storage_error(self):
        with pytest.raises(StorageError):
            raise StorageError("disk full")

    def test_catch_as_webskillerror(self):
        """All subclasses should be catchable as WebSkillError."""
        for exc_class in [EngineError, EngineNotAvailableError, EngineTimeoutError,
                          AuthRequiredError, BlockedError, ConfigError,
                          DiscoveryError, ExtractionError, StorageError]:
            try:
                if issubclass(exc_class, EngineError):
                    raise exc_class("eng", "msg")
                else:
                    raise exc_class("msg")
            except WebSkillError:
                pass  # expected
