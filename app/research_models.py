"""research_models.py — Pydantic v2 数据模型"""
from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class ResearchTask(BaseModel):
    query: str
    language: str = "zh"
    max_sources: int = Field(default=20, ge=1, le=200)
    max_pages: int = Field(default=20, ge=1, le=200)
    max_depth: int = Field(default=2, ge=0, le=4)
    max_queries: int = Field(default=5, ge=1, le=20)
    trusted_mode: bool = True
    min_credibility: float = Field(default=0.55, ge=0.0, le=1.0)
    min_text_length: int = Field(default=200, ge=0)
    output_format: str = Field(default="json", pattern="^(json|ndjson|md)$")
    output_path: str = "outputs/research"
    timeout_seconds: int = Field(default=60, ge=1)
    task_id: str | None = None
    opencli_enabled: bool = True
    opencli_preferred_sites: list[str] = Field(default_factory=list)
    opencli_fallback: bool = True
    preferred_tool_order: list[str] = Field(default_factory=lambda: ["opencli", "scrapling"])
    domain_qps: float = Field(default=1.0, gt=0.0)
    max_concurrency: int = Field(default=4, ge=1)
    time_window_days: int = Field(default=0, ge=0)
    include_domains: list[str] = Field(default_factory=list)
    exclude_domains: list[str] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        if self.task_id is None:
            self.task_id = str(uuid.uuid4())


class ResearchRecord(BaseModel):
    url: str
    title: str = ""
    text: str = ""
    summary: str = ""
    credibility: float = 0.5
    fetch_mode: str = ""
    source_type: str = ""
    tool_chain: list[str] = Field(default_factory=list)
    attempts: list[dict] = Field(default_factory=list)
    content_hash: str = ""
    published_at: str | None = None
    text_length: int = 0
    language_detected: str = "unknown"

    def model_post_init(self, __context: Any) -> None:
        if not self.text_length:
            self.text_length = len(self.text)
        if not self.summary and self.text:
            self.summary = self.text[:300].replace("\n", " ")


class ResearchStats(BaseModel):
    discovered: int = 0
    selected: int = 0
    collected: int = 0
    skipped_duplicate: int = 0
    skipped_low_quality: int = 0
    opencli_used: int = 0
    tool_chain_counter: dict[str, int] = Field(default_factory=dict)
    fallback_reason_last: str = ""
    rate_limited_domains: list[str] = Field(default_factory=list)
    avg_fetch_ms: float = 0.0


class ResearchResult(BaseModel):
    task_id: str
    expanded_queries: list[str] = Field(default_factory=list)
    discovered: list[dict] = Field(default_factory=list)
    selected: list[dict] = Field(default_factory=list)
    collected: list[ResearchRecord] = Field(default_factory=list)
    stats: ResearchStats = Field(default_factory=ResearchStats)
    manifest_path: str = ""
    saved: list[str] = Field(default_factory=list)


class Candidate(BaseModel):
    url: str
    canonical_url: str = ""
    score: float = 0.5
    source_type: str = "web"

    def model_post_init(self, __context: Any) -> None:
        if not self.canonical_url:
            self.canonical_url = self.url.split("#")[0].rstrip("/")
