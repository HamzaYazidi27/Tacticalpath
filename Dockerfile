# Self-contained autoedit image: docker build -t autoedit .
# docker run --rm -v "$PWD/work:/work" -e PEXELS_API_KEY autoedit /work/video.mp4 --out /work/out
# docker run --rm -v "$PWD/work:/work" -e PEXELS_API_KEY autoedit --watch /work/inbox --out /work/outbox
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"
COPY autoedit ./autoedit
COPY templates ./templates
COPY tools ./tools
COPY fonts ./fonts
ENTRYPOINT ["python", "-m", "autoedit"]
