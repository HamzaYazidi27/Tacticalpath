# Self-contained autoedit image: docker build -t autoedit .
# docker run --rm -v "$PWD/work:/work" -e PEXELS_API_KEY autoedit /work/video.mp4 --out /work/out
# docker run --rm -v "$PWD/work:/work" -e PEXELS_API_KEY autoedit --watch /work/inbox --out /work/outbox
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg nodejs && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt requirements-vision.txt requirements-web.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-vision.txt -r requirements-web.txt \
 && python -c "from transformers import CLIPModel, CLIPProcessor as P; CLIPModel.from_pretrained('openai/clip-vit-base-patch32'); P.from_pretrained('openai/clip-vit-base-patch32')" \
 && python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"
COPY autoedit ./autoedit
COPY templates ./templates
COPY tools ./tools
COPY fonts ./fonts
COPY webui ./webui
# Web studio: docker run -p 8765:8765 -v "$PWD/work:/app/workspace" --entrypoint python autoedit -m webui --host 0.0.0.0 --no-browser
ENTRYPOINT ["python", "-m", "autoedit"]
