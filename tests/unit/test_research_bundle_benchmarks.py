import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.models import ResearchRecord, ResearchResult, ResearchStats, ResearchTask
from app.pipeline.bundle import ResearchBundleBuilder


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "research_bundle_benchmarks"


def _result_from_fixture(fixture: dict) -> ResearchResult:
    return ResearchResult(
        task=ResearchTask(**fixture["task"]),
        records=[ResearchRecord(**record) for record in fixture["records"]],
        stats=ResearchStats(**fixture["stats"]),
        queries_used=fixture["queries_used"],
        created_at=fixture["created_at"],
    )


@pytest.mark.parametrize(
    "fixture_name",
    [
        "global_policy_research.json",
        "academic_literature_research.json",
        "package_code_research.json",
        "news_research.json",
    ],
)
def test_research_bundle_regression_benchmark(fixture_name: str):
    fixture = json.loads((FIXTURE_DIR / fixture_name).read_text())
    bundle = ResearchBundleBuilder(
        now=datetime.fromisoformat(fixture["now"]).astimezone(timezone.utc)
    ).build(_result_from_fixture(fixture))

    assert [record["canonical_url"] for record in bundle["accepted_records"]] == fixture[
        "expected"
    ]["accepted_canonical_order"]
    assert bundle["rejected_records"] == fixture["expected"]["rejected_records"]
    assert [citation["canonical_url"] for citation in bundle["citations"]] == fixture[
        "expected"
    ]["citation_canonical_order"]
    assert [
        record["score_breakdown"] for record in bundle["accepted_records"]
    ] == fixture["expected"]["score_breakdowns"]
    assert bundle["stats"] == fixture["expected"]["stats"]
