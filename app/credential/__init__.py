"""Cookie / credential management for unified-web-skill.

Provides a structured YAML/JSON config layer, browser cookie extraction,
optional encryption, and credential injection into engine subprocesses.
"""

from .config import CredentialStore, mask_value
from .inject import env_for_url, env_for_platform, cookie_header_for_platform, platform_for_url
from .extractor import (
    CookieExtractionError,
    extract_for_domain,
    extract_for_platform,
    extract_all,
    extract_to_store,
    import_from_agent_reach,
)

__all__ = [
    "CredentialStore",
    "mask_value",
    "CookieExtractionError",
    "extract_for_domain",
    "extract_for_platform",
    "extract_all",
    "extract_to_store",
    "import_from_agent_reach",
]

