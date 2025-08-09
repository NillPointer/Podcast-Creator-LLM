from __future__ import annotations

from datetime import datetime

from app.logger import setup_logger


logger = setup_logger('progress')


# In-memory storage for job tracking (in production, use a database)
jobs: dict[str, dict] = {}


def increment_progress(job_id: str, increment: float) -> None:
    """Increment job progress and update timestamp."""
    if job_id not in jobs:
        logger.warning(f"Job not found: {job_id}")
        return
    jobs[job_id]["progress"] = jobs[job_id].get("progress", 0) + float(increment)
    jobs[job_id]["updated_at"] = datetime.now(datetime.UTC).isoformat()
    logger.info(
        f"Progress incremented for job {job_id}: {jobs[job_id]['progress']}"
    )


