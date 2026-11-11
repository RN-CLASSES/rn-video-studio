"""Background jobs: every request gets its own id and its own folder, so two
students can never overwrite each other's video."""
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from . import config
from .engine import build_video
from .router import LESSONS, classify
from .solver import ProblemError, solve_equation_text, solve_speed

LEGACY_DIR = Path(__file__).parent / "legacy"
WORKER_ROOT = Path(__file__).resolve().parent.parent


class Busy(Exception):
    pass


@dataclass
class Job:
    id: str
    status: str = "queued"          # queued | running | done | error
    progress: int = 0
    message: str = "Waiting in line"
    error: Optional[str] = None
    title: str = ""
    created: float = field(default_factory=time.time)
    video_path: Optional[str] = None

    def public(self) -> dict:
        return {"id": self.id, "status": self.status, "progress": self.progress,
                "message": self.message, "error": self.error, "title": self.title,
                "video_url": f"/api/videos/{self.id}.mp4" if self.status == "done" else None}


class JobManager:
    def __init__(self):
        config.JOBS_DIR.mkdir(parents=True, exist_ok=True)
        self.jobs: Dict[str, Job] = {}
        self.lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=config.MAX_WORKERS)
        threading.Thread(target=self._janitor, daemon=True).start()

    # ------------------------------------------------------------- public --
    def submit(self, text: str) -> Job:
        with self.lock:
            waiting = sum(1 for j in self.jobs.values() if j.status in ("queued", "running"))
            if waiting >= config.MAX_WORKERS + config.MAX_QUEUE:
                raise Busy()
            job = Job(id=uuid.uuid4().hex)
            self.jobs[job.id] = job
        self.pool.submit(self._run, job, text)
        return job

    def get(self, job_id: str) -> Optional[Job]:
        return self.jobs.get(job_id)

    # ----------------------------------------------------------- internal --
    def _set(self, job: Job, **kw):
        for k, v in kw.items():
            setattr(job, k, v)

    def _run(self, job: Job, text: str):
        workdir = config.JOBS_DIR / job.id
        try:
            self._set(job, status="running", progress=2, message="Understanding the problem")
            spec = classify(text)
            out = str(workdir / "video.mp4")
            workdir.mkdir(parents=True, exist_ok=True)

            if spec["type"] == "lesson":
                self._run_lesson(job, spec["key"], workdir, out)
            else:
                if spec["type"] == "equation":
                    scenes = solve_equation_text(spec["text"])
                    title = "Solution"
                else:
                    scenes = solve_speed(spec["distance"], spec["time"], spec["speed"],
                                         spec["dist_unit"], spec["time_unit"])
                    title = "Speed, distance and time"
                self._set(job, title=title)
                build_video(scenes, out, str(workdir / "tmp"), title=title,
                            progress=lambda p, m: self._set(job, progress=p, message=m))
            shutil.rmtree(workdir / "tmp", ignore_errors=True)
            self._set(job, status="done", progress=100, message="Your video is ready", video_path=out)
        except ProblemError as e:
            self._fail(job, str(e), workdir)
        except Exception as e:                     # unexpected: log it, show a friendly message
            print(f"[job {job.id}] failed: {e!r}", file=sys.stderr, flush=True)
            self._fail(job, "Something went wrong while making the video. Please try again.", workdir)

    def _fail(self, job: Job, msg: str, workdir: Path):
        shutil.rmtree(workdir, ignore_errors=True)
        self._set(job, status="error", error=msg, message="Failed")

    def _run_lesson(self, job: Job, key: str, workdir: Path, out: str):
        script, produced, title = LESSONS[key]
        self._set(job, title=title, progress=10, message="Preparing the animation (this takes 1-2 minutes)")
        args = [sys.executable, str(LEGACY_DIR / script)]
        if script == "spherical_mirror.py":
            args += ["convex" if key == "mirror_convex" else "concave", "between_infinity_pole"]
        env = dict(os.environ, PYTHONPATH=str(WORKER_ROOT), PYTHONUNBUFFERED="1")
        r = subprocess.run(args, cwd=workdir, env=env, capture_output=True, text=True,
                           timeout=config.RENDER_TIMEOUT_SEC)
        src = workdir / produced
        if r.returncode != 0 or not src.exists():
            print(f"[job {job.id}] lesson {key} failed:\n{r.stderr[-800:]}", file=sys.stderr, flush=True)
            raise RuntimeError("lesson script failed")
        src.rename(out)
        shutil.rmtree(workdir / "temp_frames", ignore_errors=True)

    def _janitor(self):
        while True:
            time.sleep(300)
            cutoff = time.time() - config.JOB_TTL_MINUTES * 60
            with self.lock:
                old = [j.id for j in self.jobs.values() if j.created < cutoff and j.status in ("done", "error")]
                for jid in old:
                    del self.jobs[jid]
            for jid in old:
                shutil.rmtree(config.JOBS_DIR / jid, ignore_errors=True)
