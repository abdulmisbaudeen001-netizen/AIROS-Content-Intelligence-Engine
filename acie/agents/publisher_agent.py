"""
AIROS Content Intelligence Engine
Agent 9 — Publishing Agent

Formats the final article, injects SEO metadata, and publishes to Blogger.
"""

import json
from dataclasses import dataclass
from typing import Optional

from agents.writer_agent import ArticleDraftContent
from agents.seo_agent import SEOPackage
from cms import blogger
from logger import get_logger

logger = get_logger("publisher_agent")


@dataclass
class PublishResult:
    success: bool
    post_id: Optional[str]
    post_url: Optional[str]
    headline: str
    error: Optional[str] = None


def initialize():
    logger.info("Publishing Agent initialized.")


def validate_input(draft: ArticleDraftContent, seo: SEOPackage) -> bool:
    return draft.word_count > 200 and bool(draft.headline)


def _build_full_html(draft: ArticleDraftContent, seo: SEOPackage) -> str:
    """
    Assemble the final publishable HTML with:
    - JSON-LD schema markup
    - Subheadline
    - Article body
    - Source attribution footer
    """
    schema_json = json.dumps(seo.schema_markup, indent=2)

    html = f"""<script type="application/ld+json">
{schema_json}
</script>

"""

    if draft.subheadline:
        html += f'<p class="airos-deck"><em>{draft.subheadline}</em></p>\n\n'

    html += draft.body_html

    # Footer
    html += """

<hr/>
<p><small><em>This article was researched and written by AIROS, an autonomous AI content engine. 
All facts are sourced from multiple independent news sources and verified before publication.</em></small></p>
"""

    return html


def execute(
    draft: ArticleDraftContent,
    seo: SEOPackage,
    window: str = "general",
    labels: Optional[list] = None,
) -> PublishResult:
    """
    Build final HTML and publish to Blogger.
    """
    logger.info(f"Publishing | headline='{draft.headline}'")

    if not blogger.is_authenticated():
        return PublishResult(
            success=False,
            post_id=None,
            post_url=None,
            headline=draft.headline,
            error="Blogger not authenticated. Complete OAuth2 setup first.",
        )

    full_html = _build_full_html(draft, seo)

    # Use SEO title for Blogger title (slightly different from article headline)
    publish_title = seo.seo_title or draft.headline

    # Build labels from keyword + category
    post_labels = labels or []
    if seo.primary_keyword and seo.primary_keyword not in post_labels:
        post_labels.append(seo.primary_keyword)

    result = blogger.publish_post(
        title=publish_title,
        body_html=full_html,
        labels=post_labels[:5],  # Blogger recommends ≤5 labels
        is_draft=False,
    )

    if result:
        logger.info(f"Published | post_id={result['post_id']} | url={result['url']}")
        return PublishResult(
            success=True,
            post_id=result["post_id"],
            post_url=result["url"],
            headline=draft.headline,
        )
    else:
        logger.error("Publishing failed — Blogger returned no result.")
        return PublishResult(
            success=False,
            post_id=None,
            post_url=None,
            headline=draft.headline,
            error="Blogger publish returned None.",
        )


def validate_output(result: PublishResult) -> bool:
    return result.success and bool(result.post_id)


def report(result: PublishResult) -> dict:
    return {
        "agent": "PublishingAgent",
        "success": result.success,
        "post_id": result.post_id,
        "post_url": result.post_url,
        "error": result.error,
    }
