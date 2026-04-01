import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        value = default
    return max(value, minimum)

TELEGRAM_BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID    = os.getenv("TELEGRAM_CHAT_ID", "")
BEARER_TOKEN        = os.getenv("BEARER_TOKEN", "")
CHECK_INTERVAL_MINUTES = _env_int("CHECK_INTERVAL_MINUTES", 30, minimum=1)
API_TIMEOUT_SECONDS = _env_int("API_TIMEOUT_SECONDS", 20, minimum=5)
TELEGRAM_TIMEOUT_SECONDS = _env_int("TELEGRAM_TIMEOUT_SECONDS", 10, minimum=5)
JOB_DESCRIPTION_MAX_LEN = _env_int("JOB_DESCRIPTION_MAX_LEN", 900, minimum=200)

ELIGIBLE_ONLY       = _env_bool("ELIGIBLE_ONLY", False)
FETCH_DETAIL_FOR_NEW_JOBS = _env_bool("FETCH_DETAIL_FOR_NEW_JOBS", True)
SNAPSHOT_ON_STARTUP = _env_bool("SNAPSHOT_ON_STARTUP", True)

DB_PATH             = os.getenv("DB_PATH", "seen_jobs.db").strip() or "seen_jobs.db"

SERVICE = os.getenv("SERVICE", "internship").strip().lower() or "internship"
YEAR = _env_int("YEAR", 2025, minimum=2000)
SEASON = os.getenv("SEASON", "autumn").strip().lower() or "autumn"


def validate_runtime_config() -> List[str]:
    errors: List[str] = []

    if not BEARER_TOKEN:
        errors.append("BEARER_TOKEN is missing in .env")

    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is missing in .env")

    if not TELEGRAM_CHAT_ID:
        errors.append("TELEGRAM_CHAT_ID is missing in .env")

    if SERVICE not in {"internship", "placement"}:
        errors.append("SERVICE must be either 'internship' or 'placement'")

    return errors