# RN Classes Video Studio

Type a maths problem (or upload a photo/PDF) and get a narrated, step-by-step video.

```
web/      Next.js website (deploy on Vercel)
worker/   FastAPI video server (deploy with Docker on a VPS)
deploy/   docker-compose + Caddy (automatic HTTPS) + .env.example
```

## What it can do
- **Equations**: linear (x on both sides, brackets, fractions), quadratics (factorising, formula, repeated and complex roots), higher-degree polynomials, pairs of linear equations (elimination). Sympy does the maths, so answers are always right.
- **Speed / distance / time** word problems (works free, offline).
- **Ready-made animated lessons**: trigonometry balloon, concave/convex mirror, reflection, covalent bonds.
- **Photos / PDFs**: read with Claude vision (if a key is set) or Tesseract.
- Free AI-free mode works out of the box. Add `ANTHROPIC_API_KEY` to also understand free-form word problems and handwriting.

## Run on your own computer
Needs Python 3.11+, ffmpeg and Node 20+.
```powershell
# terminal 1 - video server
cd worker
python -m venv .venv ; .\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000

# terminal 2 - website
cd web
npm install
npm run dev          # http://localhost:3000
```
Windows: install ffmpeg (`winget install ffmpeg`) so `ffmpeg` is on PATH, or set `FFMPEG_PATH`.
Photo reading without an AI key needs Tesseract installed.

## Put it online (recommended setup)
1. **Server**: any Ubuntu VPS with 2 vCPU / 2-4 GB RAM (Hetzner, DigitalOcean, AWS Lightsail...).
   Install Docker: `curl -fsSL https://get.docker.com | sh`
2. **DNS**: create an A-record `api.yourdomain.com` -> your server IP.
3. Copy this project to the server, then:
   ```bash
   cd deploy
   cp .env.example .env && nano .env     # set API_DOMAIN, CORS_ORIGINS, optional ANTHROPIC_API_KEY
   docker compose up -d --build
   curl https://api.yourdomain.com/health     # -> {"ok":true}
   ```
4. **Website on Vercel**: import the `web` folder, add the environment variable
   `NEXT_PUBLIC_API_URL=https://api.yourdomain.com`, deploy. Put the Vercel site address in `CORS_ORIGINS`
   and run `docker compose up -d` again.

## Safety and capacity (already built in)
- Every request gets its own job id and folder; videos are deleted after `JOB_TTL_MINUTES`.
- Per-IP rate limit (`RATE_LIMIT_PER_HOUR`), a waiting-line limit (`MAX_QUEUE`) and `MAX_WORKERS` videos at once.
- CORS only allows your website. Only Caddy can reach the API container.
- Equation input is whitelisted and size-limited (no code execution, no giant-power attacks).
- Keep **one** API process (job status is in memory). Handle more students by raising `MAX_WORKERS` / a bigger server.

## Tests
```bash
cd worker && pip install pytest && pytest -q
```

## Adding a new topic
Write a function that returns a list of `Scene(lines=[...], voice="...")` (see `app/solver.py`), route to it in
`app/jobs.py`. The engine in `app/engine.py` does the pictures, voice and video.
The old scripts in `app/legacy/` still work; move them onto the engine one at a time.

## Known limits / next steps
- Ready-made lessons are fixed scenes (same numbers every time) and take 1-2 minutes.
- Slides are still images + voice (no animation yet); LaTeX-style fractions and Manim animation are the next upgrade.
- Job state is in memory: a server restart loses videos in progress. Use Redis + a worker queue if you grow.
- Docker files were written but not build-tested in my environment; run step 3 once and tell me if anything fails.
