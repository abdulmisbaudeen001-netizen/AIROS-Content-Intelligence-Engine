"""
AIROS Content Intelligence Engine
Long-Term Memory — persistent knowledge retrieved from the database.
Provides fast access to learning insights and publication history.
"""

from typing import List, Dict, Any, Optional
from database.connection import SessionLocal
from database import repository
from logger import get_logger

logger = get_logger("long_memory")

# In-process cache — refreshed at each scheduler run
_learning_cache: Dict[str, str] = {}
_recently_published_titles: List[str] = []


def refresh(limit: int = 50):
    """Reload learning insights and recent headlines from the database."""
    global _learning_cache, _recently_published_titles

    with SessionLocal() as db:
        learnings = repository.get_all_learnings(db)
        _learning_cache = {r.insight_type: r.insight_value for r in learnings}

        recent = repository.get_recent_publications(db, limit=limit)
        _recently_published_titles = [r.headline for r in recent]

    logger.info(f"Long memory refreshed | insights={len(_learning_cache)} | recent_articles={len(_recently_published_titles)}")


def get_insight(key: str, default: Optional[str] = None) -> Optional[str]:
    return _learning_cache.get(key, default)


def get_all_insights() -> Dict[str, str]:
    return dict(_learning_cache)


def get_recent_titles() -> List[str]:
    return list(_recently_published_titles)


def is_duplicate_topic(title: str, threshold: float = 0.7) -> bool:
    """
    Simple duplicate check — returns True if title is too similar to a
    recently published headline.
    Uses character-level overlap (no external dependency).
    """
    title_lower = title.lower()
    for published in _recently_published_titles:
        pub_lower = published.lower()
        # Jaccard similarity on word sets
        a = set(title_lower.split())
        b = set(pub_lower.split())
        if not a or not b:
            continue
        similarity = len(a & b) / len(a | b)
        if similarity >= threshold:
            logger.debug(f"Duplicate detected | title='{title}' | similar_to='{published}' | score={similarity:.2f}")
            return True
    return False
