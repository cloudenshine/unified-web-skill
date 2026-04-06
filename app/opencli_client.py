"""opencli_client.py — OpenCLI 异步子进程客户端"""
from __future__ import annotations

import asyncio
import json
import logging

from . import config

logger = logging.getLogger(__name__)


async def run_opencli(
    site: str,
    command: str,
    args: list[str] | None = None,
    timeout_seconds: int | None = None,
) -> dict:
    """
    异步调用 opencli 子进程。

    返回结构:
    {
        "ok": bool,
        "exit_code": int,
        "stdout": str,
        "stderr": str,
        "parsed": dict,   # 若 stdout 为 JSON 则解析，否则 {}
    }
    exit_code 78 表示 opencli 二进制未找到（FileNotFoundError）
    """
    args = args or []
    timeout = timeout_seconds or config.OPENCLI_TIMEOUT_SECONDS
    cmd = [config.OPENCLI_BIN, site, command] + args

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=float(timeout)
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return {
                "ok": False,
                "exit_code": 75,  # TEMPFAIL
                "stdout": "",
                "stderr": f"timeout after {timeout}s",
                "parsed": {},
            }

        stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
        stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
        exit_code = proc.returncode or 0

        parsed: dict = {}
        if stdout:
            try:
                parsed = json.loads(stdout)
            except Exception:
                pass

        return {
            "ok": exit_code == 0,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "parsed": parsed,
        }

    except FileNotFoundError:
        logger.debug("opencli binary not found: %s", config.OPENCLI_BIN)
        return {
            "ok": False,
            "exit_code": 78,  # NOT_FOUND
            "stdout": "",
            "stderr": f"binary not found: {config.OPENCLI_BIN}",
            "parsed": {},
        }
    except Exception as exc:
        logger.warning("opencli unexpected error: %s", exc)
        return {
            "ok": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": str(exc),
            "parsed": {},
        }
