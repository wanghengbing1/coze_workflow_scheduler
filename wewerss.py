"""
Optimize Coze workflow runner: daily schedule (configurable), retry until success, Zeabur-ready.
"""

import os
import time
import logging
from datetime import datetime, timedelta
import pytz
import random
import signal
from threading import Event

try:
    from cozepy import Coze, TokenAuth, COZE_CN_BASE_URL
except Exception as e:
    raise RuntimeError("Failed to import cozepy. Please ensure requirements are installed.") from e

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s"
)

COZE_API_TOKEN = os.getenv("COZE_API_TOKEN")
WORKFLOW_ID = os.getenv("WORKFLOW_ID", "7569877408963231763")
SCHEDULE_TIME = os.getenv("SCHEDULE_TIME", "21:00")  # HH:MM
TIMEZONE_NAME = os.getenv("TIMEZONE", "Asia/Shanghai")
INITIAL_RETRY_DELAY = int(os.getenv("INITIAL_RETRY_DELAY", "5"))
MAX_BACKOFF = int(os.getenv("MAX_BACKOFF", "300"))
COZE_API_BASE_URL = os.getenv("COZE_API_BASE_URL", "")
COZE_REGION = os.getenv("COZE_REGION", "").lower()  # "cn" to use coze.cn

# Retry/backoff tuning
JITTER_MAX_SECONDS = int(os.getenv("JITTER_MAX_SECONDS", "3"))  # add up to N seconds jitter
SLEEP_CHUNK_SECONDS = int(os.getenv("SLEEP_CHUNK_SECONDS", "5"))  # countdown sleep chunk
STOP_ON_SHUTDOWN = os.getenv("STOP_ON_SHUTDOWN", "true").lower() == "true"  # break loops on SIGTERM

if not COZE_API_TOKEN:
    logging.error("Missing COZE_API_TOKEN environment variable.")
    raise SystemExit(1)

# Configure base_url: prefer explicit URL, else use CN when region=cn, else default (api.coze.com)
base_url = None
if COZE_API_BASE_URL:
    base_url = COZE_API_BASE_URL
elif COZE_REGION == "cn":
    base_url = COZE_CN_BASE_URL
else:
    base_url = None  # Use cozepy default api.coze.com

# Ensure base_url has protocol prefix
if base_url and not base_url.startswith(("http://", "https://")):
    base_url = "https://" + base_url

# Initialize client
coze = Coze(auth=TokenAuth(token=COZE_API_TOKEN), base_url=base_url)

# Global shutdown event to gracefully stop loops (SIGTERM/SIGINT)
shutdown_event = Event()

def _handle_signal(signum, frame):
    logging.info("Received signal %s, initiating shutdown...", signum)
    shutdown_event.set()

# Register signal handlers for graceful shutdown (Zeabur sends SIGTERM on stop/redeploy)
signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)

def _parse_time_str(time_str: str):
    """Return hour, minute from 'HH:MM' string."""
    try:
        parts = time_str.strip().split(":")
        if len(parts) != 2:
            raise ValueError("Invalid time format")
        hour = int(parts[0])
        minute = int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Hour/minute out of range")
        return hour, minute
    except Exception as e:
        logging.error("Failed to parse SCHEDULE_TIME '%s': %s", time_str, e)
        raise

def _next_run_datetime(now: datetime, tz: pytz.BaseTzInfo, time_str: str) -> datetime:
    """Compute next run datetime in given timezone based on 'HH:MM'."""
    hour, minute = _parse_time_str(time_str)
    candidate = tz.localize(datetime(now.year, now.month, now.day, hour, minute))
    if candidate <= now:
        candidate = candidate + timedelta(days=1)
    return candidate

def _sleep_until(target_dt: datetime, tz: pytz.BaseTzInfo):
    """Sleep until target datetime, logging countdown. Interruptible by signals."""
    while True:
        now = datetime.now(tz)
        remaining = (target_dt - now).total_seconds()
        if remaining <= 0 or shutdown_event.is_set():
            break
        # Log roughly every minute
        if remaining % 60 < 1:
            logging.info("Time until next run: %.0f seconds", remaining)
        chunk = max(0.5, min(SLEEP_CHUNK_SECONDS, remaining))
        # Sleep for a chunk or exit early if shutdown requested
        if shutdown_event.wait(timeout=chunk):
            break

def _run_once() -> bool:
    """Trigger the workflow once; return True if success."""
    try:
        result = coze.workflows.runs.create(
            workflow_id=WORKFLOW_ID,
            parameters={},
            bot_id=None,
            conversation_id=None,
            additional_messages=None,
            interrupt_enabled=False
        )
        logging.info("Workflow run success: %s", getattr(result, "data", result))
        return True
    except Exception as e:
        logging.warning("Workflow run failed: %s", e, exc_info=True)
        return False

def _retry_until_success(initial_delay: int = INITIAL_RETRY_DELAY, max_backoff: int = MAX_BACKOFF):
    """Keep retrying with exponential backoff and optional jitter until success or shutdown."""
    delay = max(1, initial_delay)
    while not shutdown_event.is_set():
        ok = _run_once()
        if ok:
            logging.info("Workflow executed successfully.")
            return
        # Add jitter to avoid thundering herd
        jitter = random.uniform(0, JITTER_MAX_SECONDS) if JITTER_MAX_SECONDS > 0 else 0.0
        sleep_sec = delay + jitter
        logging.warning("Retrying in %.1f seconds (base=%ds, jitter=%.1fs)...", sleep_sec, delay, jitter)
        # Wait with ability to interrupt on shutdown
        if shutdown_event.wait(timeout=sleep_sec):
            break
        delay = min(delay * 2, max_backoff)
    logging.info("Retry loop exited due to shutdown signal.")

def main():
    tz = pytz.timezone(TIMEZONE_NAME)
    while not shutdown_event.is_set():
        now = datetime.now(tz)
        next_dt = _next_run_datetime(now, tz, SCHEDULE_TIME)
        logging.info("Next scheduled run at %s (%s)", next_dt.isoformat(), TIMEZONE_NAME)
        _sleep_until(next_dt, tz)
        if shutdown_event.is_set() and STOP_ON_SHUTDOWN:
            break
        _retry_until_success()

if __name__ == "__main__":
    # 注册信号处理
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Shutting down scheduler.")
    except Exception as e:
        logging.exception("Fatal error in scheduler: %s", e)
        raise