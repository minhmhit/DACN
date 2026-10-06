#!/usr/bin/env python3
"""
Full Automation Benchmark — PostgreSQL (B-Tree)
Đề tài: Ảnh hưởng của thứ tự cột trong Composite Index đến Latency p95/p99

ĐÃ KIỂM TRA / SỬA so với bản trước:
1. CREATE INDEX CONCURRENTLY không chạy trong transaction → dùng autocommit
2. Cấu hình DB qua biến môi trường (không hard-code password trong code production)
3. Quote tên index an toàn
4. Tách rõ warm-up / measure; cố định seed random (tùy chọn) để tái lập
5. Kiểm tra bảng tồn tại trước khi chạy
6. Không dùng CONCURRENTLY khi không cần (flag USE_CONCURRENTLY)

Cài:
  pip install -r requirements.txt

Chạy (Postgres đã có schema + data):
  export PGHOST=localhost PGPORT=5432 PGUSER=research PGPASSWORD=research PGDATABASE=indexing_research
  python run_postgres_benchmark.py
"""

from __future__ import annotations

import csv
import json
import os
import random
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import psycopg2
import psycopg2.extensions
from psycopg2 import sql

# ====================== CẤU HÌNH ======================
DB_CONFIG = {
    "host": os.environ.get("PGHOST", "localhost"),
    "port": int(os.environ.get("PGPORT", "5432")),
    "dbname": os.environ.get("PGDATABASE", "indexing_research"),
    "user": os.environ.get("PGUSER", "research"),
    "password": os.environ.get("PGPASSWORD", "research"),
}

WARMUP_RUNS = int(os.environ.get("WARMUP_RUNS", "150"))
MEASURE_RUNS = int(os.environ.get("MEASURE_RUNS", "1200"))
# True: CREATE INDEX CONCURRENTLY (không block write lâu, bắt buộc autocommit)
USE_CONCURRENTLY = os.environ.get("USE_CONCURRENTLY", "1") == "1"
# Giới hạn user_id khi random param — phải ≤ số user thật trong DB
MAX_USER_ID = int(os.environ.get("MAX_USER_ID", "20000"))
RANDOM_SEED = os.environ.get("RANDOM_SEED")  # ví dụ "42" để tái lập

RESULT_DIR = Path(os.environ.get("RESULT_DIR", "benchmark_results"))
RESULT_DIR.mkdir(parents=True, exist_ok=True)
(RESULT_DIR / "plans").mkdir(parents=True, exist_ok=True)

if RANDOM_SEED is not None:
    random.seed(int(RANDOM_SEED))
    np.random.seed(int(RANDOM_SEED))
# ======================================================


@contextmanager
def get_conn(autocommit: bool = False):
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = autocommit
    try:
        yield conn
        if not autocommit:
            conn.commit()
    except Exception:
        if not autocommit:
            conn.rollback()
        raise
    finally:
        conn.close()


