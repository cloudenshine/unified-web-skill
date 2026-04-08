"""Source credibility scoring."""
import logging
from urllib.parse import urlparse

from ..constants import TRUSTED_DOMAINS, KNOWN_MEDIA, KNOWN_TECH

_logger = logging.getLogger(__name__)


def score_credibility(url: str, *, trusted_mode: bool = False) -> float:
    """Score URL credibility from 0.0 to 1.0."""
    score = 0.4  # baseline
    domain = _extract_domain(url).lower()

    # HTTPS bonus
    if url.startswith("https://"):
        score += 0.1

    # Trusted domain bonus
    for trusted in TRUSTED_DOMAINS:
        if domain.endswith(trusted):
            score += 0.35
            break

    # Known media bonus
    for media in KNOWN_MEDIA:
        if domain.endswith(media):
            score += 0.15
            break

    # Known tech bonus
    for tech in KNOWN_TECH:
        if domain.endswith(tech):
            score += 0.1
            break

    # TLD bonuses
    if any(domain.endswith(tld) for tld in (".gov", ".edu", ".org", ".mil")):
        score += 0.2
    elif any(domain.endswith(tld) for tld in (".com", ".net", ".io")):
        score += 0.05

    # Trusted mode penalty for low scores
    if trusted_mode and score < 0.5:
        score *= 0.8

    return round(min(score, 1.0), 4)


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    if not url:
        return ""
    if "://" not in url:
        url = "http://" + url
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""
