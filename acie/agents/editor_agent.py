"""
AIROS Content Intelligence Engine
Agent 5 — Editorial Agent

Designs the article structure before writing begins.
Produces headline, outline, tone, and section plan.
"""

import json
from dataclasses import dataclass
from typing import List

from services import llm_service
from agents.knowledge_agent import KnowledgePackage
from memory import long_memory
from config import ARTICLE_EDITORIAL_VOICE, ARTICLE_MIN_WORDS, ARTICLE_MAX_WORDS
from logger import get_logger

logger = get_logger("editor_agent")


@dataclass
class EditorialPlan:
    topic: str
    headline: str
    subheadline: str
    sections: List[dict]       # [{title, purpose, key_points}]
    tone: str
    target_word_count: int
    faq_questions: List[str]


def initialize():
    logger.info("Editorial Agent initialized.")


def validate_input(pkg: KnowledgePackage) -> bool:
    return isinstance(pkg, KnowledgePackage) and bool(pkg.topic)


def execute(pkg: KnowledgePackage) -> EditorialPlan:
    """
    Plan the article structure using knowledge package + editorial learnings.
    """
    logger.info(f"Editorial planning | topic='{pkg.topic}'")

    # Pull any learned best practices
    best_structure = long_memory.get_insight("best_content_structure", "")
    best_headline = long_memory.get_insight("best_headline_style", "")

    facts_text = "\n".join(f"- {f['fact']}" for f in pkg.verified_facts[:20])

    prompt = f"""
You are the Editorial Planning module of AIROS. Your job is to design a compelling article
before any writing begins.

TOPIC: {pkg.topic}

VERIFIED FACTS:
{facts_text}

ANALYSIS ANGLES AVAILABLE:
{chr(10).join(pkg.analysis_angles)}

KEY ENTITIES: {', '.join(pkg.key_entities)}

EDITORIAL VOICE: {ARTICLE_EDITORIAL_VOICE}

TARGET LENGTH: {ARTICLE_MIN_WORDS}-{ARTICLE_MAX_WORDS} words

{f"BEST PERFORMING HEADLINE STYLE (from past articles): {best_headline}" if best_headline else ""}
{f"BEST PERFORMING STRUCTURE (from past articles): {best_structure}" if best_structure else ""}

YOUR TASK:
1. Write the main headline (under 65 characters, compelling, informative).
2. Write a subheadline / deck (1 sentence, adds context to headline).
3. Design 5-7 sections. Each section needs:
   - title: section header (shown to reader)
   - purpose: what this section achieves (internal note)
   - key_points: 2-4 bullets of what to cover
4. Specify the tone (e.g., Analytical, Investigative, Explainer, Breaking News).
5. Generate 3-5 FAQ questions readers would ask about this topic.

RESPOND ONLY WITH VALID JSON:
{{
  "headline": "...",
  "subheadline": "...",
  "tone": "...",
  "target_word_count": 1200,
  "sections": [
    {{
      "title": "Introduction",
      "purpose": "Hook the reader and state the core news",
      "key_points": ["Lead with the most important fact", "Establish why this matters"]
    }}
  ],
  "faq_questions": ["What is...", "Why did...", "How will..."]
}}
"""

    try:
        raw = llm_service.generate(prompt, json_mode=True, temperature=0.4)
        data = json.loads(raw)

        plan = EditorialPlan(
            topic=pkg.topic,
            headline=data.get("headline", pkg.topic),
            subheadline=data.get("subheadline", ""),
            sections=data.get("sections", []),
            tone=data.get("tone", "Informative"),
            target_word_count=int(data.get("target_word_count", ARTICLE_MIN_WORDS)),
            faq_questions=data.get("faq_questions", []),
        )

        logger.info(f"Editorial plan complete | headline='{plan.headline}' | sections={len(plan.sections)}")
        return plan

    except Exception as e:
        logger.error(f"Editorial planning failed | {e}")
        return EditorialPlan(
            topic=pkg.topic,
            headline=pkg.topic,
            subheadline="",
            sections=[
                {"title": "Overview", "purpose": "Cover the story", "key_points": ["Report facts"]},
                {"title": "Background", "purpose": "Context", "key_points": ["Historical context"]},
                {"title": "Analysis", "purpose": "Depth", "key_points": ["Implications"]},
                {"title": "Conclusion", "purpose": "Wrap up", "key_points": ["Summary"]},
            ],
            tone="Informative",
            target_word_count=ARTICLE_MIN_WORDS,
            faq_questions=[],
        )


def validate_output(plan: EditorialPlan) -> bool:
    return bool(plan.headline) and len(plan.sections) >= 3


def report(plan: EditorialPlan) -> dict:
    return {
        "agent": "EditorialAgent",
        "headline": plan.headline,
        "sections": len(plan.sections),
        "tone": plan.tone,
        "faq_questions": len(plan.faq_questions),
    }
