# Provider Contracts

## Purpose

This document defines the normalized provider contracts that let the engine layer plug in search, fetch, interaction, and profile backends while keeping agent-facing tools stable.

## Search Provider

```python
class SearchProvider(Protocol):
    async def search(
        self,
        query: str,
        region: str | None = None,
        freshness_days: int | None = None,
        max_results: int = 10,
        **opts: Any,
    ) -> list[SearchResult]: ...
```

## Fetch Provider

```python
class FetchProvider(Protocol):
    async def fetch(
        self,
        url: str,
        *,
        purpose: str,
        prefer_text: bool = True,
        allow_dynamic: bool = False,
        timeout: int = 30,
        **opts: Any,
    ) -> FetchResult: ...
```

## Interact Provider

```python
class InteractProvider(Protocol):
    async def interact(
        self,
        url: str,
        actions: list[dict[str, Any]],
        *,
        profile: str,
        intent: str,
        require_login: bool = False,
        timeout: int = 60,
        **opts: Any,
    ) -> InteractResult: ...
```

## Profile Provider

```python
class ProfileProvider(Protocol):
    async def list_profiles(
        self,
        region: str | None = None,
        tag: str | None = None,
        **opts: Any,
    ) -> list[dict[str, Any]]: ...

    async def use_profile(
        self,
        profile: str,
        reason: str,
        **opts: Any,
    ) -> dict[str, Any]: ...
```

## New Internal Providers

### `CloakManagerEngine`
- Capability: internal profile/session authority
- Agent-facing role: backing provider for `web_profile_list` and `web_profile_use`

### `CloakBrowserEngine`
- Capability: `INTERACT` and optional `FETCH`
- Agent-facing role: backing provider for `web_interact`

## Compatibility Requirement

New providers should match the existing v3 result objects:
- `SearchResult`
- `FetchResult`
- `InteractResult`

This keeps the MCP layer, tracing, and bundle-building stable while provider ownership changes underneath.

