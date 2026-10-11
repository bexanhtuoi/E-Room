# EC2 scorer: FastAPI cham diem phat am + embedding (XLSR-only + Qwen3).
# Build tu backend/: docker build -f ec2/Dockerfile -t eroom-scorer:latest backend/
FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /tmp/log /opt/nltk_data /opt/hf_cache /app/log

RUN pip install uv

COPY ec2/pyproject.toml ec2/uv.lock ./

RUN uv sync --frozen --no-dev

COPY ec2/*.py ./
COPY app/ ./app/

ENV HF_HOME=/opt/hf_cache \
    NLTK_DATA=/opt/nltk_data \
    OMP_NUM_THREADS=4 \
    APP_ENV=development \
    SECRET_KEY=scorer-dummy \
    SCORER_BACKEND=local

# 1. Bake NLTK data + HF weights vao image (runtime khong tai gi them).
RUN uv run --frozen --no-dev python -c "import nltk; nltk.download('cmudict', download_dir='/opt/nltk_data')" && \
    uv run --frozen --no-dev python -c "from transformers import Wav2Vec2ForCTC, AutoFeatureExtractor; \
        Wav2Vec2ForCTC.from_pretrained('facebook/wav2vec2-xlsr-53-espeak-cv-ft'); \
        AutoFeatureExtractor.from_pretrained('facebook/wav2vec2-xlsr-53-espeak-cv-ft')" && \
    uv run --frozen --no-dev python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('Qwen/Qwen3-Embedding-0.6B')"

EXPOSE 8005

CMD ["uv", "run", "--frozen", "--no-dev", "python", "-m", "server"]
