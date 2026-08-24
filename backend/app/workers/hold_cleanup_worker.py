"""HoldCleanupWorker — periodic sweep that expires stale HELD slot holds.
This is a defense-in-depth measure; booking itself also performs an inline
expiry check (hold_service._expire_stale_holds_for_doctor /
get_valid_hold), so a delayed or down beat scheduler can never let a stale
hold block a slot indefinitely.
"""
import logging

from app.core.db import session_scope
from app.services.hold_service import cleanup_expired_holds
from app.workers.celery_app import celery_app

logger = logging.getLogger("hold_cleanup_worker")


@celery_app.task(name="app.workers.hold_cleanup_worker.cleanup_expired_holds_task")
def cleanup_expired_holds_task() -> int:
    with session_scope() as db:
        count = cleanup_expired_holds(db)
        if count:
            logger.info("Expired %d stale slot holds", count)
        return count
