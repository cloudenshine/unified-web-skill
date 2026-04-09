"""Quick DuckDuckGo test."""
import warnings
warnings.filterwarnings("ignore")

from duckduckgo_search import DDGS

with DDGS() as ddgs:
    results = list(ddgs.text("Python asyncio", max_results=3))
    print(f"Results: {len(results)}")
    for r in results:
        title = r.get("title", "?")
        href = r.get("href", "?")
        print(f"  - {title} => {href}")
