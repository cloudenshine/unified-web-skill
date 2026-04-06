"""research_pipeline.py — 核心研究流水线"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from .config import (
    RESEARCH_OPENCLI_ENABLED,
    RESEARCH_OPENCLI_FALLBACK,
    SCRAPLING_TIMEOUT,
)
from .discovery import discover_from_queries
from .extractor import build_record, extract_date, extract_text
from .frontier import Candidate as FrontierCandidate, Frontier
from .opencli_client import run_opencli
from .opencli_exit_handler import evaluate_opencli_failure
from .opencli_router_integration import get_router
from .quality_validator import deduplicate_by_hash, validate_content
from .query_planner import expand_queries
from .rate_limiter import DomainRateLimiter
from .research_models import (
    Candidate,
    ResearchRecord,
    ResearchResult,
    ResearchStats,
    ResearchTask,
)
from .scrapling_engine import fetch_with_fallback
from .source_scorer import score_credibility
from .storage import save_research

logger = logging.getLogger(__name__)


def _extract_domain(url: str) -> str:
    from urllib.parse import urlparse
    try:
        return urlparse(url).netloc.removeprefix("www.")
    except Exception:
        return url


class ResearchPipeline:
    def __init__(self) -> None:
        self._rate_limiter = DomainRateLimiter(default_qps=1.0)

    async def _fetch_via_opencli(
        self,
        url: str,
        task: ResearchTask,
        stats: ResearchStats,
    ) -> tuple[dict | None, list[dict]]:
        """
        尝试通过 OpenCLI 抓取。返回 (record_dict_or_None, attempts_list)。
        """
        router = get_router()
        match = router.get_opencli_command(url)
        if not match:
            return None, []

        site, command = match
        attempts: list[dict] = []
        fallback_enabled = task.opencli_fallback and RESEARCH_OPENCLI_FALLBACK

        for attempt_idx in range(3):
            t0 = time.monotonic()
            cli_result = await run_opencli(site, command, timeout_seconds=task.timeout_seconds)
            dur = (time.monotonic() - t0) * 1000

            decision = evaluate_opencli_failure(
                exit_code=cli_result["exit_code"],
                attempt=attempt_idx,
                fallback_enabled=fallback_enabled,
                stderr=cli_result["stderr"],
                stdout=cli_result["stdout"],
            )
            attempts.append({
                "engine": f"opencli:{site}/{command}",
                "exit_code": cli_result["exit_code"],
                "ok": cli_result["ok"],
                "duration_ms": dur,
                "label": decision.label,
            })

            if cli_result["ok"] and cli_result["stdout"]:
                stats.opencli_used += 1
                stats.tool_chain_counter["opencli"] = stats.tool_chain_counter.get("opencli", 0) + 1
                text = cli_result["stdout"]
                rec = build_record(
                    url=url,
                    title=cli_result["parsed"].get("title", ""),
                    text=text,
                    published_at=cli_result["parsed"].get("published_at"),
                    fetch_mode=f"opencli:{site}/{command}",
                    source_type="opencli",
                    extra={
                        "credibility": score_credibility(url, task.trusted_mode),
                        "tool_chain": ["opencli"],
                    },
                )
                rec["attempts"] = attempts
                return rec, attempts

            stats.fallback_reason_last = decision.label
            if not decision.should_retry:
                break
            await asyncio.sleep(1.0 * (attempt_idx + 1))

        return None, attempts

    async def _fetch_via_scrapling(
        self,
        url: str,
        task: ResearchTask,
        stats: ResearchStats,
        prior_attempts: list[dict] | None = None,
    ) -> dict | None:
        """
        通过 Scrapling 多级引擎抓取。返回 record_dict 或 None。
        """
        domain = _extract_domain(url)
        await self._rate_limiter.acquire(domain, qps=task.domain_qps)

        t0 = time.monotonic()
        fetch_result = await fetch_with_fallback(
            url=url,
            task_text=task.query,
            first="auto",
            timeout=SCRAPLING_TIMEOUT,
        )
        dur = (time.monotonic() - t0) * 1000

        attempts = list(prior_attempts or [])
        attempts.append({
            "engine": fetch_result.engine,
            "status": fetch_result.status,
            "ok": fetch_result.ok,
            "duration_ms": dur,
        })

        if not fetch_result.ok or not fetch_result.html:
            stats.tool_chain_counter["scrapling_fail"] = (
                stats.tool_chain_counter.get("scrapling_fail", 0) + 1
            )
            # Track rate-limited domains
            if fetch_result.status == 429 and domain not in stats.rate_limited_domains:
                stats.rate_limited_domains.append(domain)
            return None

        text = extract_text(fetch_result.html, max_chars=8000)
        published_at = extract_date(fetch_result.html)

        stats.tool_chain_counter["scrapling"] = stats.tool_chain_counter.get("scrapling", 0) + 1

        rec = build_record(
            url=url,
            title="",
            text=text,
            published_at=published_at,
            fetch_mode=f"scrapling:{fetch_result.route}",
            source_type="scrapling",
            extra={
                "credibility": score_credibility(url, task.trusted_mode,
                                                  task.include_domains,
                                                  task.exclude_domains),
                "tool_chain": [t["engine"] for t in attempts],
            },
        )
        rec["attempts"] = attempts
        return rec

    async def _process_url(
        self,
        url: str,
        task: ResearchTask,
        stats: ResearchStats,
    ) -> dict | None:
        """处理单个 URL，按 preferred_tool_order 尝试"""
        tool_order = task.preferred_tool_order or ["opencli", "scrapling"]
        opencli_enabled = task.opencli_enabled and RESEARCH_OPENCLI_ENABLED

        opencli_attempts: list[dict] = []
        rec: dict | None = None

        for tool in tool_order:
            if tool == "opencli" and opencli_enabled:
                rec, opencli_attempts = await self._fetch_via_opencli(url, task, stats)
                if rec:
                    return rec
                # If fallback not enabled, skip scrapling
                if not task.opencli_fallback:
                    return None

            elif tool == "scrapling":
                rec = await self._fetch_via_scrapling(url, task, stats, opencli_attempts)
                if rec:
                    return rec

        return rec

    async def run(self, task: ResearchTask) -> ResearchResult:
        """
        主流水线：
        1. 扩展查询词
        2. 搜索发现候选 URL
        3. 评分入队
        4. 并发抓取（最大 max_concurrency）
        5. 质量验证 & 去重
        6. 落盘
        """
        stats = ResearchStats()
        already_fetched: set[str] = set()

        # 幂等重跑：若传入 task_id，尝试从已保存结果中提取已抓 URL
        if task.task_id:
            import glob as _glob, json as _json, os as _os
            pattern = _os.path.join(task.output_path, f"*{task.task_id}*manifest*.json")
            for f in _glob.glob(pattern):
                try:
                    with open(f, encoding="utf-8") as fh:
                        m = _json.load(fh)
                    already_fetched.update(m.get("fetched_urls", []))
                except Exception:
                    pass

        # Step 1: 扩展查询词
        queries = expand_queries(task.query, task.max_queries, task.language)
        logger.info("Expanded to %d queries", len(queries))

        # Step 2: 搜索发现
        candidates = discover_from_queries(
            queries=queries,
            max_sources=task.max_sources,
            trusted_mode=task.trusted_mode,
            include_domains=task.include_domains or [],
            exclude_domains=task.exclude_domains or [],
            min_credibility=0.0,
        )
        stats.discovered = len(candidates)
        logger.info("Discovered %d candidates", stats.discovered)

        # Step 3: 评分入队（优先队列）
        frontier = Frontier(already_fetched=already_fetched)
        for c in candidates:
            credibility = score_credibility(
                c.url, task.trusted_mode, task.include_domains, task.exclude_domains
            )
            if credibility < task.min_credibility:
                continue
            fc = FrontierCandidate(url=c.url, score=credibility)
            frontier.push(fc)

        stats.selected = len(frontier)
        logger.info("Selected %d candidates into frontier", stats.selected)

        discovered_dicts = [c.model_dump() for c in candidates]
        selected_dicts: list[dict] = []

        # Step 4: 并发抓取
        collected_records: list[dict] = []
        semaphore = asyncio.Semaphore(task.max_concurrency)
        fetch_times: list[float] = []

        async def _guarded_fetch(candidate: FrontierCandidate) -> dict | None:
            async with semaphore:
                t0 = time.monotonic()
                rec = await self._process_url(candidate.url, task, stats)
                fetch_times.append((time.monotonic() - t0) * 1000)
                return rec

        tasks_to_run: list[Any] = []
        count = 0
        while not frontier.is_empty() and count < task.max_pages:
            fc = frontier.pop()
            if fc is None:
                break
            selected_dicts.append({"url": fc.url, "score": fc.score})
            tasks_to_run.append(_guarded_fetch(fc))
            count += 1

        results_raw = await asyncio.gather(*tasks_to_run, return_exceptions=True)

        for r in results_raw:
            if isinstance(r, Exception):
                logger.warning("fetch exception: %s", r)
                continue
            if r is not None:
                collected_records.append(r)

        # Step 5: 质量验证
        validated: list[dict] = []
        for rec in collected_records:
            ok, reason = validate_content(
                rec.get("text", ""),
                published_at=rec.get("published_at"),
                min_text_length=task.min_text_length,
                time_window_days=task.time_window_days,
            )
            if ok:
                validated.append(rec)
            else:
                stats.skipped_low_quality += 1
                logger.debug("Skipped %s: %s", rec.get("url", ""), reason)

        # 去重
        deduped = deduplicate_by_hash(validated)
        stats.skipped_duplicate = len(validated) - len(deduped)
        stats.collected = len(deduped)

        if fetch_times:
            stats.avg_fetch_ms = sum(fetch_times) / len(fetch_times)

        # 转换为 ResearchRecord
        collected_models = [ResearchRecord(**r) for r in deduped]

        result = ResearchResult(
            task_id=task.task_id or "",
            expanded_queries=queries,
            discovered=discovered_dicts,
            selected=selected_dicts,
            collected=collected_models,
            stats=stats,
        )

        # Step 6: 落盘
        try:
            save_info = save_research(
                result,
                output_path=task.output_path,
                output_format=task.output_format,
                task_id=task.task_id,
            )
            result.manifest_path = save_info["manifest_path"]
            result.saved = save_info["saved"]
        except Exception as exc:
            logger.warning("Storage failed: %s", exc)

        logger.info(
            "Pipeline done: discovered=%d selected=%d collected=%d",
            stats.discovered, stats.selected, stats.collected
        )
        return result
