FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV DEBIAN_FRONTEND=noninteractive
ENV HOME=/data
ENV XDG_CACHE_HOME=/data/cache
ENV HF_HOME=/data/cache/huggingface
ENV TRANSFORMERS_CACHE=/data/cache/huggingface
ENV HUGGINGFACE_HUB_CACHE=/data/cache/huggingface
ENV EASYOCR_HOME=/data/easyocr
ENV TMPDIR=/data/tmp

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxcb1 \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /data/cache /data/easyocr /data/tmp /app/logs \
    && chmod -R 777 /data \
    && chmod -R 777 /app/logs

COPY requirements.txt /app/requirements.txt
RUN pip install --root-user-action=ignore --no-cache-dir --upgrade pip \
    && pip install --root-user-action=ignore --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r /app/requirements.txt

COPY . /app

EXPOSE 8002

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002", "--log-level", "info"]
