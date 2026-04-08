"""Pydantic v2 data models for research tasks and results."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ResearchTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str
    language: str = "zh"
    max_sources: int = Field(default=30, ge=1, le=500)
    max_pages: int = Field(default=20, ge=1, le=200)
    max_queries: int = Field(default=8, ge=1, le=30)
    max_concurrency: int = Field(default=5, ge=1, le=20)
    timeout_seconds: int = Field(default=30, ge=5, le=300)

    # Engine preferences
    preferred_engines: list[str] = Field(default_factory=list)
    search_engines: list[str] = Field(default_factory=list)
    enable_site_adapters: bool = True
    enable_stealth: bool = False

    # Quality filters
    min_text_length: int = Field(default=100, ge=0)
    min_credibility: float = Field(default=0.3, ge=0.0, le=1.0)
    trusted_mode: bool = False
    time_window_days: int = Field(default=0, ge=0)  # 0 = no filter

    # Domain filters
    include_domains: list[str] = Field(default_factory=list)
    exclude_domains: list[str] = Field(default_factory=list)

    # Output
    output_format: str = "json"  # json | ndjson | md
    output_dir: str = "outputs"


class ResearchRecord(BaseModel):
    url: str
    title: str = ""
    text: str = ""
    summary: str = ""
    published_at: Optional[str] = None
    language: str = "unknown"
    content_hash: str = ""
    text_length: int = 0

    # Metadata
    fetch_engine: str = ""
    fetch_mode: str = ""  # e.g., "opencli:bilibili/hot"
    fetch_duration_ms: float = 0
    credibility: float = 0.5
    source_type: str = ""  # "search" | "site_adapter" | "direct"
    tool_chain: list[str] = Field(default_factory=list)
    extra: dict = Field(default_factory=dict)

    def model_post_init(self, __context) -> None:
        if not self.text_length and self.text:
            self.text_length = len(self.text)
        if not self.summary and self.text:
            self.summary = self.text[:300].strip()


class ResearchStats(BaseModel):
    total_discovered: int = 0
    total_collected: int = 0
    total_skipped: int = 0
    skipped_quality: int = 0
    skipped_duplicate: int = 0
    skipped_blocked: int = 0

    engines_used: dict[str, int] = Field(default_factory=dict)
    search_engines_used: list[str] = Field(default_factory=list)
    fallback_count: int = 0
    avg_fetch_ms: float = 0
    total_duration_s: float = 0


class ResearchResult(BaseModel):
    task: ResearchTask
    records: list[ResearchRecord] = Field(default_factory=list)
    stats: ResearchStats = Field(default_factory=ResearchStats)
    queries_used: list[str] = Field(default_factory=list)
    output_files: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
