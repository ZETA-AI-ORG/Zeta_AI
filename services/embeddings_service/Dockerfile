FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/embeddings_service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/embeddings_service /app/services/embeddings_service

EXPOSE 8010

ENV EMBEDDINGS_MODEL_NAME=dangvantuan/sentence-camembert-large
ENV EMBEDDINGS_NORMALIZE=true

CMD ["uvicorn", "services.embeddings_service.app:app", "--host", "0.0.0.0", "--port", "8010"]
