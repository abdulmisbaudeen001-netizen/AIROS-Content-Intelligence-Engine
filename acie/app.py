"""
AIROS Content Intelligence Engine
Main entry point — FastAPI application deployed on Render.

Endpoints:
  GET  /                    Health check
  GET  /auth/url            Get Google OAuth2 consent URL
  GET  /auth/callback       OAuth2 callback — Google redirects here after consent
  GET  /auth/status         Check if Blogger is authorized
  POST /run/{window}        Manually trigger a publishing window
  POST /run/topic/{topic}   Run pipeline for a specific topic
  GET  /status              Active workflow states
  GET  /articles            Recent published articles
  GET  /queue               Publication retry queue
  GET  /insights            Learning insights from past performance
"""

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from database.connection import init_db, SessionLocal
from database import repository
from cms import blogger
from orchestrator.orchestrator import Orchestrator
from memory import short_memory, long_memory
from scheduler import start_background
from logger import get_logger

logger = get_logger("app")

orchestrator = Orchestrator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AIROS Content Intelligence Engine starting...")
    init_db()
    long_memory.refresh()
    start_background()
    logger.info("AIROS ready.")
    yield
    logger.info("AIROS shutting down.")


app = FastAPI(
    title="AIROS Content Intelligence Engine",
    description="Autonomous AI publishing system",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/")
def health():
    return {
        "status": "running",
        "engine": "AIROS Content Intelligence Engine",
        "version": "1.0.0",
        "blogger_authenticated": blogger.is_authenticated(),
    }


# ---------------------------------------------------------------------------
# OAuth2 — Blogger authorization
# One-time setup. After completion, tokens are saved and auto-refreshed.
# ---------------------------------------------------------------------------

@app.get("/auth/url")
def get_auth_url():
    """
    Step 1 — Get the Google consent URL.
    Visit this URL in your browser to authorize AIROS to publish to Blogger.
    """
    from config import GOOGLE_REDIRECT_URI
    url = blogger.get_auth_url()
    return {
        "auth_url": url,
        "redirect_uri_configured": GOOGLE_REDIRECT_URI,
        "instruction": "Open auth_url in your browser. Google will redirect back to /auth/callback.",
    }


@app.get("/auth/callback")
def auth_callback(code: str = Query(...)):
    """
    Step 2 — Google redirects here with an authorization code.
    AIROS exchanges the code for tokens and saves them automatically.
    This endpoint must be registered in Google Cloud Console as an authorized redirect URI.
    """
    success = blogger.exchange_code(code)
    if success:
        return {
            "status": "success",
            "message": "AIROS is now authorized to publish to Blogger. You will not need to do this again.",
        }
    raise HTTPException(status_code=400, detail="OAuth2 code exchange failed. Check logs.")


@app.get("/auth/status")
def auth_status():
    return {
        "authenticated": blogger.is_authenticated(),
        "message": "Ready to publish." if blogger.is_authenticated() else "Not authorized. Visit /auth/url to complete setup.",
    }


# ---------------------------------------------------------------------------
# Manual publishing triggers
# ---------------------------------------------------------------------------

@app.post("/run/{window}")
def run_window(window: str):
    """
    Manually trigger a publishing window.
    window: morning | afternoon | evening | general
    Runs in background — returns immediately.
    """
    valid = {"morning", "afternoon", "evening", "general"}
    if window not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid window. Use one of: {sorted(valid)}")

    def _run():
        orchestrator.run_publishing_window(window)

    threading.Thread(target=_run, daemon=True, name=f"window-{window}").start()
    return {"status": "started", "window": window}


@app.post("/run/topic/{topic}")
def run_for_topic(topic: str):
    """
    Run the full pipeline for a specific topic.
    Useful for testing or manual article creation.
    """
    from agents.trend_agent import TopicOpportunity

    def _run():
        opportunity = TopicOpportunity(
            title=topic,
            category="General",
            trend_score=80.0,
            opportunity_score=80.0,
            source_urls=[],
            summary="Manual trigger",
        )
        orchestrator._run_single_article("manual", opportunity, "general")

    threading.Thread(target=_run, daemon=True, name=f"topic-{topic[:20]}").start()
    return {"status": "started", "topic": topic}


# ---------------------------------------------------------------------------
# Monitoring
# ---------------------------------------------------------------------------

@app.get("/status")
def status():
    active = short_memory.all_active()
    return {
        "active_workflows": len(active),
        "workflows": [
            {
                "id": wid,
                "stage": w.current_stage,
                "window": w.window,
                "completed": w.completed,
                "failed_stages": w.failed_stages,
                "error": w.error,
            }
            for wid, w in active.items()
        ],
    }


@app.get("/articles")
def recent_articles(limit: int = 20):
    with SessionLocal() as db:
        articles = repository.get_recent_publications(db, limit=limit)
        return [
            {
                "id": a.id,
                "headline": a.headline,
                "url": a.blogger_url,
                "word_count": a.word_count,
                "window": a.window,
                "published_at": str(a.published_at),
            }
            for a in articles
        ]


@app.get("/queue")
def publication_queue():
    with SessionLocal() as db:
        items = repository.get_pending_queue(db)
        return [
            {
                "id": i.id,
                "draft_id": i.draft_id,
                "window": i.scheduled_window,
                "retry_count": i.retry_count,
                "status": i.status,
            }
            for i in items
        ]


@app.get("/insights")
def learning_insights():
    return long_memory.get_all_insights()


# ---------------------------------------------------------------------------
# Entry point — Render uses uvicorn directly via start command
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    from config import APP_HOST, APP_PORT, DEBUG
    uvicorn.run("app:app", host=APP_HOST, port=APP_PORT, reload=DEBUG)
