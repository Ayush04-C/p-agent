import logging
import schedule
import time
from config import CHECK_INTERVAL_MINUTES
from state import init_db, is_new_job, mark_as_seen, bulk_mark_seen, get_seen_job_ids
from notifier import notify
from scraper import fetch_jobs, extract_job_info

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("agent.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

IS_FIRST_RUN = True


def run_check():
    global IS_FIRST_RUN
    logger.info("========== Starting check ==========")

    jobs_raw = fetch_jobs()

    if jobs_raw is None:
        logger.warning("Fetch failed — skipping this cycle.")
        return

    # ── FIRST RUN: just snapshot everything, notify nothing ──────
    if IS_FIRST_RUN:
        logger.info(
            f"First run detected. Snapshotting {len(jobs_raw)} existing jobs "
            f"so we don't spam you with old listings."
        )
        bulk_mark_seen(jobs_raw)
        IS_FIRST_RUN = False

        # Send yourself a startup confirmation on Telegram
        from notifier import send_telegram
        send_telegram({
            "id":        "STARTUP",
            "title":     "Placement Monitor is LIVE ✅",
            "company":   "IITB Placement Cell",
            "eligible":  True,
            "cpi":       0,
            "tags":      ["monitoring"],
            "opens_at":  "Now",
            "closes_at": "Never (until you stop it)",
            "url":       "https://campus.placements.iitb.ac.in/applicant/jobs",
        })
        logger.info("Startup notification sent. Now monitoring for NEW jobs...")
        return

    # ── SUBSEQUENT RUNS: check for genuinely new job IDs ─────────
    new_count = 0
    jobs = [extract_job_info(j) for j in jobs_raw]

    for job in jobs:
        if is_new_job(job["id"]):
            logger.info(f"NEW JOB: [{job['id']}] {job['title']} @ {job['company']}")
            notify(job)
            mark_as_seen(job["id"], job["title"], job["company"], job["eligible"])
            new_count += 1

    if new_count == 0:
        logger.info(
            f"No new jobs. "
            f"Total tracked so far: {len(get_seen_job_ids())} jobs."
        )
    else:
        logger.info(f"Done. Sent {new_count} new notification(s).")

    logger.info("========== Check complete ==========\n")


def main():
    init_db()
    logger.info(f"Agent starting. Interval: every {CHECK_INTERVAL_MINUTES} minutes.")

    run_check()  # Run immediately on startup

    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(run_check)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
