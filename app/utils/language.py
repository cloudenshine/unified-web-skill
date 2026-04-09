"""Unified language detection utility.

Centralises the CJK-vs-Latin heuristic that was previously duplicated
across ``intent_classifier`` and ``extractor``.
"""

from __future__ import annotations

# CJK Unicode ranges used for language detection
_CJK_RANGES = (
    (0x4E00, 0x9FFF),   # CJK Unified Ideographs
    (0x3400, 0x4DBF),   # CJK Extension A
    (0xF900, 0xFAFF),   # CJK Compatibility Ideographs
)


def detect_language(
    text: str,
    *,
    min_length: int = 0,
    sample_size: int = 0,
) -> str:
    """Heuristic language detection based on character-class ratios.

    Parameters
    ----------
    text:
        The text to analyse.
    min_length:
        If the stripped text is shorter than this, return ``"unknown"``
        immediately.  Useful for content extraction where very short
        strings are meaningless.
    sample_size:
        When > 0, only inspect the first *sample_size* characters.
        Useful for long documents where scanning the full text is
        wasteful.

    Returns
    -------
    str
        ``"zh"`` — predominantly Chinese characters.
        ``"en"`` — predominantly ASCII / Latin.
        ``"mixed"`` — significant mix of both.
        ``"unknown"`` — too short or unrecognisable.
    """
    if not text or len(text.strip()) < max(min_length, 1):
        return "unknown"

    sample = text[:sample_size] if sample_size > 0 else text

    cjk_count = 0
    latin_count = 0
    for ch in sample:
        cp = ord(ch)
        if any(lo <= cp <= hi for lo, hi in _CJK_RANGES):
            cjk_count += 1
        elif (0x41 <= cp <= 0x5A) or (0x61 <= cp <= 0x7A):
            latin_count += 1

    total = cjk_count + latin_count
    if total == 0:
        return "unknown"

    cjk_ratio = cjk_count / total
    if cjk_ratio > 0.6:
        return "zh"
    if cjk_ratio < 0.2:
        return "en"
    return "mixed"
