"""All settings come from environment variables so the same code runs on
your laptop, in Docker and on a server."""
import os
import shutil
from pathlib import Path


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


DATA_DIR = Path(os.environ.get("DATA_DIR", "./data")).resolve()
JOBS_DIR = DATA_DIR / "jobs"
FFMPEG = os.environ.get("FFMPEG_PATH") or shutil.which("ffmpeg") or "ffmpeg"

# Comma separated list of websites allowed to call the API,
# e.g. "https://video.rnclasses.in,http://localhost:3000"
CORS_ORIGINS = [o.strip() for o in os.environ.get(
    "CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

VOICE = os.environ.get("TTS_VOICE", "en-US-ChristopherNeural")

# Optional: Claude is used to understand typed/uploaded problems and to read photos.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "claude-haiku-5-5")

# Capacity / abuse protection
MAX_WORKERS = _int("MAX_WORKERS", 2)            # videos rendered at the same time
MAX_QUEUE = _int("MAX_QUEUE", 20)               # waiting jobs before we say "busy"
RATE_LIMIT_PER_HOUR = _int("RATE_LIMIT_PER_HOUR", 20)   # per IP address
JOB_TTL_MINUTES = _int("JOB_TTL_MINUTES", 120)  # videos are deleted after this
MAX_UPLOAD_MB = _int("MAX_UPLOAD_MB", 8)
MAX_TEXT_CHARS = _int("MAX_TEXT_CHARS", 600)
RENDER_TIMEOUT_SEC = _int("RENDER_TIMEOUT_SEC", 420)
