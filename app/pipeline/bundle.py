"""Research bundle assembly and scoring helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from ..models import ResearchRecord, ResearchResult


TRACKING_PREFIXES = ("utm_",)
TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref"}


class ResearchBundleBuilder:
    """Build a structured research bundle from a pipeline result."""

    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime.now(timezone.utc)
        if self._now.tzinfo is None:
            self._now = self._now.replace(tzinfo=timezone.utc)

    def build(self, result: ResearchResult) -> dict:
        """Return accepted records, rejected records, traces, and bundle stats."""
        accepted_records: list[dict] = []
        rejected_records: list[dict] = []
        provider_traces: list[dict] = []
        source_type_by_url: dict[str, str] = {}
        seen_urls: set[str] = set()

        for record in result.records:
            canonical_url = self._canonicalize_url(record.url)
            if canonical_url in seen_urls:
                rejected_records.append(
                    {
                        "url": record.url,
                        "reason": "duplicate_url",
                        "duplicate_of": canonical_url,
                    }
                )
                continue
            seen_urls.add(canonical_url)

            score, breakdown = self._score_record(record)
            accepted_records.append(
                {
                    "url": record.url,
                    "canonical_url": canonical_url,
                    "title": record.title,
                    "summary": record.summary,
                    "published_at": record.published_at,
                    "language": record.language,
                    "credibility": record.credibility,
                    "score": score,
                    "score_breakdown": breakdown,
                }
            )
            source_type_by_url[record.url] = record.source_type
            provider_traces.append(
                {
                    "url": record.url,
                    "fetch_engine": record.fetch_engine,
                    "fetch_mode": record.fetch_mode,
                    "duration_ms": record.fetch_duration_ms,
                    "tool_chain": list(record.tool_chain),
                }
            )

        accepted_records.sort(key=lambda item: item["score"], reverse=True)
        provider_traces.sort(
            key=lambda trace: next(
                (
                    idx
                    for idx, item in enumerate(accepted_records)
                    if item["url"] == trace["url"]
                ),
                len(accepted_records),
            )
        )
        citations = [
            {
                "title": record["title"],
                "url": record["url"],
                "canonical_url": record["canonical_url"],
                "published_at": record["published_at"],
                "provider": next(
                    (
                        trace["fetch_engine"]
                        for trace in provider_traces
                        if trace["url"] == record["url"]
                    ),
                    "",
                ),
                "score": record["score"],
                "summary": record["summary"],
            }
            for record in accepted_records
        ]

        return {
            "query": result.task.query,
            "created_at": result.created_at,
            "queries_used": list(result.queries_used),
            "accepted_records": accepted_records,
            "rejected_records": rejected_records,
            "provider_traces": provider_traces,
            "citations": citations,
            "stats": {
                "source_count": len(accepted_records),
                "rejected_count": len(rejected_records),
                "engines_used": dict(result.stats.engines_used),
                "failure_stats": {
                    "skipped_quality": result.stats.skipped_quality,
                    "skipped_duplicate": result.stats.skipped_duplicate,
                    "skipped_blocked": result.stats.skipped_blocked,
                },
                "rejection_reasons": self._rejection_reason_counts(rejected_records),
                "language_distribution": self._language_distribution(
                    accepted_records
                ),
                "provider_distribution": self._distribution(
                    provider_traces, "fetch_engine"
                ),
                "source_type_distribution": self._distribution(
                    [
                        {"source_type": source_type_by_url.get(record["url"], "")}
                        for record in accepted_records
                    ],
                    "source_type",
                ),
                "domain_distribution": self._domain_distribution(
                    accepted_records
                ),
                "score_summary": self._score_summary(accepted_records),
            },
        }

    @staticmethod
    def _canonicalize_url(url: str) -> str:
        parsed = urlparse(url)
        query_params = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key not in TRACKING_PARAMS
            and not any(key.startswith(prefix) for prefix in TRACKING_PREFIXES)
        ]
        normalized_path = parsed.path.rstrip("/") or parsed.path
        return urlunparse(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                normalized_path,
                "",
                urlencode(query_params, doseq=True),
                "",
            )
        )

    def _score_record(self, record: ResearchRecord) -> tuple[float, dict[str, float]]:
        base_credibility = max(0.0, min(1.0, float(record.credibility)))
        credibility_adjustment = self._credibility_adjustment(record)
        calibrated_credibility = min(1.0, base_credibility + credibility_adjustment)
        credibility = calibrated_credibility * 0.55
        credibility_calibration = (calibrated_credibility - base_credibility) * 0.55
        length_score = min(1.0, record.text_length / 4000) * 0.25
        freshness = self._freshness_score(record.published_at)
        provider = 0.1 if record.fetch_engine else 0.0
        total = round(credibility + length_score + freshness + provider, 4)
        return total, {
            "credibility": round(credibility, 4),
            "credibility_calibration": round(credibility_calibration, 4),
            "content_length": round(length_score, 4),
            "freshness": freshness,
            "provider_trace": provider,
        }

    @staticmethod
    def _credibility_adjustment(record: ResearchRecord) -> float:
        host = urlparse(record.url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]

        adjustment = 0.0
        if host.endswith((".gov", ".edu", ".mil", ".int")):
            adjustment += 0.08
        if record.source_type == "site_adapter":
            adjustment += 0.03
        if record.fetch_mode.startswith(("api", "rss")):
            adjustment += 0.02
        return min(0.12, adjustment)

    def _freshness_score(self, published_at: str | None) -> float:
        if not published_at:
            return 0.0
        published = self._parse_published_at(published_at)
        if not published:
            return 0.0

        age_days = max(0, (self._now - published).days)
        if age_days <= 30:
            return 0.1
        if age_days <= 365:
            return 0.07
        if age_days <= 1095:
            return 0.04
        return 0.01

    @staticmethod
    def _score_summary(records: list[dict]) -> dict[str, float | int | dict[str, int]]:
        if not records:
            return {
                "count": 0,
                "max": 0.0,
                "min": 0.0,
                "avg": 0.0,
                "quality_buckets": {"high": 0, "medium": 0, "low": 0},
            }
        scores = [float(record["score"]) for record in records]
        return {
            "count": len(scores),
            "max": round(max(scores), 4),
            "min": round(min(scores), 4),
            "avg": round(sum(scores) / len(scores), 4),
            "quality_buckets": {
                "high": sum(1 for score in scores if score >= 0.8),
                "medium": sum(1 for score in scores if 0.6 <= score < 0.8),
                "low": sum(1 for score in scores if score < 0.6),
            },
        }

    @staticmethod
    def _rejection_reason_counts(records: list[dict]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in records:
            reason = str(record.get("reason") or "unknown")
            counts[reason] = counts.get(reason, 0) + 1
        return counts

    @staticmethod
    def _language_distribution(records: list[dict]) -> dict[str, int]:
        return ResearchBundleBuilder._distribution(records, "language")

    @staticmethod
    def _distribution(records: list[dict], field: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in records:
            value = str(record.get(field) or "unknown").strip() or "unknown"
            counts[value] = counts.get(value, 0) + 1
        return counts

    @staticmethod
    def _domain_distribution(records: list[dict]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in records:
            host = urlparse(str(record.get("canonical_url") or "")).netloc.lower()
            if host.startswith("www."):
                host = host[4:]
            host = host or "unknown"
            counts[host] = counts.get(host, 0) + 1
        return counts

    @staticmethod
    def _parse_published_at(value: str) -> datetime | None:
        normalized = value.strip()
        if not normalized:
            return None
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            try:
                parsed = datetime.strptime(normalized[:10], "%Y-%m-%d")
            except ValueError:
                return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
