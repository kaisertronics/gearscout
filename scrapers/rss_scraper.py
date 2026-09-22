"""
RSS feed scraper — forum RSS feeds, eBay.
Reddit uses OAuth API (scrape_reddit).
"""
import logging
import re
import time
from datetime import datetime, timezone
from typing import Optional

import feedparser
import requests

from .base import Listing, ScrapeResult, clean_price, keyword_match, truncate

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _parse_date(entry) -> Optional[datetime]:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _extract_price(text: str) -> Optional[str]:
    m = re.search(r'\$[\d,]+(?:\.\d{2})?', text)
    return m.group(0) if m else None


def scrape_rss(source: dict, keywords: list[str]) -> ScrapeResult:
    name = source["name"]
    rss_url = source.get("rss_url") or source.get("url")
    page_url = source.get("url", rss_url)
    start = time.time()

    content = None
    fetch_error = None

    try:
        resp = requests.get(rss_url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        content = resp.content
    except requests.exceptions.HTTPError as e:
        status = resp.status_code
        fetch_error = ("http", status, str(e))
    except requests.exceptions.ConnectionError as e:
        return ScrapeResult(
            source_name=name, source_url=page_url, success=False,
            error=f"Connection failed: {e}",
            fix_hint="Check internet connection or verify the RSS URL is still valid.",
            duration_seconds=time.time() - start,
        )
    except requests.exceptions.Timeout:
        return ScrapeResult(
            source_name=name, source_url=page_url, success=False,
            error="Request timed out after 20 seconds.",
            fix_hint="Site may be slow or down. Will retry next run.",
            duration_seconds=time.time() - start,
        )
    except Exception as e:
        return ScrapeResult(
            source_name=name, source_url=page_url, success=False,
            error=str(e), fix_hint="Unexpected error. Check logs.",
            duration_seconds=time.time() - start,
        )

    if content is None:
        # Plain request was blocked (e.g. Cloudflare/bot-detection). Some forum
        # hosts serve a JS challenge to non-browser clients but let a real
        # browser through — retry once with Playwright before giving up.
        from .html_scraper import _playwright_get
        html = _playwright_get(rss_url, wait_ms=1500)
        if html:
            content = html.encode("utf-8")
        else:
            _, status, err = fetch_error
            return ScrapeResult(
                source_name=name, source_url=page_url, success=False,
                error=f"HTTP {status}: {err}",
                fix_hint=_http_hint(status, name, page_url),
                duration_seconds=time.time() - start,
            )

    feed = feedparser.parse(content)
    if feed.bozo and not feed.entries:
        return ScrapeResult(
            source_name=name, source_url=page_url, success=False,
            error=f"Feed parse error: {feed.bozo_exception}",
            fix_hint=(
                "RSS feed returned malformed XML or the URL no longer points to a feed. "
                f"Open {rss_url} in a browser to check it's still valid RSS."
            ),
            duration_seconds=time.time() - start,
        )

    listings = []
    for entry in feed.entries:
        title = getattr(entry, "title", "") or ""
        summary = getattr(entry, "summary", "") or ""
        link = getattr(entry, "link", "") or ""
        combined = f"{title} {summary}"

        if not keyword_match(combined, keywords):
            continue

        price = _extract_price(combined)
        image_url = None
        if hasattr(entry, "media_content") and entry.media_content:
            image_url = entry.media_content[0].get("url")
        elif hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
            image_url = entry.media_thumbnail[0].get("url")

        listings.append(Listing(
            source_name=name,
            title=truncate(title, 120),
            url=link,
            price=clean_price(price) if price else None,
            description=truncate(summary, 250),
            image_url=image_url,
            posted_at=_parse_date(entry),
            listing_id=getattr(entry, "id", None) or link,
        ))

    return ScrapeResult(
        source_name=name, source_url=page_url, success=True,
        listings=listings, duration_seconds=time.time() - start,
    )


def scrape_reddit(source: dict, keywords: list[str], oauth_cfg: dict = None) -> ScrapeResult:
    """
    Scrape Reddit via OAuth API (app-only flow).
    Falls back to a clear error message if credentials aren't set.
    """
    name = source["name"]
    url = source["url"].rstrip("/")
    page_url = url
    start = time.time()

    if not oauth_cfg or not oauth_cfg.get("client_id"):
        return ScrapeResult(
            source_name=name, source_url=page_url, success=False,
            error="Reddit OAuth credentials not configured.",
            fix_hint=(
                "Reddit requires OAuth to scrape. To set it up:\n"
                "1. Go to https://www.reddit.com/prefs/apps\n"
                "2. Click 'Create App' → choose 'script'\n"
                "3. Name it 'GearScout', redirect URI: http://localhost:8080\n"
                "4. Copy client_id and client_secret into config.yaml under reddit_oauth:\n"
                "5. Set enabled: true on Reddit sources in config.yaml"
            ),
            duration_seconds=time.time() - start,
        )

    # Get OAuth token (app-only / password flow)
    try:
        token_resp = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=(oauth_cfg["client_id"], oauth_cfg["client_secret"]),
            data={
                "grant_type": "password",
                "username": oauth_cfg.get("username", ""),
                "password": oauth_cfg.get("password", ""),
            },
            headers={"User-Agent": "GearScout:v1.0 (by /u/" + oauth_cfg.get("username", "gearscout") + ")"},
            timeout=15,
        )
        token_resp.raise_for_status()
        token = token_resp.json().get("access_token")
        if not token:
            raise ValueError("No access_token in response")
    except Exception as e:
        return ScrapeResult(
            source_name=name, source_url=page_url, success=False,
            error=f"Reddit OAuth token failed: {e}",
            fix_hint=(
                "Reddit authentication failed. Check your client_id, client_secret, "
                "username and password in config.yaml under reddit_oauth:. "
                "Also verify your app type is 'script' at https://www.reddit.com/prefs/apps"
            ),
            duration_seconds=time.time() - start,
        )

    # Extract subreddit name from URL
    sub_match = re.search(r'reddit\.com/r/([^/]+)', url)
    if not sub_match:
        return ScrapeResult(
            source_name=name, source_url=page_url, success=False,
            error="Could not parse subreddit name from URL.",
            fix_hint="URL should be like https://www.reddit.com/r/AVexchange/new/",
            duration_seconds=time.time() - start,
        )
    subreddit = sub_match.group(1)

    api_url = f"https://oauth.reddit.com/r/{subreddit}/new?limit=50"
    headers = {
        "Authorization": f"bearer {token}",
        "User-Agent": "GearScout:v1.0 (by /u/" + oauth_cfg.get("username", "gearscout") + ")",
    }

    try:
        resp = requests.get(api_url, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        posts = data["data"]["children"]
    except Exception as e:
        return ScrapeResult(
            source_name=name, source_url=page_url, success=False,
            error=f"Reddit API error: {e}",
            fix_hint="Reddit API request failed. Check credentials and try again.",
            duration_seconds=time.time() - start,
        )

    listings = []
    for post in posts:
        p = post.get("data", {})
        title = p.get("title", "") or ""
        selftext = p.get("selftext", "") or ""
        link = "https://www.reddit.com" + (p.get("permalink", "") or "")
        combined = f"{title} {selftext}"

        flair = (p.get("link_flair_text") or "").lower()
        if flair and any(x in flair for x in ["weekly", "mod", "meta", "question", "discussion"]):
            continue

        if not keyword_match(combined, keywords):
            continue

        price = _extract_price(combined)
        image_url = p.get("thumbnail") if (p.get("thumbnail") or "").startswith("http") else None

        listings.append(Listing(
            source_name=name,
            title=truncate(title, 120),
            url=link,
            price=clean_price(price) if price else None,
            description=truncate(selftext, 250),
            image_url=image_url,
            posted_at=datetime.fromtimestamp(p.get("created_utc", 0), tz=timezone.utc),
            listing_id=p.get("id", link),
        ))

    return ScrapeResult(
        source_name=name, source_url=page_url, success=True,
        listings=listings, duration_seconds=time.time() - start,
    )


def _http_hint(status: int, name: str, url: str) -> str:
    if status == 403:
        return (
            f"{name} is blocking automated requests (HTTP 403). "
            "The feed may require login or the site has blocked scrapers. "
            f"Try visiting {url} in a browser to confirm it still works."
        )
    if status == 404:
        return (
            f"The RSS URL for {name} returned 404 — feed has moved. "
            f"Visit the forum at {url} in a browser, look for the RSS icon, "
            "copy the new URL and update rss_url in config.yaml."
        )
    if status == 429:
        return f"{name} is rate-limiting. Reduce scrape frequency in config.yaml."
    if status >= 500:
        return f"{name} server error (HTTP {status}). Usually temporary — will retry next run."
    return f"HTTP {status} from {name}. Verify the rss_url in config.yaml is still valid."
