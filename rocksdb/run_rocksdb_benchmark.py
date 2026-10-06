#!/usr/bin/env python3
"""
Full Automation Benchmark Script — RocksDB (LSM-Tree)
Đề tài: Ảnh hưởng của thứ tự cột trong Composite Key/Index đến Latency p95/p99

So sánh đối xứng với script PostgreSQL (B-Tree):
- Cùng 3 "bảng": orders, users, user_activities
- Cùng ý tưởng: đổi thứ tự cột trong composite key
- Cùng chỉ số: p50 / p95 / p99

Khác biệt quan trọng (cần nêu trong báo cáo):
- RocksDB là KV-store, không có SQL Planner / EXPLAIN
- "Composite Index" = cách mã hóa key (column order = key prefix order)
- Range/prefix scan phụ thuộc chặt vào leftmost prefix
- Có thể đọc thêm statistics: read amplification, block cache hit

Cài đặt:
  pip install rocksdict numpy

Chạy:
  python run_rocksdb_benchmark.py
"""

from __future__ import annotations

import csv
import json
import os
import random
import struct
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

try:
    from rocksdict import Rdict, Options, AccessType, WriteBatch
except ImportError as e:
    raise SystemExit(
        "Thiếu thư viện rocksdict.\n"
        "  pip install rocksdict numpy\n"
        f"Chi tiết: {e}"
    )

# ====================== CẤU HÌNH ======================
DATA_DIR = Path(os.environ.get("ROCKSDB_DATA_DIR", "./rocksdb_data"))
RESULT_DIR = Path(os.environ.get("ROCKSDB_RESULT_DIR", "./benchmark_results_rocksdb"))

# Quy mô dữ liệu (giảm nếu máy yếu)
NUM_USERS = int(os.environ.get("NUM_USERS", "200_000").replace("_", ""))
NUM_ORDERS = int(os.environ.get("NUM_ORDERS", "1_000_000").replace("_", ""))
NUM_ACTIVITIES = int(os.environ.get("NUM_ACTIVITIES", "2_000_000").replace("_", ""))

WARMUP_RUNS = int(os.environ.get("WARMUP_RUNS", "100"))
MEASURE_RUNS = int(os.environ.get("MEASURE_RUNS", "800"))

# Tái sử dụng DB đã seed (True = không xóa / không seed lại)
REUSE_EXISTING = os.environ.get("REUSE_EXISTING", "0") == "1"

RESULT_DIR.mkdir(parents=True, exist_ok=True)
(RESULT_DIR / "plans").mkdir(parents=True, exist_ok=True)
# ======================================================


# ---------- Key encoding helpers ----------
# Key format: table_prefix | col1 | col2 | col3 | id
# Thứ tự cột khác nhau = "phương án index" khác nhau.


def u32(n: int) -> bytes:
    return struct.pack(">I", int(n) & 0xFFFFFFFF)


def u64(n: int) -> bytes:
    return struct.pack(">Q", int(n) & 0xFFFFFFFFFFFFFFFF)


def i64(n: int) -> bytes:
    return struct.pack(">q", int(n))


def ts_to_int(dt: datetime) -> int:
    return int(dt.timestamp())


def encode_orders_key(order: Dict[str, Any], key_order: Tuple[str, ...]) -> bytes:
    """Mã hóa composite key cho orders theo thứ tự cột."""
    parts = [b"O"]  # table tag
    mapping = {
        "user_id": u32(order["user_id"]),
        "status": u32(order["status"]),
        "created_at": u64(ts_to_int(order["created_at"])),
        "order_id": u64(order["order_id"]),
    }
    for col in key_order:
        parts.append(mapping[col])
    # luôn gắn order_id cuối để unique (trừ khi đã có trong order)
    if "order_id" not in key_order:
        parts.append(mapping["order_id"])
    return b"".join(parts)


def encode_users_key(user: Dict[str, Any], key_order: Tuple[str, ...]) -> bytes:
    parts = [b"U"]
    mapping = {
        "city_id": u32(user["city_id"]),
        "district_id": u32(user["district_id"]),
        "age_group": u32(user["age_group"]),
        "user_id": u64(user["user_id"]),
    }
    for col in key_order:
        parts.append(mapping[col])
    if "user_id" not in key_order:
        parts.append(mapping["user_id"])
    return b"".join(parts)


