"""
AIROS Content Intelligence Engine
Scraper Service — extract clean article text from URLs.

Strategy:
  1. httpx + BeautifulSoup (fast, no JS)
  2. Playwright (fallback for JS-heavy pages)
"""

import re
from typing import Optional
import httpx
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT_SECONDS, USER_AGENT
from logger import get_logger

logger = get_logger("scraper_service")

_NOISE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "form", "iframe"]


def _clean_text(text: str) -> str:
    """Collapse whitespace and remove ad/cookie boilerplate markers."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(Cookie Policy|Privacy Policy|Accept All Cookies|Subscribe now)[^\n]*", "", text, flags=re.IGNORECASE)
    return text.strip()


def scrape_url(url: str) -> Optional[str]:
    """
    Extract main article text from a URL.
    Returns None if extraction fails or content is too short.
    """
    try:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
        }
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove noise tags
        for tag in soup(_NOISE_TAGS):
            tag.decompose()

        # Prefer <article> or <main>; fall back to <body>
        container = soup.find("article") or soup.find("main") or soup.find("body")
        if not container:
            return None

        # Collect paragraph text
        paragraphs = [p.get_text(" ", strip=True) for p in container.find_all("p")]
        text = " ".join(p for p in paragraphs if len(p) > 40)
        text = _clean_text(text)

        if len(text) < 200:
            logger.debug(f"Scrape too short | url={url} | chars={len(text)}")
            return None

        logger.debug(f"Scraped | url={url} | chars={len(text)}")
        return text[:8000]  # cap to avoid overwhelming LLM context

    except Exception as e:
        logger.warning(f"Scrape failed | url={url} | error={e}")
        return None


def scrape_with_browser(url: str) -> Optional[str]:
    """
    Playwright fallback for JS-rendered pages.
    Only called when static scraping returns None.
    Requires: pip install playwright && playwright install chromium
    """
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(user_agent=USER_AGENT)
            page.goto(url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(_NOISE_TAGS):
            tag.decompose()

        container = soup.find("article") or soup.find("main") or soup.find("body")
        if not container:
            return None

        paragraphs = [p.get_text(" ", strip=True) for p in container.find_all("p")]
        text = " ".join(p for p in paragraphs if len(p) > 40)
        text = _clean_text(text)

        return text[:8000] if len(text) > 200 else None

    except ImportError:
        logger.warning("Playwright not installed — browser scraping unavailable.")
        return None
    except Exception as e:
        logger.warning(f"Browser scrape failed | url={url} | error={e}")
        return None


def extract_content(url: str) -> Optional[str]:
    """
    Public entry point. Tries static scraping first, browser as fallback.
    """
    text = scrape_url(url)
    if text:
        return text

    logger.info(f"Falling back to browser | url={url}")
    return scrape_with_browser(url)
