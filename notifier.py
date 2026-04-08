import requests
import logging
from html import escape
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)
MAX_TELEGRAM_CHARS = 3900


def _build_session() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"POST"}),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    return session


HTTP = _build_session()


def _as_html_text(value: object) -> str:
    return escape(str(value), quote=False)


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def send_telegram(job: dict) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Telegram credentials missing. Check your .env file.")
        return False

    eligible = bool(job.get("eligible", False))
    cpi = job.get("cpi", 0)
    tags_line = ", ".join(job.get("tags", [])) if job.get("tags") else "N/A"
    stipend_value = job.get("stipend", "Not specified")

    company = _as_html_text(job.get("company", "Unknown Company"))
    title = _as_html_text(job.get("title", "Unknown Role"))
    tags = _as_html_text(tags_line)
    description = _truncate(
        _as_html_text(job.get("description", "Description not available.")),
        1400,
    )

    eligible_line = (
        "✅ <b>YOU ARE ELIGIBLE - Apply Now!</b>"
        if eligible
        else "ℹ️ <i>You are not eligible for this one</i>"
    )

    cpi_line = (
        f"📊 Min CPI: <code>{_as_html_text(cpi)}</code>"
        if cpi and cpi > 0
        else "📊 No CPI cutoff"
    )

    stipend_line = (
        f"💰 <b>Stipend:</b> <code>{_as_html_text(stipend_value)}</code>"
        if stipend_value and str(stipend_value).strip() and str(stipend_value).strip() != "Not specified"
        else "💰 <b>Stipend:</b> Not specified"
    )

    opens_at = _as_html_text(job.get("opens_at", "Unknown"))
    closes_at = _as_html_text(job.get("closes_at", "Unknown"))
    portal_url = job.get("url", "https://campus.placements.iitb.ac.in/applicant/jobs")
    job_id = _as_html_text(job.get("id", "N/A"))

    message = (
        f"🚨 <b>NEW INTERNSHIP ON IITB PORTAL</b> 🚨\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏢 <b>Company:</b> {company}\n"
        f"📌 <b>Role:</b> {title}\n\n"
        f"{eligible_line}\n"
        f"{cpi_line}\n"
        f"{stipend_line}\n"
        f"🏷️ <b>Type:</b> {tags}\n\n"
        f"📝 <b>Description:</b>\n{description}\n\n"
        f"📅 <b>Opens:</b> {opens_at}\n"
        f"⏰ <b>Closes:</b> {closes_at}\n\n"
        f"🔗 <a href=\"{portal_url}\">Open Placement Portal</a>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Job ID: {job_id}</i>"
    )

    if len(message) > MAX_TELEGRAM_CHARS:
        overflow = len(message) - MAX_TELEGRAM_CHARS
        description = _truncate(description, max(120, len(description) - overflow - 10))
        message = (
            f"🚨 <b>NEW INTERNSHIP ON IITB PORTAL</b> 🚨\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🏢 <b>Company:</b> {company}\n"
            f"📌 <b>Role:</b> {title}\n\n"
            f"{eligible_line}\n"
            f"{cpi_line}\n"
            f"{stipend_line}\n"
            f"🏷️ <b>Type:</b> {tags}\n\n"
            f"📝 <b>Description:</b>\n{description}\n\n"
            f"📅 <b>Opens:</b> {opens_at}\n"
            f"⏰ <b>Closes:</b> {closes_at}\n\n"
            f"🔗 <a href=\"{portal_url}\">Open Placement Portal</a>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Job ID: {job_id}</i>"
        )

    url     = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":                  TELEGRAM_CHAT_ID,
        "text":                     message,
        "parse_mode":               "HTML",
        "disable_web_page_preview": True,
    }

    try:
        r = HTTP.post(url, json=payload, timeout=TELEGRAM_TIMEOUT_SECONDS)
        r.raise_for_status()
        logger.info(f"Telegram sent: {job.get('title')} @ {job.get('company')}")
        return True
    except requests.RequestException as e:
        body = ""
        response = getattr(e, "response", None)
        if response is not None and getattr(response, "text", None):
            body = response.text[:300]
        logger.error(f"Telegram send failed: {e}. Response: {body}")
        return False


def notify(job: dict) -> bool:
    return send_telegram(job)