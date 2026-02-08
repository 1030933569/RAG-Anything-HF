FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/data/.cache/huggingface \
    TRANSFORMERS_CACHE=/data/.cache/huggingface/transformers \
    WORKING_DIR=/data/rag_storage \
    OUTPUT_DIR=/data/output \
    PARSER=docling \
    PARSE_METHOD=auto

RUN useradd -m -u 1000 user

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-hf-docling.txt /app/requirements-hf-docling.txt
RUN pip install --upgrade pip && pip install -r /app/requirements-hf-docling.txt

COPY . /app

RUN mkdir -p /data/rag_storage /data/output /data/upload_tmp /data/.cache/huggingface \
    && chown -R user:user /data /app

USER user

ENV PATH="/home/user/.local/bin:${PATH}"

EXPOSE 7860

CMD ["python", "app.py"]
