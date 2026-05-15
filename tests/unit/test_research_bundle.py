from datetime import datetime, timezone

from app.models import ResearchRecord, ResearchResult, ResearchStats, ResearchTask
from app.pipeline.bundle import ResearchBundleBuilder


def _result(records: list[ResearchRecord]) -> ResearchResult:
    return ResearchResult(
        task=ResearchTask(query="python asyncio"),
        records=records,
        stats=ResearchStats(
            total_discovered=4,
            total_collected=len(records),
            skipped_duplicate=1,
            skipped_quality=1,
            skipped_blocked=1,
            engines_used={"scrapling-http": 2, "bb-browser": 1},
        ),
        queries_used=["python asyncio", "asyncio tutorial"],
    )


def test_bundle_deduplicates_by_canonical_url_and_reports_rejections():
    records = [
        ResearchRecord(
            url="https://example.com/a?utm_source=newsletter",
            title="A",
            text="Python asyncio guide " * 20,
            fetch_engine="scrapling-http",
            fetch_mode="http",
            credibility=0.6,
        ),
        ResearchRecord(
            url="https://example.com/a",
            title="A duplicate",
            text="Python asyncio guide " * 10,
            fetch_engine="bb-browser",
            fetch_mode="dynamic",
            credibility=0.8,
        ),
    ]

    bundle = ResearchBundleBuilder().build(_result(records))

    assert len(bundle["accepted_records"]) == 1
    assert bundle["rejected_records"] == [
        {
            "url": "https://example.com/a",
            "reason": "duplicate_url",
            "duplicate_of": "https://example.com/a",
        }
    ]
    assert bundle["stats"]["rejected_count"] == 1
    assert bundle["stats"]["rejection_reasons"] == {"duplicate_url": 1}


def test_bundle_scores_records_and_orders_highest_first():
    records = [
        ResearchRecord(
            url="https://low.example/article",
            title="Low",
            text="short but acceptable " * 20,
            fetch_engine="scrapling-http",
            credibility=0.3,
        ),
        ResearchRecord(
            url="https://high.example/article",
            title="High",
            text="rich detailed source " * 120,
            fetch_engine="scrapling-http",
            credibility=0.9,
            published_at="2026-05-14",
        ),
    ]

    bundle = ResearchBundleBuilder().build(_result(records))

    accepted = bundle["accepted_records"]
    assert [record["url"] for record in accepted] == [
        "https://high.example/article",
        "https://low.example/article",
    ]
    assert accepted[0]["score"] > accepted[1]["score"]
    assert accepted[0]["score_breakdown"]["credibility"] > accepted[1]["score_breakdown"]["credibility"]


def test_bundle_includes_provider_traces_and_failure_stats():
    records = [
        ResearchRecord(
            url="https://example.com/a",
            title="A",
            text="content " * 80,
            fetch_engine="scrapling-http",
            fetch_mode="http",
            fetch_duration_ms=123.4,
            tool_chain=["scrapling-http"],
            credibility=0.7,
        )
    ]

    bundle = ResearchBundleBuilder().build(_result(records))

    assert bundle["query"] == "python asyncio"
    assert bundle["provider_traces"] == [
        {
            "url": "https://example.com/a",
            "fetch_engine": "scrapling-http",
            "fetch_mode": "http",
            "duration_ms": 123.4,
            "tool_chain": ["scrapling-http"],
        }
    ]
    assert bundle["stats"]["source_count"] == 1
    assert bundle["stats"]["failure_stats"] == {
        "skipped_quality": 1,
        "skipped_duplicate": 1,
        "skipped_blocked": 1,
    }


def test_bundle_scores_recent_sources_above_stale_sources():
    records = [
        ResearchRecord(
            url="https://example.com/stale",
            title="Stale",
            text="same length content " * 120,
            fetch_engine="scrapling-http",
            credibility=0.7,
            published_at="2021-05-14",
        ),
        ResearchRecord(
            url="https://example.com/recent",
            title="Recent",
            text="same length content " * 120,
            fetch_engine="scrapling-http",
            credibility=0.7,
            published_at="2026-05-10",
        ),
    ]

    bundle = ResearchBundleBuilder(
        now=datetime(2026, 5, 14, tzinfo=timezone.utc)
    ).build(_result(records))

    accepted = bundle["accepted_records"]
    assert [record["url"] for record in accepted] == [
        "https://example.com/recent",
        "https://example.com/stale",
    ]
    assert accepted[0]["score_breakdown"]["freshness"] > accepted[1]["score_breakdown"]["freshness"]


def test_bundle_exposes_ranked_citations_for_accepted_records():
    records = [
        ResearchRecord(
            url="https://example.com/a?utm_source=feed",
            title="Source A",
            text="citation source " * 80,
            fetch_engine="scrapling-http",
            fetch_mode="http",
            credibility=0.8,
            published_at="2026-05-14",
        )
    ]

    bundle = ResearchBundleBuilder(
        now=datetime(2026, 5, 14, tzinfo=timezone.utc)
    ).build(_result(records))

    assert bundle["citations"] == [
        {
            "title": "Source A",
            "url": "https://example.com/a?utm_source=feed",
            "canonical_url": "https://example.com/a",
            "published_at": "2026-05-14",
            "provider": "scrapling-http",
            "score": bundle["accepted_records"][0]["score"],
            "summary": bundle["accepted_records"][0]["summary"],
        }
    ]


