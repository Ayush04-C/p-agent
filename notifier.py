import requests
import logging
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)


def send_telegram(job: dict):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Telegram credentials missing. Check your .env file.")
        return

    eligible_line = (
        "✅ *YOU ARE ELIGIBLE — Apply Now!*"
        if job["eligible"]
        else "ℹ️ _You are not eligible for this one_"
    )

    cpi_line = (
        f"📊 Min CPI: `{job['cpi']}`"
        if job["cpi"] > 0
        else "📊 No CPI cutoff"
    )

    tags_line = ", ".join(job["tags"]) if job["tags"] else "N/A"

    message = (
        f"🚨 *NEW INTERNSHIP ON IITB PORTAL* 🚨\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏢 *Company:* {job['company']}\n"
        f"📌 *Role:* {job['title']}\n\n"
        f"{eligible_line}\n"
        f"{cpi_line}\n"
        f"🏷️ *Type:* {tags_line}\n\n"
        f"📅 *Opens:* {job['opens_at']}\n"
        f"⏰ *Closes:* {job['closes_at']}\n\n"
        f"🔗 [Open Placement Portal]({job['url']})\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"_Job ID: {job['id']}_"
    )

    url     = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":                  TELEGRAM_CHAT_ID,
        "text":                     message,
        "parse_mode":               "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        logger.info(f"Telegram sent: {job['title']} @ {job['company']}")
    except requests.RequestException as e:
        logger.error(f"Telegram send failed: {e}")


def notify(job: dict):
    send_telegram(job)