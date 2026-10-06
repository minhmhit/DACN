FROM python:3.12-slim

WORKDIR /app

# rocksdict ship wheel; cần toolchain tối thiểu trên một số platform
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Script được mount lúc runtime; copy mặc định để image tự chạy được
COPY run_rocksdb_benchmark.py .

CMD ["python", "run_rocksdb_benchmark.py"]