def test_bundle_calibrates_credibility_for_authoritative_domains():
    records = [
        ResearchRecord(
            url="https://example-blog.test/report",
            title="Blog report",
            text="same evidence body " * 120,
            fetch_engine="scrapling-http",
            credibility=0.6,
            published_at="2026-05-14",
        ),
        ResearchRecord(
            url="https://www.nasa.gov/report",
            title="NASA report",
            text="same evidence body " * 120,
            fetch_engine="scrapling-http",
            credibility=0.6,
            published_at="2026-05-14",
        ),
    ]

    bundle = ResearchBundleBuilder(
        now=datetime(2026, 5, 14, tzinfo=timezone.utc)
    ).build(_result(records))

    accepted = bundle["accepted_records"]
    assert [record["url"] for record in accepted] == [
        "https://www.nasa.gov/report",
        "https://example-blog.test/report",
    ]
    assert accepted[0]["score_breakdown"]["credibility_calibration"] > 0
    assert accepted[1]["score_breakdown"]["credibility_calibration"] == 0


def test_bundle_stats_include_score_summary():
    records = [
        ResearchRecord(
            url="https://low.example/article",
            title="Low",
            text="short but acceptable " * 20,
            fetch_engine="scrapling-http",
            credibility=0.3,
        ),
        ResearchRecord(
            url="https://high.example/article",
            title="High",
            text="rich detailed source " * 120,
            fetch_engine="scrapling-http",
            credibility=0.9,
            published_at="2026-05-14",
        ),
    ]

    bundle = ResearchBundleBuilder(
        now=datetime(2026, 5, 14, tzinfo=timezone.utc)
    ).build(_result(records))
    scores = [record["score"] for record in bundle["accepted_records"]]

    assert bundle["stats"]["score_summary"] == {
        "count": 2,
        "max": max(scores),
        "min": min(scores),
        "avg": round(sum(scores) / len(scores), 4),
        "quality_buckets": {
            "high": 1,
            "medium": 0,
            "low": 1,
        },
    }


def test_bundle_stats_include_language_distribution_for_accepted_records():
    records = [
        ResearchRecord(
            url="https://en.example/article",
            title="English",
            text="global source " * 80,
            fetch_engine="scrapling-http",
            language="en",
        ),
        ResearchRecord(
            url="https://zh.example/article",
            title="Chinese",
            text="global source " * 80,
            fetch_engine="scrapling-http",
            language="zh",
        ),
        ResearchRecord(
            url="https://unknown.example/article",
            title="Unknown",
            text="global source " * 80,
            fetch_engine="scrapling-http",
            language="",
        ),
    ]

    bundle = ResearchBundleBuilder().build(_result(records))

    assert bundle["stats"]["language_distribution"] == {
        "en": 1,
        "unknown": 1,
        "zh": 1,
    }


def test_bundle_stats_include_provider_and_source_type_distribution():
    records = [
        ResearchRecord(
            url="https://api.example/article",
            title="API source",
            text="global source " * 80,
            fetch_engine="scrapling-http",
            source_type="direct",
        ),
        ResearchRecord(
            url="https://adapter.example/article",
            title="Adapter source",
            text="global source " * 80,
            fetch_engine="bb-browser",
            source_type="site_adapter",
        ),
        ResearchRecord(
            url="https://unknown-provider.example/article",
            title="Unknown provider",
            text="global source " * 80,
            fetch_engine="",
            source_type="",
        ),
    ]

    bundle = ResearchBundleBuilder().build(_result(records))

    assert bundle["stats"]["provider_distribution"] == {
        "bb-browser": 1,
        "scrapling-http": 1,
        "unknown": 1,
    }
    assert bundle["stats"]["source_type_distribution"] == {
        "direct": 1,
        "site_adapter": 1,
        "unknown": 1,
    }


def test_bundle_stats_include_domain_distribution_from_canonical_urls():
    records = [
        ResearchRecord(
            url="https://www.example.com/a?utm_source=feed",
            title="Example A",
            text="global source " * 80,
            fetch_engine="scrapling-http",
        ),
        ResearchRecord(
            url="https://example.com/b",
            title="Example B",
            text="global source " * 80,
            fetch_engine="scrapling-http",
        ),
        ResearchRecord(
            url="https://docs.python.org/3/library/asyncio.html",
            title="Python docs",
            text="global source " * 80,
            fetch_engine="scrapling-http",
        ),
    ]

    bundle = ResearchBundleBuilder().build(_result(records))

    assert bundle["stats"]["domain_distribution"] == {
        "docs.python.org": 1,
        "example.com": 2,
    }
