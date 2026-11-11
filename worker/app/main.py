import re
import threading
import time
from collections import defaultdict, deque

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import config
from .jobs import Busy, JobManager
from .ocr import extract_text
from .router import LESSONS
from .solver import ProblemError

app = FastAPI(title="RN Video Studio", docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS,
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
manager = JobManager()

_hits = defaultdict(deque)
_hits_lock = threading.Lock()


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")      # set by Caddy/nginx on a real server
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")


def _rate_limit(request: Request):
    ip, now = _client_ip(request), time.time()
    with _hits_lock:
        q = _hits[ip]
        while q and q[0] < now - 3600:
            q.popleft()
        if len(q) >= config.RATE_LIMIT_PER_HOUR:
            raise HTTPException(429, "You have made many videos in the last hour. Please try again a little later.")
        q.append(now)


class TextRequest(BaseModel):
    text: str = Field(..., max_length=config.MAX_TEXT_CHARS * 2)


def _submit(text: str):
    try:
        return manager.submit(text).public()
    except Busy:
        raise HTTPException(503, "The studio is busy right now. Please try again in a minute.")


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/lessons")
def lessons():
    return [{"key": k, "title": v[2]} for k, v in LESSONS.items()]


@app.post("/api/jobs")
def create_job(req: TextRequest, request: Request):
    _rate_limit(request)
    return _submit(req.text)


@app.post("/api/jobs/upload")
async def create_job_from_file(request: Request, file: UploadFile = File(...)):
    _rate_limit(request)
    data = await file.read(config.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    try:
        text = extract_text(data, file.filename or "")
    except ProblemError as e:
        raise HTTPException(400, str(e))
    return _submit(text)


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = manager.get(job_id) if re.fullmatch(r"[0-9a-f]{32}", job_id) else None
    if not job:
        raise HTTPException(404, "Job not found (it may have expired).")
    return job.public()


@app.get("/api/videos/{job_id}.mp4")
def video(job_id: str):
    job = manager.get(job_id) if re.fullmatch(r"[0-9a-f]{32}", job_id) else None
    if not job or job.status != "done" or not job.video_path:
        raise HTTPException(404, "Video not found (it may have expired).")
    return FileResponse(job.video_path, media_type="video/mp4", filename="rn-solution.mp4")
