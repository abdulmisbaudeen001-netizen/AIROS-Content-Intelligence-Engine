"""
AIROS Content Intelligence Engine (ACIE)
Central configuration — all settings live here, nothing is hard-coded elsewhere.
"""

import os
from dataclasses import dataclass, field
from typing import List


# ---------------------------------------------------------------------------
# LLM / OpenRouter
# ---------------------------------------------------------------------------

OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

# Primary route — OpenRouter free router picks best available free model
LLM_PRIMARY_MODEL: str = "openrouter/auto"

# Explicit fallback chain used when primary fails
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

GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")
BLOGGER_BLOG_ID: str = os.getenv("BLOGGER_BLOG_ID", "")

# Token storage — persisted after first OAuth2 flow
TOKEN_FILE: str = os.getenv("TOKEN_FILE", ".acie_tokens.json")


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///acie.db")


# ---------------------------------------------------------------------------
# Scheduler windows (24-hour format)
# ---------------------------------------------------------------------------

SCHEDULE_MORNING_HOUR: int = 7
SCHEDULE_AFTERNOON_HOUR: int = 13
SCHEDULE_EVENING_HOUR: int = 19
SCHEDULE_TOPICS_PER_RUN: int = 2   # articles published per window


# ---------------------------------------------------------------------------
# Quality thresholds — articles below these scores are rejected / revised
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
USER_AGENT: str = (
    "Mozilla/5.0 (compatible; AIROSBot/1.0; +https://airos.news)"
)

# RSS feeds monitored by the Trend Discovery Agent
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

# Trend search engine scraping targets
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
# Deployment
# ---------------------------------------------------------------------------

APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
