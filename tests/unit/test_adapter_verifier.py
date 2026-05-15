import pytest

from app.discovery.adapter_verifier import (
    AdapterTarget,
    AdapterVerificationResult,
    verify_adapter,
    verify_adapters,
)


async def _ok_runner(site: str, command: str, query: str, *, timeout: int):
    return [
        {"title": "One", "url": f"https://{site}.example/one"},
        {"title": "Two", "url": f"https://{site}.example/two"},
    ]


async def _empty_runner(site: str, command: str, query: str, *, timeout: int):
    return []


async def _error_runner(site: str, command: str, query: str, *, timeout: int):
    raise RuntimeError("adapter timed out")


def test_adapter_verification_result_serializes_to_dict():
    result = AdapterVerificationResult(
        site="youtube",
        command="search",
        adapter="youtube/search",
        query="python asyncio",
        ok=True,
        quality_status="verified",
        result_count=2,
        duration_ms=10.5,
        error="",
    )

    assert result.to_dict()["adapter"] == "youtube/search"


@pytest.mark.asyncio
async def test_verify_adapter_marks_verified_when_enough_results_return():
    target = AdapterTarget(site="reddit", command="search", query="python")

    result = await verify_adapter(target, _ok_runner, min_results=2)

    assert result.ok is True
    assert result.quality_status == "verified"
    assert result.result_count == 2
    assert result.adapter == "reddit/search"


@pytest.mark.asyncio
async def test_verify_adapter_marks_weak_when_result_count_is_too_low():
    target = AdapterTarget(site="bilibili", command="search", query="python")

    result = await verify_adapter(target, _ok_runner, min_results=3)

    assert result.ok is True
    assert result.quality_status == "weak"
    assert result.result_count == 2


@pytest.mark.asyncio
async def test_verify_adapter_marks_failed_for_empty_results():
    target = AdapterTarget(site="youtube", command="search", query="python")

    result = await verify_adapter(target, _empty_runner, min_results=1)

    assert result.ok is False
    assert result.quality_status == "failed"
    assert result.result_count == 0


@pytest.mark.asyncio
async def test_verify_adapter_records_runner_errors():
    target = AdapterTarget(site="youtube", command="search", query="python")

    result = await verify_adapter(target, _error_runner, min_results=1)

    assert result.ok is False
    assert result.quality_status == "failed"
    assert result.error == "adapter timed out"


@pytest.mark.asyncio
async def test_verify_adapters_respects_limit():
    targets = [
        AdapterTarget(site="reddit", command="search", query="python"),
        AdapterTarget(site="youtube", command="search", query="python"),
    ]

    results = await verify_adapters(targets, _ok_runner, limit=1)

    assert [result.adapter for result in results] == ["reddit/search"]
