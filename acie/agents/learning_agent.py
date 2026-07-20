"""
AIROS Content Intelligence Engine
Agent 10 — Learning Agent

Analyzes published article performance and updates long-term memory
with insights that improve future runs.
"""

import json
from typing import List

from services import llm_service, analytics_service
from database.connection import SessionLocal
from database import repository
from memory import long_memory
from logger import get_logger

logger = get_logger("learning_agent")


def initialize():
    logger.info("Learning Agent initialized.")


def execute():
    """
    Pull recent publication data, analyze patterns, and store insights.
    Called after each publishing window completes.
    """
    logger.info("Learning agent running...")

    with SessionLocal() as db:
        recent = repository.get_recent_publications(db, limit=30)

        if len(recent) < 3:
            logger.info("Not enough publications for learning yet.")
            return

        # Fetch analytics for each
        stats_list = []
        for pub in recent:
            stats = analytics_service.get_post_stats(pub.blogger_post_id)
            if stats:
                stats_list.append({
                    "headline": pub.headline,
                    "word_count": pub.word_count,
                    "window": pub.window,
                    "comments": stats.get("comments", 0),
                    "published_at": str(pub.published_at),
                })

        if not stats_list:
            logger.info("No analytics data available yet.")
            return

        # Ask LLM to extract learning insights
        prompt = f"""
You are the Learning module of AIROS. Analyze the following published articles and their performance data.

PUBLISHED ARTICLES WITH PERFORMANCE:
{json.dumps(stats_list, indent=2)}

ANALYZE AND EXTRACT:
1. best_headline_style: What pattern do the most-engaged headlines follow?
2. best_publish_window: Which window (morning/afternoon/evening) gets most engagement?
3. best_word_count_range: What word count range performs best?
4. best_content_structure: What article structure patterns correlate with performance?
5. underperforming_patterns: What patterns should be avoided?

For each insight, assign a confidence score (0-1) based on sample size and pattern clarity.

RESPOND ONLY WITH VALID JSON:
{{
  "best_headline_style": {{"value": "...", "confidence": 0.75, "sample_size": 12}},
  "best_publish_window": {{"value": "morning", "confidence": 0.6, "sample_size": 10}},
  "best_word_count_range": {{"value": "1100-1400 words", "confidence": 0.8, "sample_size": 15}},
  "best_content_structure": {{"value": "...", "confidence": 0.65, "sample_size": 10}},
  "underperforming_patterns": {{"value": "...", "confidence": 0.7, "sample_size": 8}}
}}
"""

        try:
            raw = llm_service.generate(prompt, json_mode=True, temperature=0.2)
            insights = json.loads(raw)

            for insight_type, data in insights.items():
                repository.upsert_learning(
                    db=db,
                    insight_type=insight_type,
                    insight_value=str(data.get("value", "")),
                    confidence=float(data.get("confidence", 0.0)),
                    sample_size=int(data.get("sample_size", 0)),
                )

            # Refresh in-memory cache
            long_memory.refresh()

            logger.info(f"Learning complete | {len(insights)} insights updated")

        except Exception as e:
            logger.error(f"Learning analysis failed | {e}")


def report() -> dict:
    return {
        "agent": "LearningAgent",
        "insights": long_memory.get_all_insights(),
    }