def encode_activities_key(act: Dict[str, Any], key_order: Tuple[str, ...]) -> bytes:
    parts = [b"A"]
    mapping = {
        "user_id": u32(act["user_id"]),
        "event_type": u32(act["event_type"]),
        "event_time": u64(ts_to_int(act["event_time"])),
        "activity_id": u64(act["activity_id"]),
    }
    for col in key_order:
        parts.append(mapping[col])
    if "activity_id" not in key_order:
        parts.append(mapping["activity_id"])
    return b"".join(parts)


def encode_value(payload: Dict[str, Any]) -> bytes:
    # JSON đủ cho thí nghiệm; production có thể dùng msgpack
    def default(o):
        if isinstance(o, datetime):
            return o.isoformat()
        raise TypeError(type(o))

    return json.dumps(payload, default=default).encode("utf-8")


# ---------- Open / seed DB ----------

def make_options() -> Options:
    opt = Options()
    # Cấu hình gần production để số liệu có ý nghĩa
    opt.create_if_missing(True)
    opt.set_write_buffer_size(64 * 1024 * 1024)       # 64MB
    opt.set_max_write_buffer_number(3)
    opt.set_target_file_size_base(64 * 1024 * 1024)
    opt.set_level_zero_file_num_compaction_trigger(4)
    opt.set_max_background_jobs(4)
    opt.set_compression_type("lz4")  # nếu build không hỗ trợ sẽ fallback
    return opt


def open_db(path: Path, read_only: bool = False) -> Rdict:
    path.mkdir(parents=True, exist_ok=True)
    opt = make_options()
    if read_only:
        return Rdict(str(path), options=opt, access_type=AccessType.read_only())
    return Rdict(str(path), options=opt)


def seed_dataset(db_path: Path, key_order_orders, key_order_users, key_order_acts) -> Dict[str, int]:
    """
    Seed 1 DB instance cho 1 phương án thứ tự cột.
    Mỗi phương án index = 1 thư mục RocksDB riêng (tránh lẫn key encoding).
    """
    if db_path.exists() and any(db_path.iterdir()) and REUSE_EXISTING:
        print(f"    REUSE existing DB: {db_path}")
        return {"users": NUM_USERS, "orders": NUM_ORDERS, "activities": NUM_ACTIVITIES}

    if db_path.exists():
        # Xóa DB cũ của phương án này
        import shutil
        shutil.rmtree(db_path)

    db = open_db(db_path)
    print(f"    Seeding {db_path.name} ...")

    batch = WriteBatch()
    batch_size = 5000
    count = 0

    # users
    for uid in range(1, NUM_USERS + 1):
        city_id = 1 + (uid % 63)
        user = {
            "user_id": uid,
            "city_id": city_id,
            "district_id": city_id * 100 + 1 + (uid % 20),
            "age_group": 1 + (uid % 4),
            "gender": "M" if uid % 2 == 0 else "F",
            "is_active": (uid % 12) != 0,
            "created_at": datetime(2020, 1, 1) + timedelta(days=uid % 1800),
        }
        key = encode_users_key(user, key_order_users)
        batch[key] = encode_value(user)
        count += 1
        if count % batch_size == 0:
            db.write(batch)
            batch = WriteBatch()
    db.write(batch)
    batch = WriteBatch()

    # orders
    for oid in range(1, NUM_ORDERS + 1):
        order = {
            "order_id": oid,
            "user_id": 1 + (oid % NUM_USERS),
            "status": 1 + (oid % 5),
            "created_at": datetime.now() - timedelta(days=oid % 400, seconds=oid % 86400),
            "amount": float(50000 + (oid % 5_000_000)),
            "payment_method": 1 + (oid % 4),
        }
        key = encode_orders_key(order, key_order_orders)
        batch[key] = encode_value(order)
        count += 1
        if count % batch_size == 0:
            db.write(batch)
            batch = WriteBatch()
            if oid % 200_000 == 0:
                print(f"      orders seeded: {oid:,}/{NUM_ORDERS:,}")
    db.write(batch)
    batch = WriteBatch()

    # activities
    for aid in range(1, NUM_ACTIVITIES + 1):
        act = {
            "activity_id": aid,
            "user_id": 1 + (aid % NUM_USERS),
            "event_type": 1 + (aid % 6),
            "event_time": datetime.now() - timedelta(days=aid % 120, seconds=aid % 86400),
            "device_type": 1 + (aid % 3),
        }
        key = encode_activities_key(act, key_order_acts)
        batch[key] = encode_value(act)
        count += 1
        if count % batch_size == 0:
            db.write(batch)
            batch = WriteBatch()
            if aid % 400_000 == 0:
                print(f"      activities seeded: {aid:,}/{NUM_ACTIVITIES:,}")
    db.write(batch)

    # Flush để số liệu đọc ổn định hơn
    try:
        db.flush(True)
    except Exception:
        pass

    db.close()
    return {"users": NUM_USERS, "orders": NUM_ORDERS, "activities": NUM_ACTIVITIES}


