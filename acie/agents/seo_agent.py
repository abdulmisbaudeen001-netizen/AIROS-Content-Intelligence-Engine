"""
AIROS Content Intelligence Engine
Agent 7 — SEO Intelligence Agent

Generates SEO title, meta description, slug, keywords, and schema markup.
"""

import json
import re
from dataclasses import dataclass
from typing import List

from services import llm_service
from agents.writer_agent import ArticleDraftContent
from logger import get_logger

logger = get_logger("seo_agent")


@dataclass
class SEOPackage:
    seo_title: str              # 50-60 chars
    meta_description: str       # 120-155 chars
    slug: str                   # URL-safe slug
    primary_keyword: str
    secondary_keywords: List[str]
    schema_markup: dict         # JSON-LD Article schema
    internal_link_suggestions: List[str]


def initialize():
    logger.info("SEO Intelligence Agent initialized.")


def validate_input(draft: ArticleDraftContent) -> bool:
    return bool(draft.headline) and draft.word_count > 100


def _generate_slug(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug[:80]


def execute(draft: ArticleDraftContent) -> SEOPackage:
    logger.info(f"SEO optimization | headline='{draft.headline}'")

    # Strip HTML for analysis
    text_only = re.sub(r"<[^>]+>", " ", draft.body_html)

    prompt = f"""
You are the SEO module of AIROS. Optimize the following article for search engines.

ARTICLE HEADLINE: {draft.headline}
ARTICLE TOPIC: {draft.topic}
ARTICLE TEXT (first 2000 chars):
{text_only[:2000]}

YOUR TASK:
1. SEO title: compelling, 50-60 characters, includes primary keyword, slightly different from headline.
2. Meta description: 120-155 characters, includes keyword, creates click desire.
3. Primary keyword: the main search term this article targets.
4. Secondary keywords: 4-6 related terms.
5. Internal link suggestions: 3 topic areas this article could link to (general topics, not specific URLs).
6. Do NOT generate the schema markup — that is handled separately.

RESPOND ONLY WITH VALID JSON:
{{
  "seo_title": "...",
  "meta_description": "...",
  "primary_keyword": "...",
  "secondary_keywords": ["...", "...", "...", "..."],
  "internal_link_suggestions": ["...", "...", "..."]
}}
"""

    try:
        raw = llm_service.generate(prompt, json_mode=True, temperature=0.3)
        data = json.loads(raw)

        slug = _generate_slug(draft.headline)

        # Build Article schema markup
        schema = {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": draft.headline,
            "description": data.get("meta_description", ""),
            "keywords": [data.get("primary_keyword", "")] + data.get("secondary_keywords", []),
            "author": {
                "@type": "Organization",
                "name": "AIROS"
            },
            "publisher": {
                "@type": "Organization",
                "name": "AIROS News",
                "logo": {
                    "@type": "ImageObject",
                    "url": "https://airos.news/logo.png"
                }
            },
            "articleSection": draft.topic,
            "wordCount": draft.word_count,
        }

        pkg = SEOPackage(
            seo_title=data.get("seo_title", draft.headline)[:60],
            meta_description=data.get("meta_description", "")[:155],
            slug=slug,
            primary_keyword=data.get("primary_keyword", ""),
            secondary_keywords=data.get("secondary_keywords", []),
            schema_markup=schema,
            internal_link_suggestions=data.get("internal_link_suggestions", []),
        )

        logger.info(f"SEO complete | title='{pkg.seo_title}' | keyword='{pkg.primary_keyword}'")
        return pkg

    except Exception as e:
        logger.error(f"SEO agent failed | {e}")
        slug = _generate_slug(draft.headline)
        return SEOPackage(
            seo_title=draft.headline[:60],
            meta_description=draft.headline,
            slug=slug,
            primary_keyword=draft.topic,
            secondary_keywords=[],
            schema_markup={},
            internal_link_suggestions=[],
        )


def validate_output(pkg: SEOPackage) -> bool:
    return bool(pkg.seo_title) and bool(pkg.slug)


def report(pkg: SEOPackage) -> dict:
    return {
        "agent": "SEOIntelligenceAgent",
        "seo_title": pkg.seo_title,
        "primary_keyword": pkg.primary_keyword,
        "slug": pkg.slug,
    }
