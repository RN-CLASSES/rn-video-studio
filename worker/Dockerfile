FROM python:3.12-slim

# ffmpeg = video, fonts-dejavu = maths symbols, tesseract = reading photos
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core tesseract-ocr \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
RUN useradd -m rn && mkdir -p /data && chown rn /data
USER rn
ENV DATA_DIR=/data PYTHONUNBUFFERED=1

EXPOSE 8000
# ONE process on purpose: job status lives in memory. Scale with MAX_WORKERS, not --workers.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/health')"