# ---------- Measure helpers ----------

def percentiles(latencies_ms: List[float]) -> Dict[str, float]:
    arr = np.array(latencies_ms, dtype=float)
    return {
        "p50": round(float(np.percentile(arr, 50)), 3),
        "p95": round(float(np.percentile(arr, 95)), 3),
        "p99": round(float(np.percentile(arr, 99)), 3),
        "avg": round(float(np.mean(arr)), 3),
        "std": round(float(np.std(arr)), 3),
        "min": round(float(np.min(arr)), 3),
        "max": round(float(np.max(arr)), 3),
        "samples": int(len(arr)),
    }


def measure(fn: Callable[[], Any], warmup: int, runs: int) -> Dict[str, float]:
    for _ in range(warmup):
        fn()
    latencies = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        latencies.append((time.perf_counter() - t0) * 1000)
    return percentiles(latencies)


def prefix_scan(db: Rdict, prefix: bytes, limit: int = 100) -> int:
    """Đếm tối đa `limit` bản ghi có key bắt đầu bằng prefix."""
    n = 0
    it = db.iter()
    it.seek(prefix)
    while it.valid():
        k = it.key()
        if not k.startswith(prefix):
            break
        n += 1
        if n >= limit:
            break
        it.next()
    return n


def range_scan(db: Rdict, start: bytes, end: bytes, limit: int = 100) -> int:
    n = 0
    it = db.iter()
    it.seek(start)
    while it.valid():
        k = it.key()
        if k >= end:
            break
        n += 1
        if n >= limit:
            break
        it.next()
    return n


# ====================== ĐỊNH NGHĨA "INDEX" (key order) & QUERY ======================

# ----- ORDERS -----
# key_order không gồm order_id (sẽ tự gắn cuối để unique)
ORDERS_INDEXES = [
    {"name": "idx_orders_baseline", "key_order": ("order_id",), "label": "O0 - Baseline (chỉ order_id)"},
    {"name": "idx_orders_uid_time_stt", "key_order": ("user_id", "created_at", "status"), "label": "O1 - (user_id, created_at, status)"},
    {"name": "idx_orders_uid_stt_time", "key_order": ("user_id", "status", "created_at"), "label": "O2 - (user_id, status, created_at)"},
    {"name": "idx_orders_time_uid_stt", "key_order": ("created_at", "user_id", "status"), "label": "O3 - (created_at, user_id, status)"},
    {"name": "idx_orders_stt_uid_time", "key_order": ("status", "user_id", "created_at"), "label": "O4 - (status, user_id, created_at)"},
]

USERS_INDEXES = [
    {"name": "idx_users_baseline", "key_order": ("user_id",), "label": "U0 - Baseline"},
    {"name": "idx_users_city_dist_age", "key_order": ("city_id", "district_id", "age_group"), "label": "U1 - (city_id, district_id, age_group)"},
    {"name": "idx_users_dist_city_age", "key_order": ("district_id", "city_id", "age_group"), "label": "U2 - (district_id, city_id, age_group)"},
    {"name": "idx_users_age_city_dist", "key_order": ("age_group", "city_id", "district_id"), "label": "U3 - (age_group, city_id, district_id)"},
    {"name": "idx_users_city_age_dist", "key_order": ("city_id", "age_group", "district_id"), "label": "U4 - (city_id, age_group, district_id)"},
]

