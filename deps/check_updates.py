"""
deps/check_updates.py — 外部依赖版本更新检查器。

检查三个关键依赖（scrapling, opencli, cloakbrowser）是否有新版本，
输出差异报告和升级建议。可独立运行，也可集成到 CI/cron。

用法:
    python deps/check_updates.py
    python deps/check_updates.py --json    # 机器可读输出
"""

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

# 锁文件路径
LOCK_FILE = REPO_ROOT / "deps" / "versions.lock.json"

# 每个依赖的版本获取方式
CHECKERS = {
    "scrapling": {
        "label": "Scrapling (Python 包，64K⭐)",
        "check_cmd": [sys.executable, "-m", "pip", "index", "versions", "scrapling"],
        "parse": lambda out: _parse_pip_versions(out, "scrapling"),
        "changelog": "https://github.com/D4Vinci/Scrapling/releases",
    },
    "opencli": {
        "label": "OpenCLI @jackwener/opencli (npm，24.6K⭐)",
        "check_cmd": ["npm", "view", "@jackwener/opencli", "version"],
        "parse": lambda out: {"latest": out.strip()},
        "changelog": "https://github.com/jackwener/OpenCLI/releases",
    },
    "cloakbrowser": {
        "label": "CloakBrowser (独立二进制，26K⭐)",
        "check_cmd": None,  # 手动检查（非 pip/npm 包）
        "parse": lambda out: {"latest": "（需手动访问 GitHub Releases）"},
        "changelog": "https://github.com/CloakHQ/CloakBrowser/releases",
    },
}


def _parse_pip_versions(output: str, package: str) -> dict:
    """从 pip index versions 输出中提取版本信息。"""
    lines = output.strip().splitlines()
    versions = []
    for line in lines:
        line = line.strip()
        if line.startswith("Available versions:"):
            versions_str = line.split(":", 1)[1].strip()
            versions = [v.strip() for v in versions_str.split(",")]
        elif line.startswith("  INSTALLED:"):
            installed = line.split(":", 1)[1].strip()
    return {
        "installed": versions[0] if versions else "unknown",
        "latest": versions[0] if versions else "unknown",
        "all": versions,
    }


def load_lock() -> dict:
    """加载当前版本锁文件。"""
    if not LOCK_FILE.exists():
        print(f"[WARN] 锁文件不存在: {LOCK_FILE}")
        return {"scrapling": {}, "opencli": {}, "cloakbrowser": {}}
    with open(LOCK_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def check_dependency(name: str, checker: dict) -> dict:
    """检查单个依赖的版本。"""
    result = {
        "name": name,
        "label": checker["label"],
        "changelog": checker["changelog"],
        "latest": "未知",
        "current": "未知",
        "needs_update": False,
        "error": None,
    }

    cmd = checker.get("check_cmd")
    if cmd is None:
        result["latest"] = "（需手动检查 GitHub Releases）"
        result["notes"] = "CloakBrowser 是独立二进制，非 pip/npm 包。请手动访问 changelog 链接。"
        return result

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            result["error"] = proc.stderr.strip()[:200]
            return result

        info = checker["parse"](proc.stdout)
        result["latest"] = info.get("latest", "未知")
        result["all_versions"] = info.get("all", [])
    except FileNotFoundError:
        result["error"] = f"命令未找到: {cmd[0]}。请确保已安装。"
    except subprocess.TimeoutExpired:
        result["error"] = "检查超时（30s）"
    except Exception as e:
        result["error"] = str(e)

    return result


def format_report(results: list[dict], lock: dict) -> str:
    """格式化输出报告。"""
    lines = []
    lines.append("=" * 60)
    lines.append("  unified-web-skill 外部依赖更新检查报告")
    lines.append(f"  检查时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 60)

    has_update = False
    for r in results:
        lines.append("")
        lines.append(f"  [{r['name']}] {r['label']}")
        lines.append(f"    当前锁定: {lock.get(r['name'], {}).get('version', '未知')}")
        lines.append(f"    最新可用: {r['latest']}")
        lines.append(f"    Changelog: {r['changelog']}")

        if r.get("error"):
            lines.append(f"    ⚠️ 错误: {r['error']}")
        elif r.get("latest", "").startswith("（需手动"):
            lines.append(f"    ℹ️  {r.get('notes', '')}")
        elif r["latest"] != "未知":
            current = str(lock.get(r["name"], {}).get("version", ""))
            latest = str(r["latest"])
            if current and latest and current != latest:
                lines.append(f"    🔄 有新版本可用！{current} → {latest}")
                has_update = True
            else:
                lines.append(f"    ✅ 已是最新版本")

        if r.get("all_versions"):
            lines.append(f"    所有可用版本: {', '.join(r['all_versions'][:10])}{'...' if len(r['all_versions']) > 10 else ''}")

    lines.append("")
    lines.append("-" * 60)

    updates_needed = sum(1 for r in results if r.get("needs_update"))
    errors = sum(1 for r in results if r.get("error"))

    if has_update:
        lines.append(f"  🔔 {updates_needed} 个依赖有新版本可用")
    if errors:
        lines.append(f"  ⚠️  {errors} 个检查失败")
    if not has_update and not errors:
        lines.append(f"  ✅ 所有依赖已是最新")
    lines.append("=" * 60)

    return "\n".join(lines)


def main():
    lock = load_lock()
    results = []

    for name, checker in CHECKERS.items():
        result = check_dependency(name, checker)

        # 判断是否需要更新
        current = str(lock.get(name, {}).get("version", ""))
        latest = str(result.get("latest", ""))
        if current and latest and current != latest and not latest.startswith("（需"):
            result["needs_update"] = True

        results.append(result)

    if "--json" in sys.argv:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(format_report(results, lock))

    # 退出码：有更新返回 0（信息性），错误返回 2
    if any(r.get("error") for r in results):
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
