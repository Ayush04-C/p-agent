# p-agent

`p-agent` is a Python monitoring agent for the IIT Bombay placement portal that detects newly listed jobs and sends Telegram alerts.

## Features

- Polls IITB placement API at a configurable interval
- Tracks seen jobs in SQLite to avoid duplicate alerts
- Optional startup snapshot to suppress historical-job spam
- Fetches detailed job description for new jobs
- Sends formatted Telegram notifications with eligibility, CPI, tags, and timings
- Retries API and Telegram requests on transient failures

## Project Structure

- `/home/runner/work/p-agent/p-agent/main.py` – scheduler and monitoring loop
- `/home/runner/work/p-agent/p-agent/scraper.py` – portal API client + job parsing
- `/home/runner/work/p-agent/p-agent/notifier.py` – Telegram message formatting/sending
- `/home/runner/work/p-agent/p-agent/state.py` – SQLite seen-jobs state store
- `/home/runner/work/p-agent/p-agent/config.py` – environment-driven runtime config
- `/home/runner/work/p-agent/p-agent/requirements.txt` – Python dependencies

## Requirements

- Python 3.9+ (recommended)
- Valid IITB placement portal bearer token
- Telegram bot token + chat ID

## Installation

```bash
cd /home/runner/work/p-agent/p-agent
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in `/home/runner/work/p-agent/p-agent`:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
BEARER_TOKEN=your_iitb_portal_bearer_token

# Optional tuning
SERVICE=internship                 # internship | placement
YEAR=2025
SEASON=autumn
ELIGIBLE_ONLY=false
SNAPSHOT_ON_STARTUP=true
FETCH_DETAIL_FOR_NEW_JOBS=true
CHECK_INTERVAL_SECONDS=60
RUN_LOOP_SLEEP_SECONDS=1
API_TIMEOUT_SECONDS=20
DETAIL_FETCH_TIMEOUT_SECONDS=6
TELEGRAM_TIMEOUT_SECONDS=10
JOB_DESCRIPTION_MAX_LEN=900
DB_PATH=seen_jobs.db
```

### Required Variables

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `BEARER_TOKEN`

If any required value is missing, the agent exits with a config error.

## Run

```bash
cd /home/runner/work/p-agent/p-agent
python main.py
```

Behavior:
- Runs one check immediately at startup
- Then runs on a fixed schedule (`CHECK_INTERVAL_SECONDS`)
- Writes logs to console and `agent.log`

## First-Run Behavior

- `SNAPSHOT_ON_STARTUP=true` (default): current jobs are marked as seen; only future jobs notify.
- `SNAPSHOT_ON_STARTUP=false`: existing unseen jobs can trigger notifications on first cycle.

## Data Storage

Seen jobs are stored in SQLite (`DB_PATH`, default `seen_jobs.db`) in table `seen_jobs`.

## Notes

- No test suite or lint configuration is currently present in this repository.
- Keep your bearer token fresh; expired tokens produce 401/403 errors.
