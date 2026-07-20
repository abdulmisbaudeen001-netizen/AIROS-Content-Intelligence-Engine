"""
AIROS Content Intelligence Engine
Agent 6 — Content Generation Agent

Writes the complete article using the editorial plan and knowledge package.
Produces human-like, original synthesis — not a summary.
"""

import json
from dataclasses import dataclass
from typing import List

from services import llm_service
from agents.editor_agent import EditorialPlan
from agents.knowledge_agent import KnowledgePackage
from config import ARTICLE_EDITORIAL_VOICE
from logger import get_logger

logger = get_logger("writer_agent")


@dataclass
class ArticleDraftContent:
    topic: str
    headline: str
    subheadline: str
    body_html: str              # Full article as HTML (Blogger-ready)
    word_count: int
    sections_written: List[str]


def initialize():
    logger.info("Content Generation Agent initialized.")


def validate_input(plan: EditorialPlan, pkg: KnowledgePackage) -> bool:
    return bool(plan.headline) and len(plan.sections) >= 2


def execute(plan: EditorialPlan, pkg: KnowledgePackage) -> ArticleDraftContent:
    """
    Write the complete article section by section, then assemble.
    """
    logger.info(f"Writing article | headline='{plan.headline}' | target={plan.target_word_count} words")

    facts_text = "\n".join(f"- {f['fact']}" for f in pkg.verified_facts[:30])
    sections_text = json.dumps(plan.sections, indent=2)
    timeline_text = "\n".join(pkg.timeline)

    prompt = f"""
You are the Content Generation module of AIROS, an autonomous publishing engine.
Write a complete, original news article based on the plan and knowledge provided.

ARTICLE PLAN:
Headline: {plan.headline}
Subheadline: {plan.subheadline}
Tone: {plan.tone}
Target Length: {plan.target_word_count} words
Editorial Voice: {ARTICLE_EDITORIAL_VOICE}

SECTIONS TO WRITE:
{sections_text}

VERIFIED FACTS (use these — do not invent facts):
{facts_text}

BACKGROUND CONTEXT:
{pkg.expanded_context[:3000]}

TIMELINE:
{timeline_text}

ANALYSIS ANGLES (incorporate where relevant):
{chr(10).join(pkg.analysis_angles)}

FAQ QUESTIONS TO ANSWER (add as FAQ section at the end):
{chr(10).join(plan.faq_questions)}

WRITING RULES:
1. Write in HTML format suitable for Blogger (use <h2>, <h3>, <p>, <ul>, <strong>).
2. Do NOT use <html>, <head>, or <body> tags — just the content HTML.
3. Lead with the most important fact in the first paragraph.
4. Each section must add new information — no repetition.
5. Write naturally, like a professional journalist — not like an AI.
6. Avoid: "In conclusion", "It is worth noting", "It is important to note", "Delve", "Navigate", "Landscape".
7. Cite sources inline using parenthetical references where appropriate.
8. End with a FAQ section using <h2>Frequently Asked Questions</h2> and <h3> for each question.
9. Minimum {plan.target_word_count} words.

RESPOND ONLY WITH THE HTML ARTICLE CONTENT. No preamble. No explanation.
"""

    try:
        body_html = llm_service.generate(
            prompt,
            temperature=0.7,
            max_tokens=4096,
        )

        # Clean any accidental markdown fences
        body_html = body_html.strip()
        if body_html.startswith("```"):
            body_html = body_html.split("```", 2)[-1] if len(body_html.split("```")) > 2 else body_html
            body_html = body_html.strip()

        # Estimate word count from HTML
        import re
        text_only = re.sub(r"<[^>]+>", " ", body_html)
        word_count = len(text_only.split())

        draft = ArticleDraftContent(
            topic=pkg.topic,
            headline=plan.headline,
            subheadline=plan.subheadline,
            body_html=body_html,
            word_count=word_count,
            sections_written=[s.get("title", "") for s in plan.sections],
        )

        logger.info(f"Article written | words={word_count} | chars={len(body_html)}")
        return draft

    except Exception as e:
        logger.error(f"Content generation failed | {e}")
        return ArticleDraftContent(
            topic=pkg.topic,
            headline=plan.headline,
            subheadline=plan.subheadline,
            body_html=f"<p>Article generation failed: {e}</p>",
            word_count=0,
            sections_written=[],
        )


def validate_output(draft: ArticleDraftContent) -> bool:
    return draft.word_count >= 400


def report(draft: ArticleDraftContent) -> dict:
    return {
        "agent": "ContentGenerationAgent",
        "headline": draft.headline,
        "word_count": draft.word_count,
        "sections_written": len(draft.sections_written),
    }