def check_prerequisites() -> None:
    """Fail sớm nếu DB/schema/data chưa sẵn sàng."""
    required_tables = ("orders", "users", "user_activities")
    with get_conn(autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            print(f"[ok] Connected: {cur.fetchone()[0][:60]}...")
            for t in required_tables:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = %s
                    """,
                    (t,),
                )
                if cur.fetchone()[0] == 0:
                    raise SystemExit(
                        f"[error] Bảng '{t}' chưa tồn tại.\n"
                        f"Hãy chạy schema + seed trước (docker init hoặc script generate_data)."
                    )
                cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(t)))
                n = cur.fetchone()[0]
                print(f"[ok] {t}: {n:,} rows")
                if n == 0:
                    print(f"[warn] Bảng '{t}' đang trống — latency vẫn đo được nhưng ít ý nghĩa.")


def drop_secondary_indexes(conn, table: str) -> None:
    """Xóa mọi index phụ (giữ PRIMARY KEY). Cần autocommit nếu trước đó có CONCURRENTLY."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = %s
              AND indexname NOT LIKE %s
              AND indexname NOT LIKE 'pg_%%'
            """,
            (table, f"%_pkey"),
        )
        indexes = [row[0] for row in cur.fetchall()]

    for idx in indexes:
        print(f"    Dropping index: {idx}")
        with conn.cursor() as cur:
            # Identifier quote an toàn; DROP INDEX không hỗ trợ CONCURRENTLY cùng IF EXISTS trên mọi version theo cùng cú pháp
            cur.execute(
                sql.SQL("DROP INDEX IF EXISTS {}").format(sql.Identifier(idx))
            )


def create_index(conn, index_name: str, table: str, definition: str) -> None:
    """
    Tạo index.
    Lưu ý: CONCURRENTLY *không* được chạy trong transaction block
    → connection phải autocommit=True.
    """
    concurrent = " CONCURRENTLY" if USE_CONCURRENTLY else ""
    # definition ví dụ: "(user_id, created_at, status)" hoặc "(user_id, created_at) INCLUDE (status)"
    ddl = (
        f"CREATE INDEX{concurrent} IF NOT EXISTS {index_name} "
        f"ON {table} {definition}"
    )
    print(f"    Creating: {ddl}")
    with conn.cursor() as cur:
        cur.execute(ddl)

    with conn.cursor() as cur:
        cur.execute(sql.SQL("ANALYZE {}").format(sql.Identifier(table)))


def get_execution_plan(conn, query: str, params: Optional[tuple] = None) -> dict:
    with conn.cursor() as cur:
        explain = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
        cur.execute(explain, params)
        return cur.fetchone()[0][0]


def measure_query(conn, query: str, params_list: List[tuple]) -> Dict[str, float]:
    if not params_list:
        raise ValueError("params_list rỗng")

    latencies: List[float] = []
    with conn.cursor() as cur:
        for i in range(WARMUP_RUNS):
            params = params_list[i % len(params_list)]
            cur.execute(query, params)
            cur.fetchall()

        for i in range(MEASURE_RUNS):
            params = params_list[i % len(params_list)]
            t0 = time.perf_counter()
            cur.execute(query, params)
            cur.fetchall()
            latencies.append((time.perf_counter() - t0) * 1000.0)

    arr = np.asarray(latencies, dtype=float)
    return {
        "p50": round(float(np.percentile(arr, 50)), 3),
        "p95": round(float(np.percentile(arr, 95)), 3),
        "p99": round(float(np.percentile(arr, 99)), 3),
        "avg": round(float(np.mean(arr)), 3),
        "std": round(float(np.std(arr)), 3),
        "min": round(float(np.min(arr)), 3),
        "max": round(float(np.max(arr)), 3),
        "samples": int(arr.size),
    }


# ====================== INDEX & QUERY DEFINITIONS ======================

ORDERS_INDEXES = [
    {"name": "idx_orders_baseline", "def": None, "label": "O0 - Baseline (no secondary index)"},
    {
        "name": "idx_orders_uid_time_stt",
        "def": "(user_id, created_at, status)",
        "label": "O1 - (user_id, created_at, status)",
    },
    {
        "name": "idx_orders_uid_stt_time",
        "def": "(user_id, status, created_at)",
        "label": "O2 - (user_id, status, created_at)",
    },
    {
        "name": "idx_orders_time_uid_stt",
        "def": "(created_at, user_id, status)",
        "label": "O3 - (created_at, user_id, status)",
    },
    {
        "name": "idx_orders_stt_uid_time",
        "def": "(status, user_id, created_at)",
        "label": "O4 - (status, user_id, created_at)",
    },
    {
        "name": "idx_orders_covering",
        "def": "(user_id, created_at) INCLUDE (status)",
        "label": "O5 - Covering (user_id, created_at) INCLUDE status",
    },
]

ORDERS_QUERIES = [
    {
        "id": "OQ1",
        "name": "User + Time range + Status",
        "sql": """
            SELECT order_id, user_id, status, created_at, amount
            FROM orders
            WHERE user_id = %s
              AND created_at >= %s
              AND created_at < %s
              AND status = %s
        """,
        "param_generator": lambda: (
            random.randint(1, MAX_USER_ID),
            datetime.now() - timedelta(days=random.randint(10, 90)),
            datetime.now() - timedelta(days=random.randint(0, 9)),
            random.choice([2, 3]),
        ),
    },
    {
        "id": "OQ2",
        "name": "User + Status IN + Time",
        "sql": """
            SELECT order_id, status, created_at, amount
            FROM orders
            WHERE user_id = %s
              AND status IN (%s, %s)
              AND created_at >= %s
            ORDER BY created_at DESC
            LIMIT 30
        """,
        "param_generator": lambda: (
            random.randint(1, MAX_USER_ID),
            2,
            3,
            datetime.now() - timedelta(days=random.randint(30, 180)),
        ),
    },
    {
        "id": "OQ3",
        "name": "Aggregation by Status",
        "sql": """
            SELECT status, COUNT(*) AS cnt, COALESCE(SUM(amount), 0) AS total_amount
            FROM orders
            WHERE user_id = %s
              AND created_at >= %s
              AND created_at < %s
            GROUP BY status
        """,
        "param_generator": lambda: (
            random.randint(1, MAX_USER_ID),
            datetime.now() - timedelta(days=random.randint(60, 200)),
            datetime.now() - timedelta(days=random.randint(0, 30)),
        ),
    },
    {
        "id": "OQ4",
        "name": "Covering-style query",
        "sql": """
            SELECT user_id, created_at, status
            FROM orders
            WHERE user_id = %s
              AND created_at >= %s
              AND created_at < %s
        """,
        "param_generator": lambda: (
            random.randint(1, MAX_USER_ID),
            datetime.now() - timedelta(days=random.randint(5, 45)),
            datetime.now() - timedelta(days=random.randint(0, 4)),
        ),
    },
]

USERS_INDEXES = [
    {"name": "idx_users_baseline", "def": None, "label": "U0 - Baseline"},
    {
        "name": "idx_users_city_dist_age",
        "def": "(city_id, district_id, age_group)",
        "label": "U1 - (city_id, district_id, age_group)",
    },
    {
        "name": "idx_users_dist_city_age",
        "def": "(district_id, city_id, age_group)",
        "label": "U2 - (district_id, city_id, age_group)",
    },
    {
        "name": "idx_users_age_city_dist",
        "def": "(age_group, city_id, district_id)",
        "label": "U3 - (age_group, city_id, district_id)",
    },
    {
        "name": "idx_users_city_age_dist",
        "def": "(city_id, age_group, district_id)",
        "label": "U4 - (city_id, age_group, district_id)",
    },
    {
        "name": "idx_users_covering",
        "def": "(city_id, district_id) INCLUDE (age_group)",
        "label": "U5 - Covering",
    },
]

USERS_QUERIES = [
    {
        "id": "UQ1",
        "name": "City + District + Age",
        "sql": """
            SELECT user_id, city_id, district_id, age_group, gender
            FROM users
            WHERE city_id = %s
              AND district_id = %s
              AND age_group = %s
              AND is_active = true
        """,
        "param_generator": lambda: (
            random.randint(1, 63),
            random.randint(1, 63) * 100 + random.randint(1, 20),
            random.choice([1, 2, 3, 4]),
        ),
    },
    {
        "id": "UQ2",
        "name": "City + Age group aggregation",
        "sql": """
            SELECT age_group, COUNT(*) AS cnt
            FROM users
            WHERE city_id = %s
              AND is_active = true
            GROUP BY age_group
            ORDER BY age_group
        """,
        "param_generator": lambda: (random.randint(1, 63),),
    },
    {
        "id": "UQ3",
        "name": "District first (correlation test)",
        "sql": """
            SELECT user_id, city_id, district_id, age_group
            FROM users
            WHERE district_id = %s
              AND city_id = %s
        """,
        "param_generator": lambda: (
            random.randint(1, 63) * 100 + random.randint(1, 20),
            random.randint(1, 63),
        ),
    },
]

ACTIVITIES_INDEXES = [
    {"name": "idx_act_baseline", "def": None, "label": "A0 - Baseline"},
    {
        "name": "idx_act_uid_time_type",
        "def": "(user_id, event_time, event_type)",
        "label": "A1 - (user_id, event_time, event_type)",
    },
    {
        "name": "idx_act_uid_type_time",
        "def": "(user_id, event_type, event_time)",
        "label": "A2 - (user_id, event_type, event_time)",
    },
    {
        "name": "idx_act_time_uid_type",
        "def": "(event_time, user_id, event_type)",
        "label": "A3 - (event_time, user_id, event_type)",
    },
    {
        "name": "idx_act_type_uid_time",
        "def": "(event_type, user_id, event_time)",
        "label": "A4 - (event_type, user_id, event_time)",
    },
    {
        "name": "idx_act_covering",
        "def": "(user_id, event_time) INCLUDE (event_type)",
        "label": "A5 - Covering",
    },
]

ACTIVITIES_QUERIES = [
    {
        "id": "AQ1",
        "name": "User + Time range",
        "sql": """
            SELECT activity_id, user_id, event_type, event_time, device_type
            FROM user_activities
            WHERE user_id = %s
              AND event_time >= %s
              AND event_time < %s
            ORDER BY event_time DESC
            LIMIT 100
        """,
        "param_generator": lambda: (
            random.randint(1, MAX_USER_ID),
            datetime.now() - timedelta(days=random.randint(7, 60)),
            datetime.now() - timedelta(days=random.randint(0, 6)),
        ),
    },
    {
        "id": "AQ2",
        "name": "User + Event type + Time",
        "sql": """
            SELECT activity_id, event_type, event_time, device_type
            FROM user_activities
            WHERE user_id = %s
              AND event_type = %s
              AND event_time >= %s
            ORDER BY event_time DESC
            LIMIT 50
        """,
        "param_generator": lambda: (
            random.randint(1, MAX_USER_ID),
            random.choice([1, 2, 3, 4]),
            datetime.now() - timedelta(days=random.randint(15, 120)),
        ),
    },
    {
        "id": "AQ3",
        "name": "Event type first (low selectivity first)",
        "sql": """
            SELECT user_id, event_type, event_time
            FROM user_activities
            WHERE event_type = %s
              AND event_time >= %s
              AND event_time < %s
              AND user_id = %s
        """,
        "param_generator": lambda: (
            random.choice([1, 2, 3]),
            datetime.now() - timedelta(days=random.randint(10, 40)),
            datetime.now() - timedelta(days=random.randint(0, 9)),
            random.randint(1, MAX_USER_ID),
        ),
    },
    {
        "id": "AQ4",
        "name": "Aggregation by event_type",
        "sql": """
            SELECT event_type, COUNT(*) AS cnt
            FROM user_activities
            WHERE user_id = %s
              AND event_time >= %s
            GROUP BY event_type
            ORDER BY cnt DESC
        """,
        "param_generator": lambda: (
            random.randint(1, MAX_USER_ID),
            datetime.now() - timedelta(days=random.randint(30, 180)),
        ),
    },
]


def run_table_benchmark(table: str, indexes: list, queries: list) -> List[Dict[str, Any]]:
    print(f"\n{'=' * 80}")
    print(f" BẮT ĐẦU BENCHMARK BẢNG: {table.upper()}")
    print(f"{'=' * 80}")

    results: List[Dict[str, Any]] = []

    for idx_info in indexes:
        index_name = idx_info["name"]
        index_def = idx_info["def"]
        label = idx_info["label"]

        print(f"\n>>> Phương án Index: {label}")

        # DDL (DROP/CREATE INDEX CONCURRENTLY) → bắt buộc autocommit
        with get_conn(autocommit=True) as conn:
            drop_secondary_indexes(conn, table)
            if index_def is not None:
                create_index(conn, index_name, table, index_def)
            else:
                print("    → Baseline (không tạo index phụ)")

        # Đo query + EXPLAIN trên connection thường
        with get_conn(autocommit=True) as conn:
            for q in queries:
                print(f"    Running query {q['id']}: {q['name']} ...", end=" ", flush=True)

                params_list = [q["param_generator"]() for _ in range(80)]
                metrics = measure_query(conn, q["sql"], params_list)

                plan = get_execution_plan(conn, q["sql"], params_list[0])
                plan_node = plan.get("Plan", {}).get("Node Type", "?")
                plan_cost = plan.get("Plan", {}).get("Total Cost")

                plan_file = RESULT_DIR / "plans" / f"{table}_{index_name}_{q['id']}.json"
                plan_file.write_text(
                    json.dumps(plan, indent=2, default=str), encoding="utf-8"
                )

                row = {
                    "timestamp": datetime.now().isoformat(),
                    "engine": "postgresql-btree",
                    "table": table,
                    "index_name": index_name,
                    "index_label": label,
                    "index_def": index_def if index_def else "NONE",
                    "query_id": q["id"],
                    "query_name": q["name"],
                    "plan_node": plan_node,
                    "plan_cost": plan_cost,
                    **metrics,
                }
                results.append(row)
                print(f"p95={metrics['p95']:.2f}ms | p99={metrics['p99']:.2f}ms | Plan={plan_node}")

    csv_file = RESULT_DIR / f"{table}_results.csv"
    if results:
        keys = list(results[0].keys())
        with csv_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(results)
        print(f"\n>>> Đã lưu kết quả vào: {csv_file}")

    return results


def main() -> None:
    print("=" * 80)
    print(" POSTGRESQL (B-Tree) BENCHMARK — COMPOSITE INDEX ORDER STUDY")
    print(f" host={DB_CONFIG['host']}:{DB_CONFIG['port']} db={DB_CONFIG['dbname']} user={DB_CONFIG['user']}")
    print(f" warmup={WARMUP_RUNS} measure={MEASURE_RUNS} concurrently={USE_CONCURRENTLY}")
    print(f" MAX_USER_ID={MAX_USER_ID} RESULT_DIR={RESULT_DIR.resolve()}")
    print("=" * 80)

    try:
        check_prerequisites()
    except psycopg2.OperationalError as e:
        print(
            f"\n[error] Không kết nối được PostgreSQL: {e}\n"
            "Kiểm tra container/service và biến PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    all_results: List[Dict[str, Any]] = []
    all_results.extend(run_table_benchmark("orders", ORDERS_INDEXES, ORDERS_QUERIES))
    all_results.extend(run_table_benchmark("users", USERS_INDEXES, USERS_QUERIES))
    all_results.extend(
        run_table_benchmark("user_activities", ACTIVITIES_INDEXES, ACTIVITIES_QUERIES)
    )

    summary_file = RESULT_DIR / "all_results_summary.csv"
    if all_results:
        keys = list(all_results[0].keys())
        with summary_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_results)

    print("\n" + "=" * 80)
    print(" HOÀN THÀNH TOÀN BỘ BENCHMARK POSTGRESQL")
    print(f" Kết quả tổng hợp: {summary_file}")
    print(f" Execution Plans:  {RESULT_DIR / 'plans'}")
    print("=" * 80)


if __name__ == "__main__":
    main()
