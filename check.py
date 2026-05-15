"""Diagnostic entry point for the single v3 MCP router."""
from __future__ import annotations

import asyncio
import sys

from app.mcp_server import _get_engine_manager


def classify_smoke(ok: bool, *, critical: bool = False) -> tuple[str, bool]:
    """Return display status and whether the failure is critical."""
    if ok:
        return "[OK]", False
    if critical:
        return "[FAIL]", True
    return "[WARN]", False


async def main() -> None:
    """Run dependency and low-cost live checks for the v3 router."""
    ok = True
    print("=== unified-web-skill diagnostics ===")
    print("Architecture: v3 engine-manager MCP router")
    print("Entry point: python -m app.mcp_server --stdio\n")

    try:
        em = _get_engine_manager()
    except Exception as exc:
        print(f"[FAIL] EngineManager initialization failed: {exc}")
        sys.exit(1)

    engines = em.list_engines()
    if not engines:
        print("[FAIL] No engines registered")
        sys.exit(1)

    print("Registered engines:")
    for name, caps in engines.items():
        print(f"  {name}: {', '.join(caps)}")
    print()

    print("Provider profiles:")
    for profile in await em.provider_status():
        state = "enabled" if profile["enabled"] else "disabled"
        registered = "registered" if profile["registered"] else "not registered"
        version = profile["version"]
        version_text = version["version"] if version["ok"] else f"version unknown: {version['error']}"
        print(
            f"  {profile['name']} ({profile['category']}): "
            f"{state}, {registered}, {version_text}"
        )
    print()

    print("Checking engine health... ", end="", flush=True)
    try:
        health_map = await em.health_check_all()
        healthy_count = sum(1 for healthy in health_map.values() if healthy)
        label, critical = classify_smoke(healthy_count > 0, critical=True)
        print(f"{label} {healthy_count}/{len(engines)} available")
        ok = ok and not critical
    except Exception as exc:
        label, critical = classify_smoke(False, critical=True)
        print(f"{label} {exc}")
        ok = ok and not critical

    print("Testing fetch smoke (httpbin.org)... ", end="", flush=True)
    try:
        result = await em.fetch_with_fallback(
            "https://httpbin.org/json",
            timeout=10,
            preferred_engines=["scrapling"],
            no_cache=True,
            mode="http",
        )
        label, critical = classify_smoke(result.ok)
        if result.ok:
            print(f"{label} {result.engine} ({result.duration_ms:.0f}ms)")
        else:
            print(f"{label} {result.error} (live network smoke failed)")
        ok = ok and not critical
    except Exception as exc:
        label, critical = classify_smoke(False)
        print(f"{label} {exc} (live network smoke failed)")
        ok = ok and not critical

    print("Testing search smoke... ", end="", flush=True)
    try:
        results = await em.search_multi(
            "test",
            engines=["scrapling"],
            max_results=2,
            language="en",
        )
        label, critical = classify_smoke(bool(results))
        if results:
            print(f"{label} {len(results)} results")
        else:
            print(f"{label} no results (live search smoke failed)")
        ok = ok and not critical
    except Exception as exc:
        label, critical = classify_smoke(False)
        print(f"{label} {exc} (live search smoke failed)")
        ok = ok and not critical

    print()
    if ok:
        print("Critical dependency checks passed. Review WARN lines for live network or optional provider issues.")
        sys.exit(0)

    print("Critical checks FAILED. Fix above issues before starting.")
    sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
