"""
AIROS Content Intelligence Engine
Orchestrator — the central brain.

Controls the full pipeline. No agent talks to another directly.
All data flows through here.

Pipeline:
  trend → source → verify → expand → edit → write → seo → quality → publish → learn
"""

import uuid
from datetime import datetime
from typing import Optional

from agents import (
    trend_agent, source_agent, verification_agent,
    knowledge_agent, editor_agent, writer_agent,
    seo_agent, quality_agent, publisher_agent, learning_agent,
)
from database.connection import SessionLocal
from database import repository
from memory import short_memory, long_memory
from logger import get_logger

logger = get_logger("orchestrator")

MAX_REVISION_ATTEMPTS = 2
MAX_SOURCE_RETRIES = 2


class Orchestrator:

    def run_publishing_window(self, window: str = "general") -> dict:
        """
        Execute one full publishing window.
        Discovers topics and publishes SCHEDULE_TOPICS_PER_RUN articles.
        """
        from config import SCHEDULE_TOPICS_PER_RUN

        workflow_id = f"{window}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        logger.info(f"=== WORKFLOW START | id={workflow_id} | window={window} ===")

        state = short_memory.start_workflow(workflow_id, window)
        results = []

        try:
            long_memory.refresh()

            # Stage 1: Trend Discovery
            short_memory.update_stage(workflow_id, "trend")
            opportunities = self._run_trend_discovery(workflow_id)
            if not opportunities:
                return self._abort(workflow_id, "No topics discovered.")

            state.discovered_topics = [
                {"title": o.title, "score": o.opportunity_score, "urls": o.source_urls}
                for o in opportunities
            ]

            # Publish top N topics
            for opportunity in opportunities[:SCHEDULE_TOPICS_PER_RUN]:
                result = self._run_single_article(workflow_id, opportunity, window)
                results.append(result)

            # Stage 10: Learning
            short_memory.update_stage(workflow_id, "learn")
            learning_agent.execute()

        except Exception as e:
            logger.error(f"Workflow error | id={workflow_id} | {e}")
            short_memory.mark_stage_failed(workflow_id, state.current_stage, str(e))

        finally:
            short_memory.complete_workflow(workflow_id)
            logger.info(f"=== WORKFLOW END | id={workflow_id} | articles={len(results)} ===")

        return {
            "workflow_id": workflow_id,
            "window": window,
            "articles_published": len([r for r in results if r.get("published")]),
            "results": results,
        }

    def _run_single_article(self, workflow_id: str, opportunity, window: str) -> dict:
        """Run the full pipeline for one topic → one published article."""
        result = {"topic": opportunity.title, "published": False}

        try:
            with SessionLocal() as db:
                # Save topic
                topic_row = repository.create_topic(
                    db, opportunity.title, opportunity.category, opportunity.trend_score
                )
                repository.update_topic_score(db, topic_row.id, opportunity.opportunity_score)
                topic_id = topic_row.id

                repository.log_event(db, workflow_id, "orchestrator", "topic_selected", opportunity.title)

            # Stage 2: Source Collection
            short_memory.update_stage(workflow_id, "source")
            source_pkg = self._run_source_collection(workflow_id, opportunity, topic_id)
            if not source_pkg:
                return result

            # Stage 3: Verification
            short_memory.update_stage(workflow_id, "verify")
            verification = self._run_verification(workflow_id, source_pkg, topic_id)
            if not verification:
                return result

            # Stage 4: Knowledge Expansion
            short_memory.update_stage(workflow_id, "expand")
            knowledge = self._run_knowledge_expansion(workflow_id, verification)

            # Stage 5 + 6: Editorial Plan + Writing (with revision loop)
            short_memory.update_stage(workflow_id, "write")
            draft, plan = self._run_writing_with_revision(workflow_id, knowledge, topic_id)
            if not draft:
                return result

            # Stage 7: SEO
            short_memory.update_stage(workflow_id, "seo")
            seo = self._run_seo(workflow_id, draft, topic_id)

            # Stage 9: Publish
            short_memory.update_stage(workflow_id, "publish")
            publish_result = self._run_publishing(
                workflow_id, draft, seo, plan, topic_id, window
            )

            if publish_result and publish_result.success:
                result["published"] = True
                result["url"] = publish_result.post_url
                result["post_id"] = publish_result.post_id

        except Exception as e:
            logger.error(f"Article pipeline error | topic='{opportunity.title}' | {e}")
            result["error"] = str(e)

        return result

    # ------------------------------------------------------------------
    # Individual stage runners
    # ------------------------------------------------------------------

    def _run_trend_discovery(self, workflow_id: str):
        try:
            from config import SCHEDULE_TOPICS_PER_RUN
            opportunities = trend_agent.execute(top_n=SCHEDULE_TOPICS_PER_RUN + 2)
            if not trend_agent.validate_output(opportunities):
                logger.warning("Trend agent output invalid.")
                return None
            logger.info(trend_agent.report(opportunities))
            return opportunities
        except Exception as e:
            logger.error(f"Trend discovery failed | {e}")
            return None

    def _run_source_collection(self, workflow_id, opportunity, topic_id):
        retries = 0
        while retries <= MAX_SOURCE_RETRIES:
            try:
                pkg = source_agent.execute(opportunity.title, opportunity.source_urls)
                if source_agent.validate_output(pkg):
                    # Persist sources
                    with SessionLocal() as db:
                        for src in pkg.sources:
                            repository.save_source(
                                db, topic_id, src["url"], src["title"],
                                src["content"], src["source_name"],
                            )
                        repository.log_event(db, workflow_id, "source_agent", "sources_collected",
                                             f"{pkg.source_count} sources")
                    logger.info(source_agent.report(pkg))
                    return pkg

                logger.warning(f"Source collection insufficient | retry {retries + 1}")
                retries += 1
            except Exception as e:
                logger.error(f"Source agent error | {e}")
                retries += 1

        logger.error("Source collection exhausted retries.")
        return None

    def _run_verification(self, workflow_id, source_pkg, topic_id):
        try:
            result = verification_agent.execute(source_pkg)
            if not verification_agent.validate_output(result):
                logger.warning("Verification returned no facts.")
                # Don't abort — continue with empty verification
            else:
                with SessionLocal() as db:
                    for fact in result.verified_facts:
                        repository.save_fact(
                            db, topic_id, fact["fact"],
                            fact["confidence"], fact["source_count"],
                        )
                    repository.log_event(db, workflow_id, "verification_agent", "verified",
                                         f"{len(result.verified_facts)} facts")
            logger.info(verification_agent.report(result))
            return result
        except Exception as e:
            logger.error(f"Verification error | {e}")
            return None

    def _run_knowledge_expansion(self, workflow_id, verification):
        try:
            pkg = knowledge_agent.execute(verification)
            logger.info(knowledge_agent.report(pkg))
            return pkg
        except Exception as e:
            logger.error(f"Knowledge expansion error | {e}")
            # Return minimal package — pipeline can continue
            from agents.knowledge_agent import KnowledgePackage
            return KnowledgePackage(
                topic=verification.topic,
                verified_facts=verification.verified_facts,
                expanded_context="",
                timeline=[],
                key_entities=[],
                analysis_angles=[],
            )

    def _run_writing_with_revision(self, workflow_id, knowledge, topic_id):
        """Edit → Write → Quality check → Revise if needed."""
        plan = editor_agent.execute(knowledge)

        for attempt in range(1, MAX_REVISION_ATTEMPTS + 2):
            draft = writer_agent.execute(plan, knowledge)
            if not writer_agent.validate_output(draft):
                logger.warning(f"Writer output invalid | attempt {attempt}")
                continue

            # Quality gate
            qr = quality_agent.execute(draft)
            logger.info(quality_agent.report_summary(qr))

            if qr.passed:
                # Save draft to DB
                with SessionLocal() as db:
                    draft_row = repository.create_draft(
                        db, topic_id, draft.headline, {},
                        draft.body_html, draft.word_count,
                    )
                    repository.update_draft_scores(
                        db, draft_row.id,
                        qr.quality_score, qr.seo_score, qr.policy_score,
                        qr.originality_score, qr.readability_score,
                    )
                    repository.log_event(db, workflow_id, "writer_agent", "draft_passed",
                                         f"quality={qr.quality_score}")
                return draft, plan

            if attempt <= MAX_REVISION_ATTEMPTS and qr.revision_prompt:
                logger.info(f"Quality failed — revising | attempt={attempt} | prompt='{qr.revision_prompt[:80]}'")
                # Inject revision instruction into editorial plan
                plan.sections.insert(0, {
                    "title": "REVISION INSTRUCTION",
                    "purpose": qr.revision_prompt,
                    "key_points": qr.suggestions,
                })
                with SessionLocal() as db:
                    repository.log_event(db, workflow_id, "quality_agent", "revision_requested",
                                         qr.revision_prompt[:200])

        logger.warning("Draft failed quality after max revisions — publishing best version anyway.")
        return draft, plan

    def _run_seo(self, workflow_id, draft, topic_id):
        try:
            seo = seo_agent.execute(draft)
            with SessionLocal() as db:
                repository.save_seo(
                    db, topic_id, seo.seo_title, seo.meta_description,
                    seo.slug, seo.secondary_keywords, seo.schema_markup,
                )
                repository.log_event(db, workflow_id, "seo_agent", "seo_complete", seo.seo_title)
            logger.info(seo_agent.report(seo))
            return seo
        except Exception as e:
            logger.error(f"SEO agent error | {e}")
            from agents.seo_agent import SEOPackage
            return SEOPackage(
                seo_title=draft.headline[:60],
                meta_description=draft.headline,
                slug=draft.headline.lower().replace(" ", "-")[:60],
                primary_keyword=draft.topic,
                secondary_keywords=[],
                schema_markup={},
                internal_link_suggestions=[],
            )

    def _run_publishing(self, workflow_id, draft, seo, plan, topic_id, window):
        try:
            category = getattr(plan, "category", "General")
            result = publisher_agent.execute(draft, seo, window, labels=[category])

            with SessionLocal() as db:
                if result.success:
                    repository.record_publication(
                        db, topic_id, topic_id,
                        result.post_id, result.post_url,
                        draft.headline, draft.word_count, window,
                    )
                    repository.log_event(db, workflow_id, "publisher_agent", "published",
                                         result.post_url or "")
                else:
                    # Queue for retry
                    repository.enqueue(db, topic_id, window)
                    repository.log_event(db, workflow_id, "publisher_agent", "queued_for_retry",
                                         result.error or "")

            logger.info(publisher_agent.report(result))
            return result

        except Exception as e:
            logger.error(f"Publishing error | {e}")
            return None

    def _abort(self, workflow_id: str, reason: str) -> dict:
        short_memory.mark_stage_failed(workflow_id, "abort", reason)
        short_memory.complete_workflow(workflow_id)
        logger.error(f"Workflow aborted | {reason}")
        return {"workflow_id": workflow_id, "aborted": True, "reason": reason}
