"""
AIROS Content Intelligence Engine
Agent 1 — Trend Discovery Agent

Discovers trending topics, scores them, and returns ranked opportunities.
Uses RSS feeds + search signals + LLM scoring.
"""

import json
from dataclasses import dataclass
from typing import List, Optional

from services import rss_service, search_service, llm_service
from memory import long_memory
from logger import get_logger

logger = get_logger("trend_agent")


@dataclass
class TopicOpportunity:
    title: str
    category: str
    trend_score: float          # 0-100: how hot is this right now
    opportunity_score: float    # 0-100: composite score (trend + originality + value)
    source_urls: List[str]
    summary: str


def initialize():
    logger.info("Trend Discovery Agent initialized.")


def validate_input(signals: list) -> bool:
    return isinstance(signals, list) and len(signals) > 0


def execute(top_n: int = 5) -> List[TopicOpportunity]:
    """
    Full trend discovery run.
    1. Collect RSS + search signals.
    2. Deduplicate against recently published articles.
    3. Ask LLM to score and rank opportunities.
    4. Return top_n opportunities.
    """
    logger.info("Trend discovery starting...")

    # Collect raw signals
    rss_items = rss_service.fetch_all_feeds()
    search_items = search_service.collect_all_signals()

    # Build a combined title list
    all_titles = [item.title for item in rss_items if item.title]
    all_titles += [item.title for item in search_items if item.title]

    # Deduplicate
    seen = set()
    unique_titles = []
    for t in all_titles:
        key = t.lower().strip()
        if key not in seen and len(key) > 10:
            seen.add(key)
            unique_titles.append(t)

    logger.info(f"Unique signals collected: {len(unique_titles)}")

    if not unique_titles:
        logger.warning("No trend signals found.")
        return []

    # Filter already-published topics
    recent_titles = long_memory.get_recent_titles()
    filtered = [t for t in unique_titles if not long_memory.is_duplicate_topic(t)]
    logger.info(f"After duplicate filter: {len(filtered)} topics")

    # Limit input to LLM to avoid context overflow
    candidates = filtered[:60]

    # Build source map: topic title -> URLs found
    source_map: dict = {}
    for item in rss_items:
        if item.title in candidates:
            source_map.setdefault(item.title, []).append(item.link)
    for item in search_items:
        if item.title in candidates and item.url:
            source_map.setdefault(item.title, []).append(item.url)

    # Ask LLM to score and select best topics
    prompt = f"""
You are the Trend Discovery module of AIROS, an autonomous news publishing engine.

Below is a list of trending news titles collected from RSS feeds and search signals.

YOUR TASK:
1. Select the {top_n} most valuable topics to write about.
2. For each, assign scores (0-100):
   - trend_score: how hot / breaking is this topic right now
   - originality_score: how much can we add beyond basic reporting
   - value_score: how useful is this article to readers
   - policy_score: is this topic safe for general-audience publishing (100 = fully safe)
3. Compute opportunity_score = (trend_score * 0.3) + (originality_score * 0.3) + (value_score * 0.3) + (policy_score * 0.1)
4. Assign a category (e.g., Technology, Politics, Business, Science, Health, World News).
5. Write a 1-sentence summary of why this is worth covering.

RECENTLY PUBLISHED (avoid these):
{json.dumps(recent_titles[:20])}

CANDIDATE TOPICS:
{json.dumps(candidates)}

RESPOND ONLY WITH VALID JSON — an array of objects, no preamble:
[
  {{
    "title": "...",
    "category": "...",
    "trend_score": 85,
    "originality_score": 70,
    "value_score": 80,
    "policy_score": 100,
    "opportunity_score": 82.5,
    "summary": "..."
  }}
]
"""

    try:
        raw = llm_service.generate(prompt, json_mode=True, temperature=0.3)
        data = json.loads(raw)

        opportunities = []
        for item in data[:top_n]:
            title = item.get("title", "")
            opportunities.append(TopicOpportunity(
                title=title,
                category=item.get("category", "General"),
                trend_score=float(item.get("trend_score", 50)),
                opportunity_score=float(item.get("opportunity_score", 50)),
                source_urls=source_map.get(title, [])[:5],
                summary=item.get("summary", ""),
            ))

        logger.info(f"Trend agent complete | {len(opportunities)} opportunities selected")
        return opportunities

    except Exception as e:
        logger.error(f"Trend agent LLM scoring failed | {e}")
        # Graceful fallback: return first N candidates as minimal opportunities
        return [
            TopicOpportunity(
                title=t,
                category="General",
                trend_score=50.0,
                opportunity_score=50.0,
                source_urls=source_map.get(t, []),
                summary="",
            )
            for t in candidates[:top_n]
        ]


def validate_output(opportunities: List[TopicOpportunity]) -> bool:
    return isinstance(opportunities, list) and len(opportunities) > 0


def report(opportunities: List[TopicOpportunity]) -> dict:
    return {
        "agent": "TrendDiscoveryAgent",
        "topics_found": len(opportunities),
        "top_topic": opportunities[0].title if opportunities else None,
        "top_score": opportunities[0].opportunity_score if opportunities else 0,
    }
