"""query_planner.py — 查询词扩展（纯离线，不依赖外部 API）"""
from __future__ import annotations

import datetime


def expand_queries(query: str, max_queries: int = 5, language: str = "zh") -> list[str]:
    """
    从原始查询词生成扩展变体列表。
    返回去重后的列表，数量不超过 max_queries。
    """
    query = (query or "").strip()
    if not query:
        return []

    year = datetime.datetime.now(datetime.timezone.utc).year
    variants: list[str] = [query]

    if language == "zh":
        suffixes_zh = [
            f"{query} {year}",
            f"{query} 官方",
            f"{query} 最新",
            f"{query} 研究报告",
            f"{query} 政策",
            f"{query} 分析",
            f"{query} 数据",
        ]
        variants.extend(suffixes_zh)
    else:
        suffixes_en = [
            f"{query} {year}",
            f"{query} latest",
            f"{query} official",
            f"{query} research",
            f"{query} report",
            f"{query} analysis",
            f"{query} statistics",
        ]
        variants.extend(suffixes_en)

    # Always add a cross-language variant
    variants.append(f"{query} site:gov")
    variants.append(f"{query} site:edu")

    # Deduplicate preserving order
    seen: set[str] = set()
    result: list[str] = []
    for v in variants:
        v = v.strip()
        if v and v not in seen:
            seen.add(v)
            result.append(v)
        if len(result) >= max_queries:
            break

    return result
