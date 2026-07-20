"""
AIROS Content Intelligence Engine
Agent 3 — Verification Agent

Cross-checks facts across sources. Outputs verified facts with confidence scores.
"""

import json
from dataclasses import dataclass
from typing import List

from services import llm_service
from agents.source_agent import SourcePackage
from logger import get_logger

logger = get_logger("verification_agent")


@dataclass
class VerificationResult:
    topic: str
    verified_facts: List[dict]      # [{fact, confidence, source_count}]
    conflicts: List[str]            # facts that contradict across sources
    overall_confidence: float       # 0-100


def initialize():
    logger.info("Verification Agent initialized.")


def validate_input(pkg: SourcePackage) -> bool:
    return pkg.source_count >= 1 and len(pkg.merged_text) > 100


def execute(pkg: SourcePackage) -> VerificationResult:
    """
    Send merged source text to LLM for cross-source fact extraction and verification.
    """
    logger.info(f"Verification | topic='{pkg.topic}' | sources={pkg.source_count}")

    prompt = f"""
You are the Verification module of AIROS. Your job is to extract and verify facts from multiple news sources.

TOPIC: {pkg.topic}

SOURCE MATERIAL (from {pkg.source_count} independent sources):
{pkg.merged_text[:12000]}

YOUR TASK:
1. Extract all significant facts (names, dates, numbers, events, statements).
2. For each fact:
   - Count how many sources mention it (source_count).
   - Assign confidence: 90-100 if 3+ sources agree, 70-89 if 2 sources agree, 50-69 if only 1 source.
   - Mark as "conflict" if sources contradict each other.
3. List any contradictions between sources.
4. Compute overall_confidence: average confidence across all verified facts.

RESPOND ONLY WITH VALID JSON:
{{
  "verified_facts": [
    {{"fact": "...", "confidence": 95, "source_count": 3}},
    {{"fact": "...", "confidence": 75, "source_count": 2}}
  ],
  "conflicts": [
    "Source A says X but Source B says Y"
  ],
  "overall_confidence": 87.5
}}
"""

    try:
        raw = llm_service.generate(prompt, json_mode=True, temperature=0.1)
        data = json.loads(raw)

        result = VerificationResult(
            topic=pkg.topic,
            verified_facts=data.get("verified_facts", []),
            conflicts=data.get("conflicts", []),
            overall_confidence=float(data.get("overall_confidence", 50.0)),
        )

        logger.info(
            f"Verification complete | facts={len(result.verified_facts)} "
            f"| conflicts={len(result.conflicts)} | confidence={result.overall_confidence}"
        )
        return result

    except Exception as e:
        logger.error(f"Verification failed | {e}")
        # Return minimal result so pipeline can continue
        return VerificationResult(
            topic=pkg.topic,
            verified_facts=[],
            conflicts=[],
            overall_confidence=0.0,
        )


def validate_output(result: VerificationResult) -> bool:
    return len(result.verified_facts) > 0


def report(result: VerificationResult) -> dict:
    return {
        "agent": "VerificationAgent",
        "verified_facts": len(result.verified_facts),
        "conflicts": len(result.conflicts),
        "overall_confidence": result.overall_confidence,
    }
