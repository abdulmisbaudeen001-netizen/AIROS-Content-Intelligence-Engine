"""
AIROS Content Intelligence Engine
RSS Service — fetch and parse RSS/Atom feeds.
"""

from dataclasses import dataclass
from typing import List, Optional
import httpx
import feedparser

from config import RSS_FEEDS, REQUEST_TIMEOUT_SECONDS, USER_AGENT
from logger import get_logger

logger = get_logger("rss_service")


@dataclass
class FeedItem:
    title: str
    summary: str
    link: str
    published: str
    source: str


def fetch_feed(url: str) -> List[FeedItem]:
    """Fetch a single RSS/Atom feed. Returns empty list on failure."""
    try:
        headers = {"User-Agent": USER_AGENT}
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            resp = client.get(url, headers=headers, follow_redirects=True)
            resp.raise_for_status()

        parsed = feedparser.parse(resp.text)
        items = []

        for entry in parsed.entries[:20]:  # cap per feed
            items.append(FeedItem(
                title=entry.get("title", "").strip(),
                summary=entry.get("summary", "")[:500].strip(),
                link=entry.get("link", ""),
                published=entry.get("published", ""),
                source=parsed.feed.get("title", url),
            ))

        logger.debug(f"RSS | {url} | {len(items)} items")
        return items

    except Exception as e:
        logger.warning(f"RSS fetch failed | url={url} | error={e}")
        return []


def fetch_all_feeds(feed_urls: Optional[List[str]] = None) -> List[FeedItem]:
    """Fetch all configured feeds concurrently and return combined list."""
    urls = feed_urls or RSS_FEEDS
    all_items: List[FeedItem] = []

    for url in urls:
        all_items.extend(fetch_feed(url))

    logger.info(f"RSS | total items collected={len(all_items)}")
    return all_items
