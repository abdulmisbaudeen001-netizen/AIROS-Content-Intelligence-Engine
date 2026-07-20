"""
AIROS Content Intelligence Engine (ACIE)
Central configuration — all values are read from Render environment variables.
No defaults for secrets. If a required variable is missing, the system raises
a clear error at startup rather than running silently with wrong values.
"""

import os
from typing import List


def _require(key: str) -> str:
    """Read a required environment variable. Raises if missing or empty."""
    value = os.environ.get(key, "").strip()
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            f"Add it in Render → your service → Environment."
        )
    return value


def _optional(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


# ---------------------------------------------------------------------------
# LLM / OpenRouter
# ---------------------------------------------------------------------------

OPENROUTER_API_KEY: str = _require("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

# Primary — OpenRouter free router picks best available free model
LLM_PRIMARY_MODEL: str = "openrouter/auto"

# Explicit fallback chain when primary fails
LLM_FALLBACK_CHAIN: List[str] = [
    "deepseek/deepseek-chat-v3-0324:free",   # DeepSeek V4 Flash free
    "tencent/hunyuan-a13b-instruct:free",     # Tencent Hy3 free
    "qwen/qwen3-8b:free",                     # Qwen emergency fallback
]

LLM_MAX_TOKENS: int = 4096
LLM_TEMPERATURE: float = 0.7
LLM_TIMEOUT_SECONDS: int = 120
LLM_MAX_RETRIES: int = 3


# ---------------------------------------------------------------------------
# Blogger / Google OAuth2
# ---------------------------------------------------------------------------

GOOGLE_CLIENT_ID: str = _require("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET: str = _require("GOOGLE_CLIENT_SECRET")
BLOGGER_BLOG_ID: str = _require("BLOGGER_BLOG_ID")

# Render service URL — set this in Render environment as your full service URL
# Example: https://airos-engine.onrender.com
RENDER_SERVICE_URL: str = _optional("RENDER_SERVICE_URL", "http://localhost:8000")
GOOGLE_REDIRECT_URI: str = f"{RENDER_SERVICE_URL.rstrip('/')}/auth/callback"

# Token file — OAuth2 tokens saved here after first authorization
# On Render, use /tmp/ — it persists within the same instance
TOKEN_FILE: str = _optional("TOKEN_FILE", "/tmp/.acie_tokens.json")


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

# On Render: set DATABASE_URL to your PostgreSQL connection string
# Render provides this automatically when you attach a PostgreSQL database
DATABASE_URL: str = _require("DATABASE_URL")


# ---------------------------------------------------------------------------
# Scheduler windows (24-hour format)
# ---------------------------------------------------------------------------

SCHEDULE_MORNING_HOUR: int = 7
SCHEDULE_AFTERNOON_HOUR: int = 13
SCHEDULE_EVENING_HOUR: int = 19
SCHEDULE_TOPICS_PER_RUN: int = 2


# ---------------------------------------------------------------------------
# Quality thresholds
# ---------------------------------------------------------------------------

MIN_QUALITY_SCORE: int = 80
MIN_SEO_SCORE: int = 75
MIN_POLICY_SCORE: int = 90
MIN_ORIGINALITY_SCORE: int = 75
MIN_READABILITY_SCORE: int = 70


# ---------------------------------------------------------------------------
# Content acquisition
# ---------------------------------------------------------------------------

MAX_SOURCES_PER_TOPIC: int = 8
MIN_SOURCES_PER_TOPIC: int = 3
REQUEST_TIMEOUT_SECONDS: int = 30
USER_AGENT: str = "Mozilla/5.0 (compatible; AIROSBot/1.0; +https://airos.news)"

RSS_FEEDS: List[str] = [
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://feeds.reuters.com/reuters/topNews",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://techcrunch.com/feed/",
    "https://feeds.feedburner.com/TheHackersNews",
    "https://www.theguardian.com/world/rss",
    "https://feeds.skynews.com/feeds/rss/world.xml",
    "https://www.independent.co.uk/news/world/rss",
    "https://apnews.com/hub/ap-top-news?format=rss",
    "https://feeds.washingtonpost.com/rss/world",
    "https://www.voanews.com/api/zmoqiauqte",
    "https://www.dw.com/rss/rss.xml",
    "https://www.bloomberg.com/feeds/podcasts/etf_report.xml",
    "https://rss.cnn.com/rss/edition.rss",
]

TREND_SEARCH_URLS: List[str] = [
    "https://trends.google.com/trending?geo=US",
    "https://trends.google.com/trending?geo=GB",
    "https://news.google.com/rss",
    "https://bing.com/news/search?q=trending+today&format=rss",
]


# ---------------------------------------------------------------------------
# Article style
# ---------------------------------------------------------------------------

ARTICLE_MIN_WORDS: int = 800
ARTICLE_MAX_WORDS: int = 1800
ARTICLE_EDITORIAL_VOICE: str = (
    "Authoritative, clear, and human. No filler. No jargon. "
    "Lead with the most important fact. Write for an informed adult reader."
)


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

APP_HOST: str = "0.0.0.0"
APP_PORT: int = int(_optional("PORT", "8000"))   # Render sets PORT automatically
DEBUG: bool = _optional("DEBUG", "false").lower() == "true"
