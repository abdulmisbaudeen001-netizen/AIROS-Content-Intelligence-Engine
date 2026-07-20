"""
AIROS Content Intelligence Engine
Agent 2 — Source Collection Agent

For a given topic, finds and scrapes multiple independent sources.
Returns a merged knowledge package for downstream agents.
"""

from dataclasses import dataclass
from typing import List, Optional

from services import search_service, scraper_service
from config import MAX_SOURCES_PER_TOPIC, MIN_SOURCES_PER_TOPIC
from logger import get_logger

logger = get_logger("source_agent")


@dataclass
class SourcePackage:
    topic: str
    sources: List[dict]             # [{url, title, content, source_name}]
    merged_text: str                # All content concatenated for LLM input
    source_count: int


def initialize():
    logger.info("Source Collection Agent initialized.")


def validate_input(topic: str) -> bool:
    return isinstance(topic, str) and len(topic.strip()) > 3


def execute(topic: str, seed_urls: Optional[List[str]] = None) -> SourcePackage:
    """
    1. Search for articles about the topic.
    2. Scrape each article URL.
    3. Return merged knowledge package.
    """
    logger.info(f"Source collection | topic='{topic}'")

    # Discover URLs
    search_results = search_service.search_topic(topic, max_results=MAX_SOURCES_PER_TOPIC + 3)
    candidate_urls = [r.url for r in search_results if r.url]

    # Add seed URLs from trend discovery if available
    if seed_urls:
        for u in seed_urls:
            if u and u not in candidate_urls:
                candidate_urls.append(u)

    logger.info(f"Candidate URLs: {len(candidate_urls)}")

    sources = []
    for url in candidate_urls:
        if len(sources) >= MAX_SOURCES_PER_TOPIC:
            break

        content = scraper_service.extract_content(url)
        if not content:
            continue

        # Find matching title from search results
        title = next((r.title for r in search_results if r.url == url), url)
        source_name = next((r.source for r in search_results if r.url == url), "Unknown")

        sources.append({
            "url": url,
            "title": title,
            "content": content,
            "source_name": source_name,
        })
        logger.debug(f"Source collected | {source_name} | chars={len(content)}")

    if len(sources) < MIN_SOURCES_PER_TOPIC:
        logger.warning(f"Only {len(sources)} sources found — below minimum {MIN_SOURCES_PER_TOPIC}")

    # Merge all content into a single knowledge block
    parts = []
    for i, src in enumerate(sources, 1):
        parts.append(
            f"=== SOURCE {i}: {src['source_name']} ===\n"
            f"URL: {src['url']}\n"
            f"TITLE: {src['title']}\n\n"
            f"{src['content']}\n"
        )
    merged_text = "\n\n".join(parts)

    logger.info(f"Source collection complete | {len(sources)} sources | {len(merged_text)} chars total")

    return SourcePackage(
        topic=topic,
        sources=sources,
        merged_text=merged_text,
        source_count=len(sources),
    )


def validate_output(pkg: SourcePackage) -> bool:
    return pkg.source_count >= MIN_SOURCES_PER_TOPIC and len(pkg.merged_text) > 500


def report(pkg: SourcePackage) -> dict:
    return {
        "agent": "SourceCollectionAgent",
        "topic": pkg.topic,
        "source_count": pkg.source_count,
        "total_chars": len(pkg.merged_text),
    }
