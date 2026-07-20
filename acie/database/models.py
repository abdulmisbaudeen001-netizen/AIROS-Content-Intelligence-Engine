"""
AIROS Content Intelligence Engine
ORM models — one class per table.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, JSON
from database.connection import Base


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    category = Column(String(100))
    trend_score = Column(Float, default=0.0)
    opportunity_score = Column(Float, default=0.0)
    source_count = Column(Integer, default=0)
    status = Column(String(50), default="discovered")  # discovered | processing | published | failed
    detected_at = Column(DateTime, default=datetime.utcnow)


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, nullable=False, index=True)
    url = Column(String(2000))
    title = Column(String(500))
    content = Column(Text)
    source_name = Column(String(200))
    reliability_score = Column(Float, default=0.5)
    collected_at = Column(DateTime, default=datetime.utcnow)


class VerifiedFact(Base):
    __tablename__ = "verified_facts"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, nullable=False, index=True)
    fact = Column(Text)
    confidence = Column(Float, default=0.0)
    source_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class ArticleDraft(Base):
    __tablename__ = "article_drafts"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, nullable=False, index=True)
    headline = Column(String(500))
    outline = Column(JSON)
    body = Column(Text)
    word_count = Column(Integer, default=0)
    quality_score = Column(Float, default=0.0)
    seo_score = Column(Float, default=0.0)
    policy_score = Column(Float, default=0.0)
    originality_score = Column(Float, default=0.0)
    readability_score = Column(Float, default=0.0)
    revision_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SEOMetadata(Base):
    __tablename__ = "seo_metadata"

    id = Column(Integer, primary_key=True, index=True)
    draft_id = Column(Integer, nullable=False, index=True)
    seo_title = Column(String(70))
    meta_description = Column(String(160))
    slug = Column(String(200))
    keywords = Column(JSON)  # list of strings
    schema_markup = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class PublishedArticle(Base):
    __tablename__ = "published_articles"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, nullable=False, index=True)
    draft_id = Column(Integer, nullable=False)
    blogger_post_id = Column(String(100))
    blogger_url = Column(String(2000))
    headline = Column(String(500))
    word_count = Column(Integer)
    published_at = Column(DateTime, default=datetime.utcnow)
    window = Column(String(20))  # morning | afternoon | evening


class PublicationQueue(Base):
    __tablename__ = "publication_queue"

    id = Column(Integer, primary_key=True, index=True)
    draft_id = Column(Integer, nullable=False, index=True)
    scheduled_window = Column(String(20))
    retry_count = Column(Integer, default=0)
    status = Column(String(50), default="pending")  # pending | publishing | done | failed
    created_at = Column(DateTime, default=datetime.utcnow)


class AnalyticsRecord(Base):
    __tablename__ = "analytics"

    id = Column(Integer, primary_key=True, index=True)
    published_article_id = Column(Integer, nullable=False, index=True)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    recorded_at = Column(DateTime, default=datetime.utcnow)


class LearningRecord(Base):
    __tablename__ = "learning_records"

    id = Column(Integer, primary_key=True, index=True)
    insight_type = Column(String(100))   # e.g. "best_headline_style", "best_publish_window"
    insight_value = Column(Text)
    confidence = Column(Float, default=0.0)
    sample_size = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(String(100), index=True)
    agent = Column(String(100))
    event = Column(String(200))
    detail = Column(Text)
    level = Column(String(20), default="INFO")
    timestamp = Column(DateTime, default=datetime.utcnow)
