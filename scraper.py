import requests
import logging
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
from html import unescape
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import (
    BEARER_TOKEN,
    YEAR,
    SEASON,
    SERVICE,
    ELIGIBLE_ONLY,
    API_TIMEOUT_SECONDS,
    JOB_DESCRIPTION_MAX_LEN,
)

logger = logging.getLogger(__name__)

API_URL    = "https://campus.placements.iitb.ac.in/api/v1/job"
PORTAL_URL = "https://campus.placements.iitb.ac.in/applicant/jobs"
IST_TZ = timezone(timedelta(hours=5, minutes=30))


def _build_session() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


HTTP = _build_session()


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
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(IST_TZ).strftime("%d %b %Y, %I:%M %p IST")
    except Exception:
        return iso


def _clean_description(raw: str, max_len: int = JOB_DESCRIPTION_MAX_LEN) -> str:
    text = unescape(raw or "")
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</\s*p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    if not text:
        return "Description not available."

    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0].rstrip() + "..."

    return text


def _extract_description(job: Dict) -> str:
    possible_values = [
        job.get("jobDescription"),
        job.get("jobDetails"),
        job.get("additionalInfo"),
        job.get("additionalRequirements"),
        job.get("description"),
        job.get("details"),
        job.get("jd"),
    ]

    for value in possible_values:
        if isinstance(value, str) and value.strip():
            return _clean_description(value)

    for value in possible_values:
        if isinstance(value, dict):
            for key in ("text", "value", "html", "content"):
                nested = value.get(key)
                if isinstance(nested, str) and nested.strip():
                    return _clean_description(nested)

    for value in possible_values:
        if isinstance(value, list):
            parts = [v.strip() for v in value if isinstance(v, str) and v.strip()]
            if parts:
                return _clean_description("\n".join(parts))

    return "Description not available."


def fetch_job_details(job_id: int) -> Optional[Dict]:
    try:
        resp = HTTP.get(
            f"{API_URL}/{job_id}",
            headers=_headers(),
            timeout=API_TIMEOUT_SECONDS,
        )

        if resp.status_code in (401, 403):
            logger.error("Cannot fetch job details (401/403). Check token/session.")
            return None

        if resp.status_code == 404:
            logger.debug(f"Job details not found for job {job_id}")
            return None

        if resp.status_code >= 500:
            logger.warning(f"Detail API returned {resp.status_code} for job {job_id}")
            return None

        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else None
    except Exception as e:
        logger.debug(f"Could not fetch details for job {job_id}: {e}")
        return None


def fetch_jobs() -> Optional[List[Dict]]:
    params = {
        "sendEligibility": "true",
        "service": SERVICE,
        "year": YEAR,
        "season": SEASON,
    }

    try:
        resp = HTTP.get(
            API_URL,
            headers=_headers(),
            params=params,
            timeout=API_TIMEOUT_SECONDS,
        )

        if resp.status_code == 401:
            logger.error("TOKEN EXPIRED — paste a fresh Bearer token into .env")
            return None
        if resp.status_code == 403:
            logger.error("FORBIDDEN — session may have been invalidated")
            return None

        if resp.status_code >= 500:
            logger.error(f"Portal server error: HTTP {resp.status_code}")
            return None

        resp.raise_for_status()
        jobs = resp.json()
        if not isinstance(jobs, list):
            logger.error("Unexpected API response. Expected a list of jobs.")
            return None

        logger.info(f"Fetched {len(jobs)} {SERVICE} listings from API.")

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


def extract_job_info(job: Dict, fetch_full_description: bool = False) -> Dict:
    company = job.get("company", {})
    tags    = [t.get("name", "") for t in job.get("tags", [])]
    cpi     = job.get("cpiCutoff", 0)
    job_id  = job.get("id")
    description = _extract_description(job)

    if fetch_full_description and job_id:
        detail = fetch_job_details(job_id)
        if detail:
            detail_description = _extract_description(detail)
            if detail_description != "Description not available.":
                description = detail_description

    return {
        "id":        job_id,
        "title":     job.get("title", "Unknown Role").strip(),
        "company":   company.get("name", "Unknown Company").strip(),
        "eligible":  job.get("eligible", False),
        "cpi":       cpi,
        "tags":      tags,
        "description": description,
        "opens_at":  _fmt_time(job.get("opensAt", "")),
        "closes_at": _fmt_time(job.get("closesAt", "")),
        "url":       f"https://campus.placements.iitb.ac.in/applicant/jobs",
    }