# RocksDB (LSM-Tree) Benchmark — Composite Key Order

Script đối xứng với `run_full_benchmark.py` (PostgreSQL / B-Tree).

## Cài đặt

```bash
pip install -r requirements.txt
# hoặc
pip install rocksdict numpy
```

**Không cần Docker container RocksDB.**  
`rocksdict` nhúng engine RocksDB trong process Python (file DB nằm thư mục local).

## Chạy

```bash
# Mặc định: 200k users, 1M orders, 2M activities
python run_rocksdb_benchmark.py

# Máy yếu — giảm dữ liệu
NUM_USERS=50000 NUM_ORDERS=200000 NUM_ACTIVITIES=500000 \
WARMUP_RUNS=50 MEASURE_RUNS=300 \
python run_rocksdb_benchmark.py

# Chạy lại không seed lại (nếu đã có data)
REUSE_EXISTING=1 python run_rocksdb_benchmark.py
```

## Kết quả

```
benchmark_results_rocksdb/
  orders_results.csv
  users_results.csv
  user_activities_results.csv
  all_results_summary.csv
  plans/*.json
```

Cột quan trọng: `p50`, `p95`, `p99`, `index_def` (thứ tự cột), `query_id`, `plan_node`.

## So với PostgreSQL trong báo cáo

| Tiêu chí       | PostgreSQL script      | RocksDB script                          |
| -------------- | ---------------------- | --------------------------------------- |
| Cấu trúc index | Composite Index B-Tree | Composite **key encoding** (byte order) |
| Đổi thứ tự cột | `CREATE INDEX (a,b,c)` | Mã hóa key `(a\|b\|c\|id)`              |
| Planner        | Cost-based, EXPLAIN    | Không có — prefix/range thủ công        |
| Chỉ số         | p50/p95/p99            | p50/p95/p99 (cùng công thức)            |
| Container      | Cần Postgres           | **Không cần**                           |

## Lưu ý khoa học (nên viết trong luận văn)

1. Đây là so sánh **công bằng về ý tưởng** (leftmost prefix / column order → tail latency), không phải so sánh SQL engine 1:1.
2. RocksDB không có `INCLUDE` covering index kiểu Postgres; value luôn đi kèm key.
3. Nên nêu rõ quy mô dữ liệu (`NUM_*`) và cấu hình Options (write buffer, compression) khi báo cáo.

cd rocksdb_bench
docker compose run --rm bench
