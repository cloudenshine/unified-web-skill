"""Unified exception hierarchy for the web skill."""


class WebSkillError(Exception):
    """Base exception for all web skill errors."""
    pass


class EngineError(WebSkillError):
    """Error from an engine."""

    def __init__(self, engine: str, message: str, exit_code: int = 0):
        self.engine = engine
        self.exit_code = exit_code
        super().__init__(f"[{engine}] {message}")


class EngineNotAvailableError(EngineError):
    """Engine is not installed or not responding."""
    pass


class EngineTimeoutError(EngineError):
    """Engine operation timed out."""
    pass


class AuthRequiredError(EngineError):
    """Site requires authentication."""
    pass


class BlockedError(EngineError):
    """Request was blocked by anti-bot measures."""
    pass


class ConfigError(WebSkillError):
    """Configuration error."""
    pass


class DiscoveryError(WebSkillError):
    """Error during URL discovery."""
    pass


class ExtractionError(WebSkillError):
    """Error during content extraction."""
    pass


class StorageError(WebSkillError):
    """Error during result storage."""
    pass
