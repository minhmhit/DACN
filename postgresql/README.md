# PostgreSQL (B-Tree) Benchmark — Composite Index Order

Script đo **p50 / p95 / p99** và **Execution Plan** khi đổi thứ tự cột trong Composite Index.

## Cần có trước khi chạy

1. PostgreSQL đang chạy (Docker hoặc local).
2. Database + 3 bảng `orders`, `users`, `user_activities` đã có **dữ liệu**.

Ví dụ với stack Docker indexing-lab:

```bash
docker compose up -d postgres
# đợi healthy, init SQL đã seed
```

## Cài đặt

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Chạy

```bash
export PGHOST=localhost
export PGPORT=5432
export PGUSER=research
export PGPASSWORD=research
export PGDATABASE=indexing_research

# Khớp số user trong DB (seed Docker = 20000; data lớn thì tăng)
export MAX_USER_ID=20000

python run_postgres_benchmark.py
```

Máy yếu / chạy thử nhanh:

```bash
WARMUP_RUNS=30 MEASURE_RUNS=100 MAX_USER_ID=20000 python run_postgres_benchmark.py
```

Tắt `CONCURRENTLY` (DDL nhanh hơn trên DB riêng, không share với app khác):

```bash
USE_CONCURRENTLY=0 python run_postgres_benchmark.py
```

Tái lập ngẫu nhiên:

```bash
RANDOM_SEED=42 python run_postgres_benchmark.py
```

## Kết quả

```
benchmark_results/
  orders_results.csv
  users_results.csv
  user_activities_results.csv
  all_results_summary.csv
  plans/
    orders_idx_orders_uid_time_stt_OQ1.json
    ...
```

Cột chính trong CSV: `index_def`, `query_id`, `p50`, `p95`, `p99`, `plan_node`, `plan_cost`.

## Phương án Index

**orders:** O0 baseline → O1 `(user_id, created_at, status)` → … → O5 covering `INCLUDE (status)`  
**users:** U0 → U5 (city / district / age_group)  
**user_activities:** A0 → A5 (user_id / event_type / event_time)

## Lưu ý khi đưa vào báo cáo

1. Ghi rõ phiên bản Postgres, RAM, SSD/HDD, `MAX_USER_ID`, số row từng bảng.
2. `plan_node` lấy từ `EXPLAIN (ANALYZE, BUFFERS)` — so sánh Index Scan / Bitmap / Seq Scan giữa các thứ tự cột.
3. p99 nhạy với cache: lần chạy đầu sau tạo index có thể cao hơn; script đã warm-up nhưng không drop OS cache.
4. Seed Docker (20k/80k/120k) chỉ để **smoke test**. Thí nghiệm chính thức nên dùng data lớn hơn (triệu–chục triệu dòng) và chỉnh `MAX_USER_ID` cho khớp.

## Troubleshooting

| Lỗi                                                               | Nguyên nhân / cách xử lý                                                        |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `password authentication failed`                                  | Sai `PGPASSWORD` / user                                                         |
| `relation "orders" does not exist`                                | Chưa chạy schema init                                                           |
| `CREATE INDEX CONCURRENTLY cannot run inside a transaction block` | Dùng đúng file này (đã autocommit); không bọc script trong transaction ngoài    |
| `INCLUDE` syntax error                                            | Cần PostgreSQL ≥ 11                                                             |
| p99 gần bằng nhau mọi index                                       | Data quá nhỏ hoặc query gần như luôn 0 row — tăng data + kiểm tra `MAX_USER_ID` |

cd postgres_bench
docker compose up -d

# đợi healthy

export PGHOST=localhost PGPORT=5432
export PGUSER=research PGPASSWORD=research
export PGDATABASE=indexing_research MAX_USER_ID=20000

python run_postgres_benchmark.py
