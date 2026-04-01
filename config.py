import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID    = os.getenv("TELEGRAM_CHAT_ID", "")
BEARER_TOKEN        = os.getenv("BEARER_TOKEN", "")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "30"))
ELIGIBLE_ONLY       = os.getenv("ELIGIBLE_ONLY", "false").lower() == "true"
DB_PATH             = "seen_jobs.db"

YEAR   = 2025
SEASON = "autumn"