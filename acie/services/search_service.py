"""
AIROS Content Intelligence Engine
Search Service — discover trending topic URLs without paid APIs.

Sources:
  1. Google News RSS
  2. Bing News RSS
  3. Google Trending (HTML scrape)
"""

import re
from typing import List
from dataclasses import dataclass

import httpx
import feedparser
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT_SECONDS, USER_AGENT
from logger import get_logger

logger = get_logger("search_service")

GOOGLE_NEWS_RSS = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
BING_NEWS_RSS = "https://www.bing.com/news/search?q=trending+today&format=RSS&mkt=en-US"
GOOGLE_TRENDING_URL = "https://trends.google.com/trending?geo=US&hl=en"


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str


def _headers() -> dict:
    return {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}


def fetch_google_news(max_items: int = 30) -> List[SearchResult]:
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            resp = client.get(GOOGLE_NEWS_RSS, headers=_headers())
            resp.raise_for_status()

        feed = feedparser.parse(resp.text)
        results = []
        for entry in feed.entries[:max_items]:
            results.append(SearchResult(
                title=entry.get("title", "").strip(),
                url=entry.get("link", ""),
                snippet=entry.get("summary", "")[:300],
                source="Google News",
            ))
        logger.debug(f"Google News | {len(results)} items")
        return results
    except Exception as e:
        logger.warning(f"Google News RSS failed | {e}")
        return []


def fetch_bing_news(max_items: int = 20) -> List[SearchResult]:
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            resp = client.get(BING_NEWS_RSS, headers=_headers())
            resp.raise_for_status()

        feed = feedparser.parse(resp.text)
        results = []
        for entry in feed.entries[:max_items]:
            results.append(SearchResult(
                title=entry.get("title", "").strip(),
                url=entry.get("link", ""),
                snippet=entry.get("summary", "")[:300],
                source="Bing News",
            ))
        logger.debug(f"Bing News | {len(results)} items")
        return results
    except Exception as e:
        logger.warning(f"Bing News RSS failed | {e}")
        return []


def fetch_google_trending(max_items: int = 20) -> List[SearchResult]:
    """
    Scrape Google Trending page for topic titles.
    Returns minimal SearchResult objects (no URL/snippet — used for topic signals only).
    """
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            resp = client.get(GOOGLE_TRENDING_URL, headers=_headers())
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        # Google Trending stores topic names in various elements — cover common selectors
        candidates = []
        for el in soup.find_all(["h3", "a", "span"]):
            text = el.get_text(strip=True)
            if 10 < len(text) < 80:
                candidates.append(text)

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique.append(c)

        results = [
            SearchResult(title=t, url="", snippet="", source="Google Trending")
            for t in unique[:max_items]
        ]
        logger.debug(f"Google Trending | {len(results)} topics")
        return results
    except Exception as e:
        logger.warning(f"Google Trending scrape failed | {e}")
        return []


def collect_all_signals() -> List[SearchResult]:
    """
    Aggregate trend signals from all sources.
    Used by Trend Discovery Agent as input.
    """
    results: List[SearchResult] = []
    results.extend(fetch_google_news())
    results.extend(fetch_bing_news())
    results.extend(fetch_google_trending())
    logger.info(f"Search signals total | {len(results)} items")
    return results


def search_topic(topic: str, max_results: int = 10) -> List[SearchResult]:
    """
    Find articles about a specific topic using Google News RSS query.
    Used by Source Collection Agent to gather per-topic sources.
    """
    import urllib.parse
    query = urllib.parse.quote(topic)
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            resp = client.get(url, headers=_headers())
            resp.raise_for_status()

        feed = feedparser.parse(resp.text)
        results = []
        for entry in feed.entries[:max_results]:
            results.append(SearchResult(
                title=entry.get("title", "").strip(),
                url=entry.get("link", ""),
                snippet=entry.get("summary", "")[:300],
                source=entry.get("source", {}).get("title", "Unknown"),
            ))
        logger.debug(f"Topic search | topic={topic} | {len(results)} results")
        return results
    except Exception as e:
        logger.warning(f"Topic search failed | topic={topic} | {e}")
        return []
