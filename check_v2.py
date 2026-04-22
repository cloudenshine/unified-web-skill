"""Quick diagnostic — run before starting the MCP server."""
import asyncio
import sys

from core.probe import CAPS
from core.rings import r0_http


async def main() -> None:

    ok = True
    print("=== unified-web-skill v2 diagnostics ===\n")

    print(f"Ring 0 (HTTP):     {'[OK] online' if CAPS.ring0 else '[FAIL] OFFLINE'}")
    print(f"Ring 1 (Browser):  {'[OK] online' if CAPS.ring1 else '[OFF] offline (no playwright browsers)'}")
    print(f"Ring 2 (CLI):      {'[OK] online' if CAPS.ring2 else '[OFF] offline (bb-browser + opencli not found)'}")
    print(f"Ring 3 (Pipeline): {'[OK] online' if CAPS.ring3 else '[OFF] offline'}")
    print()

    if CAPS.ring2:
        print(f"  bb-browser: {CAPS.bb_browser_path}")
        print(f"  opencli:    {CAPS.opencli_path}")
        print()

    if not CAPS.ring0:
        print("CRITICAL: Ring 0 is offline. Install httpx: pip install httpx")
        ok = False

    # Quick fetch test
    print("Testing R0 fetch (httpbin.org)... ", end="", flush=True)
    r = await r0_http.fetch("https://httpbin.org/json", timeout=10)
    if r.ok:
        print(f"[OK] ({r.duration_ms:.0f}ms)")
    else:
        print(f"[FAIL] {r.error}")

    # Quick search test
    print("Testing R0 search (duckduckgo)...  ", end="", flush=True)
    results = await r0_http.search("test", max_results=2, language="en")
    if results:
        print(f"[OK] ({len(results)} results)")
    else:
        print("[WARN] no results (check network)")

    print()
    if ok:
        print("All critical checks passed. Server is ready.")
        sys.exit(0)
    else:
        print("Critical checks FAILED. Fix above issues before starting.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
