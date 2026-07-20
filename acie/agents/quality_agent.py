"""
AIROS Content Intelligence Engine
Agent 8 — Policy & Quality Agent

Scores the article against Google quality guidelines, AdSense policies,
editorial standards, SEO rules, and originality requirements.
Produces a quality scorecard. Articles below threshold are flagged for revision.
"""

import json
import re
from dataclasses import dataclass

from services import llm_service
from agents.writer_agent import ArticleDraftContent
from config import MIN_QUALITY_SCORE, MIN_SEO_SCORE, MIN_POLICY_SCORE, MIN_ORIGINALITY_SCORE, MIN_READABILITY_SCORE
from logger import get_logger

logger = get_logger("quality_agent")


@dataclass
class QualityReport:
    quality_score: float
    seo_score: float
    policy_score: float
    originality_score: float
    readability_score: float
    passed: bool
    issues: list
    suggestions: list
    revision_prompt: str    # Specific instruction to send back to writer if revision needed


def initialize():
    logger.info("Policy & Quality Agent initialized.")


def validate_input(draft: ArticleDraftContent) -> bool:
    return draft.word_count > 100


def execute(draft: ArticleDraftContent) -> QualityReport:
    logger.info(f"Quality check | headline='{draft.headline}' | words={draft.word_count}")

    text_only = re.sub(r"<[^>]+>", " ", draft.body_html)

    prompt = f"""
You are the Quality & Policy Review module of AIROS. Evaluate this article against all standards.

ARTICLE HEADLINE: {draft.headline}
WORD COUNT: {draft.word_count}

ARTICLE TEXT:
{text_only[:6000]}

SCORING CRITERIA — assign 0-100 for each:

1. QUALITY SCORE: Does the article have depth, original insight, clear structure, and a strong opening?
   Minimum passing: {MIN_QUALITY_SCORE}

2. SEO SCORE: Is the article well-structured for search? Does it answer clear search intent? Clear headers?
   Minimum passing: {MIN_SEO_SCORE}

3. POLICY SCORE: Does it comply with Google AdSense policies? No hate speech, violence, misleading content,
   political extremism, unverified medical claims, or adult content?
   Minimum passing: {MIN_POLICY_SCORE}

4. ORIGINALITY SCORE: Does the article add value beyond simply repeating other sources? Original analysis?
   Minimum passing: {MIN_ORIGINALITY_SCORE}

5. READABILITY SCORE: Is the writing clear, well-paced, and free of AI filler phrases?
   Check for: "It is worth noting", "Delve", "Navigate the landscape", "In conclusion", "Furthermore".
   Minimum passing: {MIN_READABILITY_SCORE}

FOR ANY FAILED CATEGORY:
- List specific issues found.
- Provide actionable suggestions to fix.
- Write a revision_prompt: a direct instruction the writer agent can act on to improve the article.

RESPOND ONLY WITH VALID JSON:
{{
  "quality_score": 88,
  "seo_score": 85,
  "policy_score": 100,
  "originality_score": 78,
  "readability_score": 82,
  "issues": ["Issue 1...", "Issue 2..."],
  "suggestions": ["Suggestion 1...", "Suggestion 2..."],
  "revision_prompt": "Rewrite the introduction to lead with the most impactful fact. Remove the phrase 'It is worth noting'. Add one more analysis point in the Analysis section."
}}
"""

    try:
        raw = llm_service.generate(prompt, json_mode=True, temperature=0.2)
        data = json.loads(raw)

        q = float(data.get("quality_score", 0))
        s = float(data.get("seo_score", 0))
        p = float(data.get("policy_score", 0))
        o = float(data.get("originality_score", 0))
        r = float(data.get("readability_score", 0))

        passed = (
            q >= MIN_QUALITY_SCORE and
            s >= MIN_SEO_SCORE and
            p >= MIN_POLICY_SCORE and
            o >= MIN_ORIGINALITY_SCORE and
            r >= MIN_READABILITY_SCORE
        )

        report = QualityReport(
            quality_score=q,
            seo_score=s,
            policy_score=p,
            originality_score=o,
            readability_score=r,
            passed=passed,
            issues=data.get("issues", []),
            suggestions=data.get("suggestions", []),
            revision_prompt=data.get("revision_prompt", ""),
        )

        status = "PASSED" if passed else "FAILED"
        logger.info(
            f"Quality check {status} | Q={q} SEO={s} Policy={p} Orig={o} Read={r}"
        )
        return report

    except Exception as e:
        logger.error(f"Quality check failed | {e}")
        return QualityReport(
            quality_score=0, seo_score=0, policy_score=0,
            originality_score=0, readability_score=0,
            passed=False,
            issues=[str(e)],
            suggestions=["Manual review required"],
            revision_prompt="",
        )


def validate_output(report: QualityReport) -> bool:
    return isinstance(report, QualityReport)


def report_summary(qr: QualityReport) -> dict:
    return {
        "agent": "PolicyQualityAgent",
        "passed": qr.passed,
        "quality": qr.quality_score,
        "seo": qr.seo_score,
        "policy": qr.policy_score,
        "originality": qr.originality_score,
        "readability": qr.readability_score,
        "issues_count": len(qr.issues),
    }