ACTIVITIES_INDEXES = [
    {"name": "idx_act_baseline", "key_order": ("activity_id",), "label": "A0 - Baseline"},
    {"name": "idx_act_uid_time_type", "key_order": ("user_id", "event_time", "event_type"), "label": "A1 - (user_id, event_time, event_type)"},
    {"name": "idx_act_uid_type_time", "key_order": ("user_id", "event_type", "event_time"), "label": "A2 - (user_id, event_type, event_time)"},
    {"name": "idx_act_time_uid_type", "key_order": ("event_time", "user_id", "event_type"), "label": "A3 - (event_time, user_id, event_type)"},
    {"name": "idx_act_type_uid_time", "key_order": ("event_type", "user_id", "event_time"), "label": "A4 - (event_type, user_id, event_time)"},
]


def build_orders_queries(key_order: Tuple[str, ...]) -> List[Dict]:
    """
    Mỗi query xây prefix/range dựa trên key_order hiện tại.
    Nếu leftmost prefix không khớp điều kiện query → phải scan rộng hơn (phản ánh đúng LSM).
    """
    queries = []

    # OQ1: user_id + time range + status
    def oq1_run(db: Rdict):
        uid = random.randint(1, NUM_USERS)
        t0 = datetime.now() - timedelta(days=random.randint(10, 90))
        t1 = datetime.now() - timedelta(days=random.randint(0, 9))
        status = random.choice([2, 3])
        # Nếu key bắt đầu bằng user_id → prefix tốt
        if key_order[:1] == ("user_id",):
            prefix = b"O" + u32(uid)
            return prefix_scan(db, prefix, limit=50)
        # Nếu bắt đầu bằng status
        if key_order[:1] == ("status",):
            prefix = b"O" + u32(status)
            return prefix_scan(db, prefix, limit=50)
        # created_at first → range theo thời gian (thô)
        if key_order[:1] == ("created_at",):
            start = b"O" + u64(ts_to_int(t0))
            end = b"O" + u64(ts_to_int(t1) + 1)
            return range_scan(db, start, end, limit=50)
        # baseline order_id only → full-ish prefix scan (đắt)
        return prefix_scan(db, b"O", limit=50)

    queries.append({
        "id": "OQ1",
        "name": "User + Time range + Status",
        "run": oq1_run,
        "note": "prefix phụ thuộc leftmost của key_order",
    })

    # OQ2: user + status
    def oq2_run(db: Rdict):
        uid = random.randint(1, NUM_USERS)
        st = random.choice([2, 3])
        if key_order[:2] == ("user_id", "status") or key_order[:1] == ("user_id",):
            prefix = b"O" + u32(uid)
            return prefix_scan(db, prefix, limit=30)
        if key_order[:1] == ("status",):
            prefix = b"O" + u32(st)
            return prefix_scan(db, prefix, limit=30)
        return prefix_scan(db, b"O", limit=30)

    queries.append({
        "id": "OQ2",
        "name": "User + Status",
        "run": oq2_run,
        "note": "prefix user_id hoặc status",
    })

    # OQ3: aggregation-like — scan theo user rồi đếm (mô phỏng GROUP BY)
    def oq3_run(db: Rdict):
        uid = random.randint(1, NUM_USERS)
        if key_order[:1] == ("user_id",):
            prefix = b"O" + u32(uid)
            return prefix_scan(db, prefix, limit=200)
        return prefix_scan(db, b"O", limit=200)

    queries.append({
        "id": "OQ3",
        "name": "Aggregation-like scan by user",
        "run": oq3_run,
        "note": "scan prefix user_id nếu có",
    })

    # OQ4: covering-style — chỉ đọc key/value đã đủ (vẫn decode value)
    def oq4_run(db: Rdict):
        uid = random.randint(1, NUM_USERS)
        t0 = datetime.now() - timedelta(days=random.randint(5, 45))
        if key_order[:1] == ("user_id",):
            prefix = b"O" + u32(uid)
            return prefix_scan(db, prefix, limit=50)
        start = b"O" + u64(ts_to_int(t0))
        end = b"O" + u64(ts_to_int(t0) + 7 * 86400)
        return range_scan(db, start, end, limit=50)

    queries.append({
        "id": "OQ4",
        "name": "Covering-style prefix/range",
        "run": oq4_run,
        "note": "prefix user hoặc range time",
    })

    return queries


