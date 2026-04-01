import sqlite3
import logging
from typing import Set, List, Dict
from config import DB_PATH

logger = logging.getLogger(__name__)


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_jobs (
                job_id   INTEGER PRIMARY KEY,
                title    TEXT NOT NULL,
                company  TEXT NOT NULL,
                eligible INTEGER DEFAULT 0,
                seen_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    logger.info("Database initialised.")


def get_seen_job_ids() -> Set[int]:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT job_id FROM seen_jobs").fetchall()
    return {row[0] for row in rows}


def is_new_job(job_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT 1 FROM seen_jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
    return row is None


def mark_as_seen(job_id: int, title: str, company: str, eligible: bool):
    with sqlite3.connect(DB_PATH) as conn:
        try:
            conn.execute(
                "INSERT INTO seen_jobs (job_id, title, company, eligible) "
                "VALUES (?, ?, ?, ?)",
                (job_id, title, company, int(eligible)),
            )
            conn.commit()
            logger.info(f"Marked seen: [{job_id}] {title} @ {company}")
        except sqlite3.IntegrityError:
            pass


def bulk_mark_seen(jobs_raw: List[Dict]):
    """On first run, silently swallow all existing jobs so we don't spam."""
    with sqlite3.connect(DB_PATH) as conn:
        for job in jobs_raw:
            company = job.get("company", {}).get("name", "Unknown").strip()
            title   = job.get("title", "Unknown").strip()
            conn.execute(
                "INSERT OR IGNORE INTO seen_jobs (job_id, title, company, eligible) "
                "VALUES (?, ?, ?, ?)",
                (job["id"], title, company, int(job.get("eligible", False))),
            )
        conn.commit()
    logger.info(f"First run: bulk-marked {len(jobs_raw)} existing jobs as seen.")