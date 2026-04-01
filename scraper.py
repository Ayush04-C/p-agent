import requests
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone
from config import BEARER_TOKEN, YEAR, SEASON, ELIGIBLE_ONLY

logger = logging.getLogger(__name__)

API_URL    = "https://campus.placements.iitb.ac.in/api/v1/job"
PORTAL_URL = "https://campus.placements.iitb.ac.in/applicant/jobs"


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "Accept": "application/json, text/plain, */*",
        "Referer": PORTAL_URL,
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/18.5 Mobile/15E148 Safari/604.1"
        ),
    }


def _fmt_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        # Convert to IST (UTC+5:30)
        from datetime import timedelta
        ist = dt + timedelta(hours=5, minutes=30)
        return ist.strftime("%d %b %Y, %I:%M %p IST")
    except Exception:
        return iso


def fetch_jobs() -> Optional[List[Dict]]:
    params = {
        "sendEligibility": "true",
        "service": "internship",
        "year": YEAR,
        "season": SEASON,
    }

    try:
        resp = requests.get(API_URL, headers=_headers(), params=params, timeout=20)

        if resp.status_code == 401:
            logger.error("TOKEN EXPIRED — paste a fresh Bearer token into .env")
            return None
        if resp.status_code == 403:
            logger.error("FORBIDDEN — session may have been invalidated")
            return None

        resp.raise_for_status()
        jobs = resp.json()
        logger.info(f"Fetched {len(jobs)} internship listings from API.")

        if ELIGIBLE_ONLY:
            jobs = [j for j in jobs if j.get("eligible") is True]
            logger.info(f"After eligible filter: {len(jobs)} jobs remain.")

        return jobs

    except requests.exceptions.ConnectionError:
        logger.error("Cannot reach portal. Check your internet / VPN.")
        return None
    except requests.exceptions.Timeout:
        logger.error("Request timed out.")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching jobs: {e}")
        return None


def extract_job_info(job: Dict) -> Dict:
    company = job.get("company", {})
    tags    = [t.get("name", "") for t in job.get("tags", [])]
    cpi     = job.get("cpiCutoff", 0)

    return {
        "id":        job.get("id"),
        "title":     job.get("title", "Unknown Role").strip(),
        "company":   company.get("name", "Unknown Company").strip(),
        "eligible":  job.get("eligible", False),
        "cpi":       cpi,
        "tags":      tags,
        "opens_at":  _fmt_time(job.get("opensAt", "")),
        "closes_at": _fmt_time(job.get("closesAt", "")),
        "url":       f"https://campus.placements.iitb.ac.in/applicant/jobs",
    }