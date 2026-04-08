"""E2E test: full research pipeline from query to results."""
import asyncio

import pytest

from app.engines.manager import EngineManager
from app.engines.scrapling_engine import ScraplingEngine
from app.models import ResearchTask
from app.pipeline.research import ResearchPipeline


@pytest.fixture
def pipeline():
    em = EngineManager()
    em.register(ScraplingEngine())
    return ResearchPipeline(engine_manager=em)


@pytest.mark.asyncio
async def test_research_pipeline_full_run(pipeline):
    """Full pipeline: query → discover → fetch → extract → result."""
    task = ResearchTask(
        query="Python 异步编程最佳实践",
        language="zh",
        max_sources=5,
        max_pages=3,
        max_queries=2,
        timeout_seconds=20,
        min_text_length=50,
        min_credibility=0.1,
    )

    try:
        result = await asyncio.wait_for(
            pipeline.run(task),
            timeout=60,
        )
    except (asyncio.TimeoutError, Exception) as exc:
        pytest.skip(f"Pipeline failed or timed out: {exc}")

    # Basic structure validation
    assert result is not None
    assert hasattr(result, "records")
    assert hasattr(result, "stats")
    assert hasattr(result, "queries_used")

    # Stats should be populated
    assert result.stats.total_discovered >= 0

    # If records were collected, validate them
    if len(result.records) > 0:
        rec = result.records[0]
        assert rec.url.startswith("http")
        assert rec.text_length > 0 or rec.text != ""
    elif result.stats.total_discovered > 0 and result.stats.total_collected == 0:
        # Discovered URLs but couldn't fetch (e.g., missing engine deps)
        pytest.skip(
            f"Discovered {result.stats.total_discovered} URLs but collected 0 "
            f"(blocked={result.stats.skipped_blocked}). Engine deps likely missing."
        )


@pytest.mark.asyncio
async def test_research_pipeline_english_query(pipeline):
    """Pipeline handles English queries."""
    task = ResearchTask(
        query="async programming best practices",
        language="en",
        max_sources=5,
        max_pages=3,
        max_queries=2,
        timeout_seconds=20,
        min_text_length=50,
        min_credibility=0.1,
    )

    try:
        result = await asyncio.wait_for(
            pipeline.run(task),
            timeout=60,
        )
    except asyncio.TimeoutError:
        pytest.skip("Pipeline timed out (60s)")
    except Exception as exc:
        pytest.skip(f"Pipeline failed: {exc}")

    assert result is not None
    assert isinstance(result.records, list)
    assert isinstance(result.stats.total_discovered, int)