def build_users_queries(key_order: Tuple[str, ...]) -> List[Dict]:
    queries = []

    def uq1_run(db: Rdict):
        city = random.randint(1, 63)
        dist = city * 100 + random.randint(1, 20)
        age = random.choice([1, 2, 3, 4])
        if key_order[:3] == ("city_id", "district_id", "age_group"):
            prefix = b"U" + u32(city) + u32(dist) + u32(age)
            return prefix_scan(db, prefix, limit=50)
        if key_order[:2] == ("city_id", "district_id"):
            prefix = b"U" + u32(city) + u32(dist)
            return prefix_scan(db, prefix, limit=50)
        if key_order[:1] == ("city_id",):
            prefix = b"U" + u32(city)
            return prefix_scan(db, prefix, limit=50)
        if key_order[:1] == ("district_id",):
            prefix = b"U" + u32(dist)
            return prefix_scan(db, prefix, limit=50)
        if key_order[:1] == ("age_group",):
            prefix = b"U" + u32(age)
            return prefix_scan(db, prefix, limit=50)
        return prefix_scan(db, b"U", limit=50)

    queries.append({"id": "UQ1", "name": "City + District + Age", "run": uq1_run, "note": "leftmost prefix city/dist/age"})

    def uq2_run(db: Rdict):
        city = random.randint(1, 63)
        if key_order[:1] == ("city_id",):
            return prefix_scan(db, b"U" + u32(city), limit=200)
        return prefix_scan(db, b"U", limit=200)

    queries.append({"id": "UQ2", "name": "City aggregation-like", "run": uq2_run, "note": "prefix city_id"})

    def uq3_run(db: Rdict):
        city = random.randint(1, 63)
        dist = city * 100 + random.randint(1, 20)
        if key_order[:1] == ("district_id",):
            return prefix_scan(db, b"U" + u32(dist), limit=50)
        if key_order[:2] == ("city_id", "district_id"):
            return prefix_scan(db, b"U" + u32(city) + u32(dist), limit=50)
        return prefix_scan(db, b"U", limit=50)

    queries.append({"id": "UQ3", "name": "District first (correlation)", "run": uq3_run, "note": "district vs city order"})
    return queries


def build_activities_queries(key_order: Tuple[str, ...]) -> List[Dict]:
    queries = []

    def aq1_run(db: Rdict):
        uid = random.randint(1, NUM_USERS)
        t0 = datetime.now() - timedelta(days=random.randint(7, 60))
        t1 = datetime.now() - timedelta(days=random.randint(0, 6))
        if key_order[:1] == ("user_id",):
            return prefix_scan(db, b"A" + u32(uid), limit=100)
        if key_order[:1] == ("event_time",):
            start = b"A" + u64(ts_to_int(t0))
            end = b"A" + u64(ts_to_int(t1) + 1)
            return range_scan(db, start, end, limit=100)
        return prefix_scan(db, b"A", limit=100)

    queries.append({"id": "AQ1", "name": "User + Time range", "run": aq1_run, "note": "prefix user hoặc range time"})

    def aq2_run(db: Rdict):
        uid = random.randint(1, NUM_USERS)
        et = random.choice([1, 2, 3, 4])
        if key_order[:2] == ("user_id", "event_type") or key_order[:1] == ("user_id",):
            return prefix_scan(db, b"A" + u32(uid), limit=50)
        if key_order[:1] == ("event_type",):
            return prefix_scan(db, b"A" + u32(et), limit=50)
        return prefix_scan(db, b"A", limit=50)

    queries.append({"id": "AQ2", "name": "User + Event type + Time", "run": aq2_run, "note": "prefix user/type"})

    def aq3_run(db: Rdict):
        et = random.choice([1, 2, 3])
        uid = random.randint(1, NUM_USERS)
        if key_order[:1] == ("event_type",):
            return prefix_scan(db, b"A" + u32(et), limit=50)
        if key_order[:1] == ("user_id",):
            return prefix_scan(db, b"A" + u32(uid), limit=50)
        return prefix_scan(db, b"A", limit=50)

    queries.append({"id": "AQ3", "name": "Event type first (low selectivity)", "run": aq3_run, "note": "type vs user order"})

    def aq4_run(db: Rdict):
        uid = random.randint(1, NUM_USERS)
        if key_order[:1] == ("user_id",):
            return prefix_scan(db, b"A" + u32(uid), limit=200)
        return prefix_scan(db, b"A", limit=200)

    queries.append({"id": "AQ4", "name": "Aggregation-like by user", "run": aq4_run, "note": "scan by user"})
    return queries


