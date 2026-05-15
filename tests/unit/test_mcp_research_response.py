from app.mcp_server import _research_response_payload
from app.models import ResearchRecord, ResearchResult, ResearchStats, ResearchTask


def test_research_response_payload_includes_backward_compatible_fields_and_bundle():
    result = ResearchResult(
        task=ResearchTask(query="python asyncio"),
        records=[
            ResearchRecord(
                url="https://example.com/a",
                title="A",
                text="content " * 80,
                fetch_engine="scrapling-http",
                fetch_mode="http",
                credibility=0.7,
            )
        ],
        stats=ResearchStats(total_discovered=1, total_collected=1),
        queries_used=["python asyncio"],
        output_files=["outputs/example.json"],
    )

    payload = _research_response_payload(result, query="python asyncio", duration_ms=12.3)

    assert payload["ok"] is True
    assert payload["query"] == "python asyncio"
    assert len(payload["records"]) == 1
    assert payload["stats"]["total_collected"] == 1
    assert payload["queries_used"] == ["python asyncio"]
    assert payload["output_files"] == ["outputs/example.json"]
    assert payload["duration_ms"] == 12.3
    assert payload["bundle"]["accepted_records"][0]["url"] == "https://example.com/a"
    assert payload["bundle"]["provider_traces"][0]["fetch_engine"] == "scrapling-http"
