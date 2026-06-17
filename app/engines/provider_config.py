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

    @property
    def capability_values(self) -> list[str]:
        """Return stable string capability names for diagnostics and docs."""
        values = [
            cap.value if isinstance(cap, Capability) else str(cap)
            for cap in self.capabilities
        ]
        return sorted(values)


def default_provider_profiles() -> list[ProviderProfile]:
    """Return the built-in provider profiles in registration priority order."""
    return [


        ProviderProfile(
            name="cloakbrowser",
            category="local-browser",
            capabilities={Capability.FETCH, Capability.INTERACT},
            enabled=config.CLOAK_BROWSER_ENABLED,
            description="Primary browser interaction provider backed by CloakBrowser.",
        ),

        ProviderProfile(
            name="opencli",
            category="local-cli",
            capabilities={Capability.FETCH, Capability.SEARCH, Capability.STRUCTURED},
            enabled=config.OPENCLI_ENABLED,
            description="Local CLI adapters for supported sites.",
        ),
        ProviderProfile(
            name="scrapling",
            category="local-http",
            capabilities={Capability.FETCH, Capability.SEARCH},
            enabled=True,
            optional=False,
            description="Default free local HTTP extraction and discovery provider.",
        ),



    ]


def enabled_provider_names(profiles: list[ProviderProfile]) -> list[str]:
    """Return provider names whose profiles are enabled."""
    return [profile.name for profile in profiles if profile.enabled]
