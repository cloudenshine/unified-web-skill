import requests
import json
import sys

url = "http://localhost:8000/mcp"

# research_and_collect call
payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "research_and_collect",
        "arguments": {
            "query": "AI开源项目 GitHub Trending 2026年4月 新工具 新能力 个人盈利方向",
            "language": "zh",
            "max_sources": 8,
            "trusted_mode": True,
            "output_format": "json"
        }
    }
}

print("Calling research_and_collect...", flush=True)
try:
    resp = requests.post(url, json=payload, timeout=90)
    print(f"Status: {resp.status_code}", flush=True)
    data = resp.json()
    print(json.dumps(data, ensure_ascii=False, indent=2)[:5000], flush=True)
except Exception as e:
    print(f"Error: {e}", flush=True)
