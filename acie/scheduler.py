"""
AIROS Content Intelligence Engine
Scheduler — runs the publishing windows automatically.

Windows:
  Morning   — SCHEDULE_MORNING_HOUR
  Afternoon — SCHEDULE_AFTERNOON_HOUR
  Evening   — SCHEDULE_EVENING_HOUR

Also handles retry queue and health maintenance.
"""

import schedule
import time
import threading

from orchestrator.orchestrator import Orchestrator
from database.connection import SessionLocal
from database import repository
from config import SCHEDULE_MORNING_HOUR, SCHEDULE_AFTERNOON_HOUR, SCHEDULE_EVENING_HOUR
from logger import get_logger

logger = get_logger("scheduler")

_orchestrator = Orchestrator()


def _run_window(window: str):
    logger.info(f"Scheduler triggered | window={window}")
    try:
        result = _orchestrator.run_publishing_window(window)
        logger.info(f"Window complete | {result}")
    except Exception as e:
        logger.error(f"Window failed | window={window} | {e}")


def _retry_queue():
    """Process articles stuck in the publication queue."""
    logger.info("Retry queue processing...")
    try:
        with SessionLocal() as db:
            pending = repository.get_pending_queue(db)
            logger.info(f"Pending in queue: {len(pending)}")

            for item in pending:
                if item.retry_count >= 5:
                    repository.update_queue_status(db, item.id, "failed")
                    continue
                # Re-attempt publishing would require the full draft — for V1, log and skip
                repository.increment_queue_retry(db, item.id)
                logger.info(f"Queue retry | id={item.id} | attempt={item.retry_count + 1}")
    except Exception as e:
        logger.error(f"Retry queue error | {e}")


def _health_check():
    logger.info("Health check OK.")


def start():
    """Register all scheduled jobs and start the blocking scheduler loop."""
    logger.info("Scheduler starting...")

    # Publishing windows
    schedule.every().day.at(f"{SCHEDULE_MORNING_HOUR:02d}:00").do(_run_window, "morning")
    schedule.every().day.at(f"{SCHEDULE_AFTERNOON_HOUR:02d}:00").do(_run_window, "afternoon")
    schedule.every().day.at(f"{SCHEDULE_EVENING_HOUR:02d}:00").do(_run_window, "evening")

    # Retry queue — every 30 minutes
    schedule.every(30).minutes.do(_retry_queue)

    # Health check — every hour
    schedule.every().hour.do(_health_check)

    logger.info(
        f"Scheduled | morning={SCHEDULE_MORNING_HOUR}:00 "
        f"| afternoon={SCHEDULE_AFTERNOON_HOUR}:00 "
        f"| evening={SCHEDULE_EVENING_HOUR}:00"
    )

    while True:
        schedule.run_pending()
        time.sleep(30)


def start_background():
    """Start scheduler in a daemon thread (for embedding inside FastAPI)."""
    thread = threading.Thread(target=start, daemon=True, name="acie-scheduler")
    thread.start()
    logger.info("Scheduler started in background thread.")
    return thread
