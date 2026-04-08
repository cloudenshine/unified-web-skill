"""
Intent-aware query expansion.

Generates search variants optimised for each intent type so that
downstream search engines receive well-targeted queries.
No external dependencies — pure string manipulation.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from .intent_classifier import IntentClassifier, QueryIntent

if TYPE_CHECKING:
    pass

_logger = logging.getLogger(__name__)


class QueryPlanner:
    """Expand a raw query into multiple search variants based on intent."""

    def __init__(self, classifier: IntentClassifier | None = None) -> None:
        self._classifier = classifier or IntentClassifier()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def expand(
        self,
        query: str,
        *,
        language: str = "auto",
        max_queries: int = 8,
        intent: QueryIntent | None = None,
    ) -> list[str]:
        """Generate expanded query variants based on intent.

        Parameters
        ----------
        query:
            Original user query.
        language:
            ``"zh"``, ``"en"``, ``"auto"`` (detect).
        max_queries:
            Upper bound on the number of variants to return.
        intent:
            Override intent classification.

        Returns
        -------
        list[str]
            Deduplicated list of query variants.  The original query
            is always first.
        """
        query = query.strip()
        if not query:
            return []

        if language == "auto":
            language = self._classifier.detect_language(query)

        if intent is None:
            intent = self._classifier.classify(query, language=language)

        _logger.debug("expanding query=%r  lang=%s  intent=%s", query, language, intent)

        dispatch = {
            QueryIntent.INFORMATIONAL: self._expand_informational,
            QueryIntent.NEWS:          self._expand_news,
            QueryIntent.ACADEMIC:      self._expand_academic,
            QueryIntent.CODE:          self._expand_code,
            QueryIntent.FINANCE:       self._expand_finance,
            QueryIntent.SOCIAL:        self._expand_social,
            QueryIntent.TRANSACTIONAL: self._expand_transactional,
            QueryIntent.NAVIGATIONAL:  self._expand_navigational,
            QueryIntent.LOCAL:         self._expand_local,
        }

        expander = dispatch.get(intent, self._expand_informational)
        variants = expander(query, language)

        # Deduplicate while preserving order; always start with original.
        seen: set[str] = set()
        result: list[str] = []
        for q in [query, *variants]:
            q_norm = q.strip()
            if q_norm and q_norm not in seen:
                seen.add(q_norm)
                result.append(q_norm)

        return result[:max_queries]

    # ------------------------------------------------------------------
    # Per-intent expanders
    # ------------------------------------------------------------------

    def _expand_informational(self, query: str, lang: str) -> list[str]:
        """Expand informational queries with explanatory framing."""
        variants: list[str] = []
        if lang == "zh":
            variants.extend([
                f"{query} 是什么",
                f"{query} 详解",
                f"{query} 教程",
                f"{query} 原理",
                f"{query} 入门指南",
            ])
        else:
            variants.extend([
                f"what is {query}",
                f"{query} explained",
                f"{query} tutorial",
                f"{query} guide",
                f"{query} overview",
            ])
        return variants

    def _expand_news(self, query: str, lang: str) -> list[str]:
        """Expand news queries with temporal markers."""
        variants: list[str] = []
        if lang == "zh":
            variants.extend([
                f"{query} 最新消息",
                f"{query} 新闻",
                f"{query} 今日",
                f"{query} 动态",
                f"{query} 速报",
            ])
        else:
            variants.extend([
                f"{query} latest news",
                f"{query} today",
                f"{query} update",
                f"{query} breaking",
                f"{query} recent developments",
            ])
        return variants

    def _expand_academic(self, query: str, lang: str) -> list[str]:
        """Expand academic queries with scholarly terms."""
        variants: list[str] = []
        if lang == "zh":
            variants.extend([
                f"{query} 论文",
                f"{query} 研究",
                f"{query} 综述",
                f"{query} 最新进展",
                f"{query} 学术",
            ])
        else:
            variants.extend([
                f"{query} paper",
                f"{query} research",
                f"{query} survey",
                f"{query} arxiv",
                f"{query} study",
            ])
        return variants

    def _expand_code(self, query: str, lang: str) -> list[str]:
        """Expand programming / code queries."""
        variants: list[str] = []
        if lang == "zh":
            variants.extend([
                f"{query} 代码",
                f"{query} 实现",
                f"{query} 示例",
                f"{query} github",
                f"{query} 解决方案",
            ])
        else:
            variants.extend([
                f"{query} example",
                f"{query} implementation",
                f"{query} github",
                f"{query} stackoverflow",
                f"{query} documentation",
            ])
        return variants

    def _expand_finance(self, query: str, lang: str) -> list[str]:
        """Expand finance / market queries."""
        variants: list[str] = []
        if lang == "zh":
            variants.extend([
                f"{query} 行情",
                f"{query} 分析",
                f"{query} 走势",
                f"{query} 财报",
                f"{query} 研报",
            ])
        else:
            variants.extend([
                f"{query} stock price",
                f"{query} analysis",
                f"{query} market",
                f"{query} earnings",
                f"{query} forecast",
            ])
        return variants

    def _expand_social(self, query: str, lang: str) -> list[str]:
        """Expand social-media oriented queries."""
        variants: list[str] = []
        if lang == "zh":
            variants.extend([
                f"{query} 讨论",
                f"{query} 评价",
                f"{query} 热议",
                f"{query} 观点",
                f"{query} 网友",
            ])
        else:
            variants.extend([
                f"{query} discussion",
                f"{query} opinions",
                f"{query} reddit",
                f"{query} twitter",
                f"{query} community",
            ])
        return variants

    def _expand_transactional(self, query: str, lang: str) -> list[str]:
        """Expand buy / download / deal queries."""
        variants: list[str] = []
        if lang == "zh":
            variants.extend([
                f"{query} 价格",
                f"{query} 优惠",
                f"{query} 购买",
                f"{query} 推荐",
                f"{query} 评测",
            ])
        else:
            variants.extend([
                f"{query} price",
                f"{query} review",
                f"{query} best deal",
                f"{query} buy",
                f"{query} comparison",
            ])
        return variants

    def _expand_navigational(self, query: str, lang: str) -> list[str]:
        """Expand navigational queries — keep them minimal."""
        variants: list[str] = []
        if lang == "zh":
            variants.extend([
                f"{query} 官网",
                f"{query} 登录",
            ])
        else:
            variants.extend([
                f"{query} official site",
                f"{query} login",
            ])
        return variants

    def _expand_local(self, query: str, lang: str) -> list[str]:
        """Expand location-based queries."""
        variants: list[str] = []
        if lang == "zh":
            variants.extend([
                f"{query} 推荐",
                f"{query} 排行",
                f"{query} 攻略",
                f"{query} 地址",
                f"{query} 评价",
            ])
        else:
            variants.extend([
                f"{query} near me",
                f"{query} best",
                f"{query} reviews",
                f"{query} directions",
                f"{query} recommendations",
            ])
        return variants