# ====================== RUN ======================

def run_entity_benchmark(
    entity: str,
    indexes: List[Dict],
    build_queries: Callable[[Tuple[str, ...]], List[Dict]],
    key_field_orders_for_seed: Dict[str, Tuple[str, ...]],
) -> List[Dict]:
    """
    entity: 'orders' | 'users' | 'user_activities'
    Mỗi index variant = 1 RocksDB directory riêng.
    """
    print(f"\n{'=' * 80}")
    print(f" BẮT ĐẦU BENCHMARK ROCKSDB (LSM) — {entity.upper()}")
    print(f"{'=' * 80}")

    results: List[Dict] = []

    for idx in indexes:
        name = idx["name"]
        key_order = tuple(idx["key_order"])
        label = idx["label"]
        db_path = DATA_DIR / f"{entity}__{name}"

        print(f"\n>>> Phương án key order: {label}")
        print(f"    key_order = {key_order}")

        # Seed: truyền key_order tương ứng entity; entity khác dùng order mặc định hợp lý
        ko_orders = key_order if entity == "orders" else ("user_id", "created_at", "status")
        ko_users = key_order if entity == "users" else ("city_id", "district_id", "age_group")
        ko_acts = key_order if entity == "user_activities" else ("user_id", "event_time", "event_type")

        # Chỉ seed đúng entity vào DB của phương án (tiết kiệm dung lượng)
        # → mỗi DB chỉ chứa 1 entity
        if db_path.exists() and not REUSE_EXISTING:
            import shutil
            shutil.rmtree(db_path)

        db = open_db(db_path)
        print(f"    Seeding entity={entity} ...")
        batch = WriteBatch()
        batch_size = 5000
        written = 0

        if entity == "users":
            for uid in range(1, NUM_USERS + 1):
                city_id = 1 + (uid % 63)
                user = {
                    "user_id": uid,
                    "city_id": city_id,
                    "district_id": city_id * 100 + 1 + (uid % 20),
                    "age_group": 1 + (uid % 4),
                    "gender": "M" if uid % 2 == 0 else "F",
                    "is_active": (uid % 12) != 0,
                    "created_at": datetime(2020, 1, 1) + timedelta(days=uid % 1800),
                }
                batch[encode_users_key(user, key_order)] = encode_value(user)
                written += 1
                if written % batch_size == 0:
                    db.write(batch)
                    batch = WriteBatch()
            db.write(batch)

        elif entity == "orders":
            for oid in range(1, NUM_ORDERS + 1):
                order = {
                    "order_id": oid,
                    "user_id": 1 + (oid % NUM_USERS),
                    "status": 1 + (oid % 5),
                    "created_at": datetime.now() - timedelta(days=oid % 400, seconds=oid % 86400),
                    "amount": float(50000 + (oid % 5_000_000)),
                    "payment_method": 1 + (oid % 4),
                }
                batch[encode_orders_key(order, key_order)] = encode_value(order)
                written += 1
                if written % batch_size == 0:
                    db.write(batch)
                    batch = WriteBatch()
                    if oid % 200_000 == 0:
                        print(f"      {oid:,}/{NUM_ORDERS:,}")
            db.write(batch)

        else:  # user_activities
            for aid in range(1, NUM_ACTIVITIES + 1):
                act = {
                    "activity_id": aid,
                    "user_id": 1 + (aid % NUM_USERS),
                    "event_type": 1 + (aid % 6),
                    "event_time": datetime.now() - timedelta(days=aid % 120, seconds=aid % 86400),
                    "device_type": 1 + (aid % 3),
                }
                batch[encode_activities_key(act, key_order)] = encode_value(act)
                written += 1
                if written % batch_size == 0:
                    db.write(batch)
                    batch = WriteBatch()
                    if aid % 400_000 == 0:
                        print(f"      {aid:,}/{NUM_ACTIVITIES:,}")
            db.write(batch)

        try:
            db.flush(True)
        except Exception:
            pass

        queries = build_queries(key_order)
        for q in queries:
            print(f"    Running {q['id']}: {q['name']} ...", end=" ")

            def one_run(q=q, db=db):
                return q["run"](db)

            metrics = measure(one_run, WARMUP_RUNS, MEASURE_RUNS)

            # "Plan" tương đương: mô tả chiến lược scan
            plan_info = {
                "engine": "rocksdb-lsm",
                "entity": entity,
                "key_order": list(key_order),
                "query_id": q["id"],
                "access_pattern": q.get("note", ""),
                "note": (
                    "RocksDB không có cost-based planner. "
                    "Hiệu năng phụ thuộc prefix/range có khớp leftmost key order hay không."
                ),
            }
            plan_file = RESULT_DIR / "plans" / f"{entity}_{name}_{q['id']}.json"
            plan_file.write_text(json.dumps(plan_info, indent=2, ensure_ascii=False), encoding="utf-8")

            row = {
                "timestamp": datetime.now().isoformat(),
                "engine": "rocksdb-lsm",
                "table": entity,
                "index_name": name,
                "index_label": label,
                "index_def": str(key_order),
                "query_id": q["id"],
                "query_name": q["name"],
                "plan_node": q.get("note", "prefix/range scan"),
                "plan_cost": None,
                **metrics,
            }
            results.append(row)
            print(f"p95={metrics['p95']:.2f}ms | p99={metrics['p99']:.2f}ms")

        db.close()

    csv_file = RESULT_DIR / f"{entity}_results.csv"
    if results:
        keys = list(results[0].keys())
        with csv_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(results)
        print(f"\n>>> Đã lưu: {csv_file}")

    return results


