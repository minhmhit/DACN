FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    librocksdb-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    rocksdict \
    numpy \
    pandas \
    matplotlib \
    seaborn \
    hdrhistogram \
    "psycopg[binary]"

WORKDIR /app
