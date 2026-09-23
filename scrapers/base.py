"""
Base scraper class and shared utilities.
"""
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Listing:
    source_name: str
    title: str
    url: str
    price: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    posted_at: Optional[datetime] = None
    listing_id: Optional[str] = None  # unique ID within source

    def __post_init__(self):
        if not self.listing_id:
            # Fallback: hash the URL
            self.listing_id = hashlib.md5(self.url.encode()).hexdigest()[:16]

    @property
    def global_id(self) -> str:
        """Globally unique ID across all sources."""
        return f"{self.source_name}::{self.listing_id}"


@dataclass
class ScrapeResult:
    source_name: str
    source_url: str
    success: bool
    listings: list[Listing] = field(default_factory=list)
    error: Optional[str] = None
    fix_hint: Optional[str] = None  # human-readable fix instructions
    duration_seconds: float = 0.0
    # True only for the specific "site sits behind bot detection, use the
    # manual link instead" case (Guitar Center/Sweetwater/eBay) — this is
    # expected, permanent, and has a working manual link, so the UI shouldn't
    # scare people with red "FAILED" for it the way it does for an actual bug
    # (a real layout change breaking a selector, etc).
    blocked: bool = False


_keyword_pattern_cache: dict[str, re.Pattern] = {}


def _keyword_pattern(kw: str) -> Optional[re.Pattern]:
    kw_clean = kw.strip().lower()
    if not kw_clean:
        return None
    pattern = _keyword_pattern_cache.get(kw_clean)
    if pattern is None:
        # Allow an optional trailing "s" so plurals of the keyword's last word
        # still match (e.g. "studio monitor" -> "studio monitors").
        pattern = re.compile(r'\b' + re.escape(kw_clean) + r's?\b')
        _keyword_pattern_cache[kw_clean] = pattern
    return pattern


def keyword_match(text: str, keywords: list[str]) -> bool:
    """Return True if any keyword is found in text as a whole word/phrase
    (case-insensitive). Word-boundary matching keeps short keywords like "mic"
    or "rme" from matching fragments inside unrelated words (e.g. "Samick",
    "Performer") the way plain substring matching would."""
    text_lower = text.lower()
    for kw in keywords:
        pattern = _keyword_pattern(kw)
        if pattern and pattern.search(text_lower):
            return True

    # A single term means a live search, where the site's own search already
    # did the real matching and normalizes spacing/hyphens ("KM 184", "KM-184"
    # and "KM184NI" all count as "km184" on Reverb). Compare with those
    # stripped so we don't discard results the site correctly returned. Only
    # for alphanumeric model-number-style terms (has a digit, 4+ chars) —
    # short/plain words like "eq" or "mic" must keep strict word matching.
    if len(keywords) == 1:
        compact_kw = re.sub(r'[^a-z0-9]', '', keywords[0].lower())
        if len(compact_kw) >= 4 and any(c.isdigit() for c in compact_kw):
            if compact_kw in re.sub(r'[^a-z0-9]', '', text_lower):
                return True
    return False


def clean_price(raw: str) -> Optional[str]:
    """Normalize price strings."""
    if not raw:
        return None
    raw = raw.strip()
    if not any(c.isdigit() for c in raw):
        return None
    return raw


def truncate(text: str, length: int = 200) -> str:
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:length] + "..." if len(text) > length else text