def main():
    print("=" * 80)
    print(" ROCKSDB (LSM-Tree) BENCHMARK — COMPOSITE KEY ORDER STUDY")
    print(f" users={NUM_USERS:,}  orders={NUM_ORDERS:,}  activities={NUM_ACTIVITIES:,}")
    print(f" warmup={WARMUP_RUNS}  measure={MEASURE_RUNS}")
    print(f" data_dir={DATA_DIR.resolve()}")
    print(f" result_dir={RESULT_DIR.resolve()}")
    print("=" * 80)

    all_results: List[Dict] = []
    all_results.extend(run_entity_benchmark("orders", ORDERS_INDEXES, build_orders_queries, {}))
    all_results.extend(run_entity_benchmark("users", USERS_INDEXES, build_users_queries, {}))
    all_results.extend(
        run_entity_benchmark("user_activities", ACTIVITIES_INDEXES, build_activities_queries, {})
    )

    summary = RESULT_DIR / "all_results_summary.csv"
    if all_results:
        keys = list(all_results[0].keys())
        with summary.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_results)

    print("\n" + "=" * 80)
    print(" HOÀN THÀNH BENCHMARK ROCKSDB")
    print(f" Kết quả: {summary}")
    print(f" Plans:   {RESULT_DIR / 'plans'}")
    print("=" * 80)
    print(
        "\nGợi ý báo cáo:\n"
        "- So sánh p95/p99 cùng query_id giữa PostgreSQL (B-Tree) và RocksDB (LSM).\n"
        "- Nhấn mạnh: khi leftmost prefix khớp điều kiện → LSM vẫn nhanh; "
        "khi không khớp → read amplification / scan rộng → p99 tăng mạnh.\n"
        "- RocksDB không có Execution Plan kiểu Postgres; 'plan_node' mô tả access pattern.\n"
    )


if __name__ == "__main__":
    main()
