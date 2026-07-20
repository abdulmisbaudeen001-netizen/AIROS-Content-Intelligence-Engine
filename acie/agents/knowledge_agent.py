"""
AIROS Content Intelligence Engine
Agent 4 — Knowledge Expansion Agent

Adds context, history, statistics, and analysis beyond what the sources contain.
This is what separates AIROS from a simple article summarizer.
"""

import json
from dataclasses import dataclass
from typing import List

from services import llm_service
from agents.verification_agent import VerificationResult
from logger import get_logger

logger = get_logger("knowledge_agent")


@dataclass
class KnowledgePackage:
    topic: str
    verified_facts: List[dict]
    expanded_context: str       # Historical background, statistics, expert context
    timeline: List[str]         # Key events in order
    key_entities: List[str]     # People, orgs, places involved
    analysis_angles: List[str]  # Angles the article can take to add unique value


def initialize():
    logger.info("Knowledge Expansion Agent initialized.")


def validate_input(result: VerificationResult) -> bool:
    return isinstance(result, VerificationResult)


def execute(result: VerificationResult) -> KnowledgePackage:
    """
    Ask LLM to expand verified facts with context, history, and analysis.
    """
    logger.info(f"Knowledge expansion | topic='{result.topic}'")

    facts_text = "\n".join(
        f"- {f['fact']} (confidence: {f['confidence']}%)"
        for f in result.verified_facts
    )

    prompt = f"""
You are the Knowledge Expansion module of AIROS. Your role is to enrich verified news facts with
background, context, and analysis — making the final article more valuable than simple reporting.

TOPIC: {result.topic}

VERIFIED FACTS:
{facts_text}

YOUR TASK — produce each section carefully:

1. EXPANDED CONTEXT (3-5 paragraphs):
   - Historical background relevant to this story
   - Previous related events
   - Statistics or data that add depth
   - Government or institutional context
   - Why this matters to readers

2. TIMELINE: List 5-8 key events (with dates where known) that led to this story.

3. KEY ENTITIES: List the people, organizations, and places central to this story.

4. ANALYSIS ANGLES: List 3 unique angles or insights this article can offer beyond what other outlets will report.

RESPOND ONLY WITH VALID JSON:
{{
  "expanded_context": "...",
  "timeline": ["2023-01: ...", "2024-03: ...", "..."],
  "key_entities": ["Person A", "Organization B", "Country C"],
  "analysis_angles": ["Angle 1: ...", "Angle 2: ...", "Angle 3: ..."]
}}
"""

    try:
        raw = llm_service.generate(prompt, json_mode=True, temperature=0.5, max_tokens=2000)
        data = json.loads(raw)

        pkg = KnowledgePackage(
            topic=result.topic,
            verified_facts=result.verified_facts,
            expanded_context=data.get("expanded_context", ""),
            timeline=data.get("timeline", []),
            key_entities=data.get("key_entities", []),
            analysis_angles=data.get("analysis_angles", []),
        )

        logger.info(
            f"Knowledge expansion complete | context_chars={len(pkg.expanded_context)} "
            f"| timeline={len(pkg.timeline)} | angles={len(pkg.analysis_angles)}"
        )
        return pkg

    except Exception as e:
        logger.error(f"Knowledge expansion failed | {e}")
        return KnowledgePackage(
            topic=result.topic,
            verified_facts=result.verified_facts,
            expanded_context="",
            timeline=[],
            key_entities=[],
            analysis_angles=[],
        )


def validate_output(pkg: KnowledgePackage) -> bool:
    return len(pkg.expanded_context) > 100


def report(pkg: KnowledgePackage) -> dict:
    return {
        "agent": "KnowledgeExpansionAgent",
        "context_chars": len(pkg.expanded_context),
        "timeline_events": len(pkg.timeline),
        "key_entities": len(pkg.key_entities),
        "analysis_angles": len(pkg.analysis_angles),
    }
