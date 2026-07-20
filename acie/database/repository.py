"""
AIROS Content Intelligence Engine
Repository — all database read/write operations.
Agents and orchestrator interact with the DB only through this file.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from database.models import (
    Topic, Source, VerifiedFact, ArticleDraft, SEOMetadata,
    PublishedArticle, PublicationQueue, AnalyticsRecord, LearningRecord, SystemLog,
)


# ---------------------------------------------------------------------------
# Topics
# ---------------------------------------------------------------------------

def create_topic(db: Session, title: str, category: str = "", trend_score: float = 0.0) -> Topic:
    topic = Topic(title=title, category=category, trend_score=trend_score)
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


def get_topic(db: Session, topic_id: int) -> Optional[Topic]:
    return db.query(Topic).filter(Topic.id == topic_id).first()


def update_topic_status(db: Session, topic_id: int, status: str):
    db.query(Topic).filter(Topic.id == topic_id).update({"status": status})
    db.commit()


def update_topic_score(db: Session, topic_id: int, opportunity_score: float):
    db.query(Topic).filter(Topic.id == topic_id).update({"opportunity_score": opportunity_score})
    db.commit()


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

def save_source(db: Session, topic_id: int, url: str, title: str,
                content: str, source_name: str, reliability: float = 0.5) -> Source:
    src = Source(
        topic_id=topic_id, url=url, title=title,
        content=content, source_name=source_name, reliability_score=reliability,
    )
    db.add(src)
    db.commit()
    db.refresh(src)
    return src


def get_sources_for_topic(db: Session, topic_id: int) -> List[Source]:
    return db.query(Source).filter(Source.topic_id == topic_id).all()


# ---------------------------------------------------------------------------
# Verified Facts
# ---------------------------------------------------------------------------

def save_fact(db: Session, topic_id: int, fact: str, confidence: float, source_count: int) -> VerifiedFact:
    vf = VerifiedFact(topic_id=topic_id, fact=fact, confidence=confidence, source_count=source_count)
    db.add(vf)
    db.commit()
    db.refresh(vf)
    return vf


def get_facts_for_topic(db: Session, topic_id: int) -> List[VerifiedFact]:
    return db.query(VerifiedFact).filter(VerifiedFact.topic_id == topic_id).all()


# ---------------------------------------------------------------------------
# Article Drafts
# ---------------------------------------------------------------------------

def create_draft(db: Session, topic_id: int, headline: str, outline: dict, body: str, word_count: int) -> ArticleDraft:
    draft = ArticleDraft(
        topic_id=topic_id, headline=headline,
        outline=outline, body=body, word_count=word_count,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def update_draft_scores(db: Session, draft_id: int, quality: float, seo: float,
                        policy: float, originality: float, readability: float):
    db.query(ArticleDraft).filter(ArticleDraft.id == draft_id).update({
        "quality_score": quality,
        "seo_score": seo,
        "policy_score": policy,
        "originality_score": originality,
        "readability_score": readability,
        "updated_at": datetime.utcnow(),
    })
    db.commit()


def get_draft(db: Session, draft_id: int) -> Optional[ArticleDraft]:
    return db.query(ArticleDraft).filter(ArticleDraft.id == draft_id).first()


def increment_revision(db: Session, draft_id: int):
    draft = db.query(ArticleDraft).filter(ArticleDraft.id == draft_id).first()
    if draft:
        draft.revision_count += 1
        db.commit()


# ---------------------------------------------------------------------------
# SEO Metadata
# ---------------------------------------------------------------------------

def save_seo(db: Session, draft_id: int, seo_title: str, meta_desc: str,
             slug: str, keywords: list, schema: dict) -> SEOMetadata:
    seo = SEOMetadata(
        draft_id=draft_id, seo_title=seo_title, meta_description=meta_desc,
        slug=slug, keywords=keywords, schema_markup=schema,
    )
    db.add(seo)
    db.commit()
    db.refresh(seo)
    return seo


def get_seo_for_draft(db: Session, draft_id: int) -> Optional[SEOMetadata]:
    return db.query(SEOMetadata).filter(SEOMetadata.draft_id == draft_id).first()


# ---------------------------------------------------------------------------
# Published Articles
# ---------------------------------------------------------------------------

def record_publication(db: Session, topic_id: int, draft_id: int,
                       blogger_post_id: str, blogger_url: str,
                       headline: str, word_count: int, window: str) -> PublishedArticle:
    pub = PublishedArticle(
        topic_id=topic_id, draft_id=draft_id,
        blogger_post_id=blogger_post_id, blogger_url=blogger_url,
        headline=headline, word_count=word_count, window=window,
    )
    db.add(pub)
    db.commit()
    db.refresh(pub)
    return pub


def get_recent_publications(db: Session, limit: int = 20) -> List[PublishedArticle]:
    return (
        db.query(PublishedArticle)
        .order_by(PublishedArticle.published_at.desc())
        .limit(limit)
        .all()
    )


# ---------------------------------------------------------------------------
# Publication Queue
# ---------------------------------------------------------------------------

def enqueue(db: Session, draft_id: int, window: str) -> PublicationQueue:
    item = PublicationQueue(draft_id=draft_id, scheduled_window=window)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_pending_queue(db: Session) -> List[PublicationQueue]:
    return (
        db.query(PublicationQueue)
        .filter(PublicationQueue.status == "pending")
        .order_by(PublicationQueue.created_at)
        .all()
    )


def update_queue_status(db: Session, queue_id: int, status: str):
    db.query(PublicationQueue).filter(PublicationQueue.id == queue_id).update({"status": status})
    db.commit()


def increment_queue_retry(db: Session, queue_id: int):
    item = db.query(PublicationQueue).filter(PublicationQueue.id == queue_id).first()
    if item:
        item.retry_count += 1
        db.commit()


# ---------------------------------------------------------------------------
# System Logs
# ---------------------------------------------------------------------------

def log_event(db: Session, workflow_id: str, agent: str, event: str,
              detail: str = "", level: str = "INFO"):
    entry = SystemLog(
        workflow_id=workflow_id, agent=agent,
        event=event, detail=detail, level=level,
    )
    db.add(entry)
    db.commit()


# ---------------------------------------------------------------------------
# Learning Records
# ---------------------------------------------------------------------------

def upsert_learning(db: Session, insight_type: str, insight_value: str,
                    confidence: float, sample_size: int):
    record = db.query(LearningRecord).filter(LearningRecord.insight_type == insight_type).first()
    if record:
        record.insight_value = insight_value
        record.confidence = confidence
        record.sample_size = sample_size
        record.updated_at = datetime.utcnow()
    else:
        record = LearningRecord(
            insight_type=insight_type, insight_value=insight_value,
            confidence=confidence, sample_size=sample_size,
        )
        db.add(record)
    db.commit()


def get_all_learnings(db: Session) -> List[LearningRecord]:
    return db.query(LearningRecord).all()
