"""quality_validator.py — 内容质量验证（长度/语言/时效）"""
import re
from datetime import datetime, timedelta, timezone


def validate_content(
    text: str,
    published_at: str | None = None,
    min_text_length: int = 200,
    time_window_days: int = 0,
) -> tuple[bool, str]:
    """
    Returns (passed, rejection_reason).
    rejection_reason is empty string when passed=True.
    """
    # 1. Length check
    clean = re.sub(r"\s+", " ", text or "").strip()
    if len(clean) < min_text_length:
        return False, f"text_too_short:{len(clean)}<{min_text_length}"

    # 2. Staleness check (only when time_window_days > 0 and date parseable)
    if time_window_days > 0 and published_at:
        try:
            normalized = (
                published_at
                .replace("年", "-")
                .replace("月", "-")
                .replace("日", "")
                .strip("-")
                .strip()
            )
            # Try ISO format first, then zero-pad for non-padded dates like 2020-1-1
            pub = None
            for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z",
                        "%d/%m/%Y", "%m/%d/%Y"):
                try:
                    pub = datetime.strptime(normalized.split("T")[0].split("+")[0].split("Z")[0], fmt.split("T")[0])
                    break
                except Exception:
                    pass
            if pub is None:
                # Try fromisoformat (handles 2020-01-01 but not 2020-1-1)
                pub = datetime.fromisoformat(normalized)
            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=time_window_days)
            if pub < cutoff:
                return False, f"too_old:{published_at}"
        except Exception:
            pass  # unparseable date → skip filter

    return True, ""


def detect_language(text: str) -> str:
    """Lightweight language detection (no external library)"""
    sample = (text or "")[:500]
    if not sample:
        return "unknown"
    zh_count = sum(1 for c in sample if "\u4e00" <= c <= "\u9fff")
    ratio = zh_count / len(sample)
    if ratio > 0.15:
        return "zh"
    en_count = sum(1 for c in sample if c.isalpha() and ord(c) < 128)
    if en_count / len(sample) > 0.4:
        return "en"
    return "unknown"


def deduplicate_by_hash(records: list[dict]) -> list[dict]:
    """Remove duplicate records by content_hash, keeping first occurrence"""
    seen: set[str] = set()
    out = []
    for r in records:
        h = r.get("content_hash", "")
        if h and h in seen:
            continue
        if h:
            seen.add(h)
        out.append(r)
    return out
