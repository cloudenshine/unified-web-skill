from app.engines.base import Capability
from app.engines.provider_config import (
    ProviderProfile,
    default_provider_profiles,
    enabled_provider_names,
)


def test_provider_profile_normalizes_capabilities():
    profile = ProviderProfile(
        name="example",
        category="local-http",
        capabilities={Capability.FETCH, "search"},
    )

    assert profile.capability_values == ["fetch", "search"]


def test_default_provider_profiles_include_local_baseline():
    profiles = default_provider_profiles()
    names = [profile.name for profile in profiles]

    assert names[:3] == ["cloakbrowser", "opencli", "scrapling"]
    assert "scrapling" in enabled_provider_names(profiles)


def test_enabled_provider_names_respects_flags():
    profiles = [
        ProviderProfile("enabled", "local-http", {Capability.FETCH}, enabled=True),
        ProviderProfile("disabled", "hosted", {Capability.SEARCH}, enabled=False),
    ]

    assert enabled_provider_names(profiles) == ["enabled"]

