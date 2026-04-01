import logging
import schedule
import time
from config import (
    CHECK_INTERVAL_SECONDS,
    RUN_LOOP_SLEEP_SECONDS,
    FETCH_DETAIL_FOR_NEW_JOBS,
    SNAPSHOT_ON_STARTUP,
    SERVICE,
    YEAR,
    SEASON,
    validate_runtime_config,
)
from state import init_db, mark_as_seen, bulk_mark_seen, get_seen_job_ids
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

    # ── FIRST RUN: optionally snapshot everything to avoid historical spam ──
    if IS_FIRST_RUN and SNAPSHOT_ON_STARTUP:
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

    if IS_FIRST_RUN and not SNAPSHOT_ON_STARTUP:
        logger.info(
            "First run detected with SNAPSHOT_ON_STARTUP=false. "
            "Current jobs will be treated as new and notified if unseen."
        )
        IS_FIRST_RUN = False

    # ── SUBSEQUENT RUNS: check for genuinely new job IDs ─────────
    new_count = 0
    seen_ids = get_seen_job_ids()

    unseen_jobs_raw = []
    for raw_job in jobs_raw:
        job_id = raw_job.get("id")
        if job_id is None:
            continue
        if job_id not in seen_ids:
            unseen_jobs_raw.append(raw_job)

    if unseen_jobs_raw:
        logger.info(f"Detected {len(unseen_jobs_raw)} unseen job(s) in this cycle.")

    for raw_job in unseen_jobs_raw:
        job_id = raw_job.get("id")
        try:
            job = extract_job_info(
                raw_job,
                fetch_full_description=FETCH_DETAIL_FOR_NEW_JOBS,
            )
            logger.info(
                f"NEW JOB: [{job['id']}] {job['title']} @ {job['company']}"
            )
            sent = notify(job)
            if sent:
                mark_as_seen(
                    job["id"],
                    job["title"],
                    job["company"],
                    job["eligible"],
                )
                seen_ids.add(job["id"])
                new_count += 1
            else:
                logger.warning(
                    f"Notification failed for job [{job['id']}]. "
                    "Will retry in next cycle."
                )
        except Exception:
            logger.exception(f"Failed processing job id={job_id}")

    if new_count == 0:
        logger.info(
            f"No new jobs. "
            f"Total tracked so far: {len(seen_ids)} jobs."
        )
    else:
        logger.info(f"Done. Sent {new_count} new notification(s).")

    logger.info("========== Check complete ==========\n")


def main():
    config_errors = validate_runtime_config()
    if config_errors:
        for err in config_errors:
            logger.error(f"Config error: {err}")
        raise SystemExit(1)

    init_db()
    logger.info(
        f"Agent starting. Interval: every {CHECK_INTERVAL_SECONDS} seconds. "
        f"service={SERVICE}, year={YEAR}, season={SEASON}."
    )

    run_check()  # Run immediately on startup

    schedule.every(CHECK_INTERVAL_SECONDS).seconds.do(run_check)

    while True:
        schedule.run_pending()
        time.sleep(RUN_LOOP_SLEEP_SECONDS)


if __name__ == "__main__":
    main()
