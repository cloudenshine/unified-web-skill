"""Provider metadata and default enablement for the engine layer."""

from __future__ import annotations

from dataclasses import dataclass

from .base import Capability
from .. import config


@dataclass(frozen=True)
class ProviderProfile:
    """Declarative description of a fetch/search/browser provider."""

    name: str
    category: str
    capabilities: set[Capability | str]
    enabled: bool = True
    optional: bool = True
    description: str = ""
    # ――― Provider plugin / API provider fields ―――
    api_key_env: str = ""       # Env var name for the API key (e.g. "JINA_API_KEY")
    base_url: str = ""          # API endpoint base URL
    cost_per_fetch: float = 0.0 # Estimated USD per fetch call
    free_tier: bool = True      # Whether a free tier is available
    module_path: str = ""       # Python import path for dynamic loading, e.g. "app.engines.providers.jina_reader:JinaReaderEngine"

    @property
    def capability_values(self) -> list[str]:
        """Return stable string capability names for diagnostics and docs."""
        values = [
            cap.value if isinstance(cap, Capability) else str(cap)
            for cap in self.capabilities
        ]
        return sorted(values)

    @property
    def is_api_provider(self) -> bool:
        """True if this provider connects via HTTP API rather than local binary/library."""
        return bool(self.api_key_env or self.base_url)

    @property
    def has_api_key(self) -> bool:
        """True if the API key env var is set."""
        if not self.api_key_env:
            return True  # no key needed
        import os
        return bool(os.environ.get(self.api_key_env))


def default_provider_profiles() -> list[ProviderProfile]:
    """Return the built-in provider profiles in registration priority order."""
    return [


        ProviderProfile(
            name="cloakbrowser",
            category="local-browser",
            capabilities={Capability.FETCH, Capability.INTERACT},
            enabled=config.CLOAK_BROWSER_ENABLED,
            description="Primary browser interaction provider backed by CloakBrowser.",
            module_path="app.engines.cloak_browser:CloakBrowserEngine",
        ),

        ProviderProfile(
            name="opencli",
            category="local-cli",
            capabilities={Capability.FETCH, Capability.SEARCH, Capability.STRUCTURED},
            enabled=config.OPENCLI_ENABLED,
            description="Local CLI adapters for supported sites.",
            module_path="app.engines.opencli:OpenCLIEngine",
        ),
        ProviderProfile(
            name="scrapling",
            category="local-http",
            capabilities={Capability.FETCH, Capability.SEARCH},
            enabled=True,
            optional=False,
            description="Default free local HTTP extraction and discovery provider.",
            module_path="app.engines.scrapling_engine:ScraplingEngine",
        ),



    ]


def enabled_provider_names(profiles: list[ProviderProfile]) -> list[str]:
    """Return provider names whose profiles are enabled."""
    return [profile.name for profile in profiles if profile.enabled]
