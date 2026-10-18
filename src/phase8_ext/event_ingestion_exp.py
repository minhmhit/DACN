#!/usr/bin/env python3
"""
Phase 8 Extension - Task B: Event Log Archetype Experiment (order_events table)
Evaluates:
1. 100% Append-Only Ingestion Workload (500,000 events)
2. Compares PostgreSQL B-Tree vs RocksDB LSM-Tree under two key orderings:
   - TIME_LEAD (event_ts, tenant_id): Right-most leaf append vs Sequential monotonic keys
   - TENANT_LEAD (tenant_id, event_ts): Random B-Tree leaf page split & WAL Full-Page Image explosion
3. Concurrency levels: Threads in [1, 8, 16]
4. Metrics: Ingestion Throughput (inserts/s), Write Latency (p50, p95, p99), WAL Bytes, Index Size.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import struct
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import psycopg
from psycopg import sql

# Ensure workspace root is in python path
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from rocksdict import BlockBasedOptions, Options, Rdict

from src.common.config import PG_CONFIG, RANDOM_SEED
from src.common.latency_tracker import LatencyTracker


# ==============================================================================
# DATA MODEL FOR EVENT LOG
# ==============================================================================
@dataclass
class EventRecord:
    event_id: int
    event_ts: int
    tenant_id: int
    event_type: int
    payload: str


def generate_event_stream(num_events: int = 100_000, seed: int = RANDOM_SEED) -> List[EventRecord]:
    """Generates deterministic monotonic event stream."""
    rng = np.random.default_rng(seed)
    base_ts = 1704067200000  # 2024-01-01 00:00:00 UTC
    events: List[EventRecord] = []

    for i in range(1, num_events + 1):
        # Monotonically increasing timestamp
        ts = base_ts + (i * 10)  # every 10ms
        # Random tenant_id (uniform across 10,000 tenants)
        tenant_id = int(rng.integers(1, 10_001))
        event_type = int(rng.integers(1, 10))
        payload = f"Event_{i:08d}_payload_audit_metadata_stream".ljust(100, "Z")[:100]

        events.append(EventRecord(
            event_id=i,
            event_ts=ts,
            tenant_id=tenant_id,
            event_type=event_type,
            payload=payload,
        ))

    return events


# ==============================================================================
# POSTGRESQL EVENT INGESTION BENCHMARK
# ==============================================================================
class PostgresEventIngestionBenchmark:
    def __init__(self, db_config: Optional[Dict[str, Any]] = None):
        self.config = db_config or PG_CONFIG

    def get_wal_stats(self) -> Dict[str, int]:
        with psycopg.connect(**self.config) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT wal_records, wal_fpi, wal_bytes FROM pg_stat_wal;")
                row = cur.fetchone()
                return {
                    "wal_records": int(row[0] or 0),
                    "wal_fpi": int(row[1] or 0),  # Full-Page Images
                    "wal_bytes": int(row[2] or 0),
                }

    def setup_events_table(self, ordering: str) -> str:
        """Initializes order_events table and creates specified index variant."""
        with psycopg.connect(**self.config, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("DROP TABLE IF EXISTS order_events CASCADE;")
                cur.execute("""
                    CREATE TABLE order_events (
                        event_id   BIGINT NOT NULL,
                        event_ts   BIGINT NOT NULL,
                        tenant_id  INT NOT NULL,
                        event_type SMALLINT NOT NULL,
                        payload    VARCHAR(100) NOT NULL
                    );
                """)
                if ordering == "TIME_LEAD":
                    idx_name = "idx_events_time"
                    cur.execute(f"CREATE INDEX {idx_name} ON order_events (event_ts, tenant_id);")
                else:  # TENANT_LEAD
                    idx_name = "idx_events_tenant"
                    cur.execute(f"CREATE INDEX {idx_name} ON order_events (tenant_id, event_ts);")
                print(f"[PG-Events] Table initialized with index: {idx_name} ({ordering})")
                return idx_name

    def run_ingestion(
        self,
        events: List[EventRecord],
        ordering: str,
        num_threads: int,
    ) -> Dict[str, Any]:
        idx_name = self.setup_events_table(ordering)

        wal_before = self.get_wal_stats()
        tracker = LatencyTracker()
        num_events = len(events)
        chunk_size = num_events // num_threads

        batch_size = 100
        def worker_task(chunk: List[EventRecord]) -> None:
            insert_sql = "INSERT INTO order_events (event_id, event_ts, tenant_id, event_type, payload) VALUES (%s, %s, %s, %s, %s);"
            with psycopg.connect(**self.config) as conn:
                with conn.cursor() as cur:
                    for i, ev in enumerate(chunk):
                        with tracker.measure():
                            cur.execute(insert_sql, (ev.event_id, ev.event_ts, ev.tenant_id, ev.event_type, ev.payload))
                        if (i + 1) % batch_size == 0 or (i + 1) == len(chunk):
                            conn.commit()

        threads: List[threading.Thread] = []
        for t_idx in range(num_threads):
            start_i = t_idx * chunk_size
            end_i = start_i + chunk_size if t_idx < num_threads - 1 else num_events
            th = threading.Thread(target=worker_task, args=(events[start_i:end_i],))
            threads.append(th)

        print(f"    [Postgres] Ingesting {num_events:,} events with {num_threads} threads ({ordering})...")
        t_start = time.perf_counter()
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        total_duration = time.perf_counter() - t_start

        wal_after = self.get_wal_stats()
        delta_wal_bytes = max(0, wal_after["wal_bytes"] - wal_before["wal_bytes"])
        delta_wal_fpi = max(0, wal_after["wal_fpi"] - wal_before["wal_fpi"])

        # Query index size
        with psycopg.connect(**self.config) as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT pg_relation_size('{idx_name}');")
                idx_size_bytes = int(cur.fetchone()[0])

        metrics = tracker.get_summary()
        throughput = round(metrics["throughput_ops"], 2)
        print(f"    [Postgres Result] Throughput: {throughput:,} inserts/s | p50: {metrics['p50_ms']:.3f}ms | p99: {metrics['p99_ms']:.3f}ms | WAL: {delta_wal_bytes/(1024*1024):.2f}MB | FPI: {delta_wal_fpi:,}")

        return {
            "system": "PostgreSQL 17",
            "archetype": "Loại 3: Event Log",
            "variant": ordering,
            "threads": num_threads,
            "total_records": num_events,
            "duration_sec": round(total_duration, 3),
            "throughput_ops": throughput,
            "p50_ms": metrics["p50_ms"],
            "p95_ms": metrics["p95_ms"],
            "p99_ms": metrics["p99_ms"],
            "p999_ms": metrics["p999_ms"],
            "max_ms": metrics["max_ms"],
            "variance_ms2": metrics["variance_ms2"],
            "wal_bytes": delta_wal_bytes,
            "wal_fpi": delta_wal_fpi,
            "index_size_bytes": idx_size_bytes,
        }


# ==============================================================================
# ROCKSDB EVENT INGESTION BENCHMARK
# ==============================================================================
class RocksDBEventIngestionBenchmark:
    def __init__(self, db_base_dir: Path):
        self.base_dir = db_base_dir

    @staticmethod
    def encode_key(ordering: str, ev: EventRecord) -> bytes:
        if ordering == "TIME_LEAD":
            # [event_ts: 8B uint64 BE][tenant_id: 4B uint32 BE][event_id: 8B uint64 BE] = 20 Bytes
            return struct.pack(">QIQ", ev.event_ts, ev.tenant_id, ev.event_id)
        else:  # TENANT_LEAD
            # [tenant_id: 4B uint32 BE][event_ts: 8B uint64 BE][event_id: 8B uint64 BE] = 20 Bytes
            return struct.pack(">IQQ", ev.tenant_id, ev.event_ts, ev.event_id)

    def run_ingestion(
        self,
        events: List[EventRecord],
        ordering: str,
        num_threads: int,
    ) -> Dict[str, Any]:
        db_path = str(self.base_dir / f"db_events_{ordering}_t{num_threads}")
        if os.path.exists(db_path):
            shutil.rmtree(db_path)

        table_opts = BlockBasedOptions()
        table_opts.set_block_size(4 * 1024)

        opts = Options()
        opts.create_if_missing(True)
        opts.set_block_based_table_factory(table_opts)
        opts.set_write_buffer_size(64 * 1024 * 1024)  # 64MB MemTable
        opts.enable_statistics()

        db = Rdict(db_path, opts)

        tracker = LatencyTracker()
        num_events = len(events)
        chunk_size = num_events // num_threads

        def worker_task(chunk: List[EventRecord]) -> None:
            for ev in chunk:
                key = self.encode_key(ordering, ev)
                val = struct.pack(">H", ev.event_type) + ev.payload.encode("utf-8")
                with tracker.measure():
                    db[key] = val

        threads: List[threading.Thread] = []
        for t_idx in range(num_threads):
            start_i = t_idx * chunk_size
            end_i = start_i + chunk_size if t_idx < num_threads - 1 else num_events
            th = threading.Thread(target=worker_task, args=(events[start_i:end_i],))
            threads.append(th)

        print(f"    [RocksDB] Ingesting {num_events:,} events with {num_threads} threads ({ordering})...")
        t_start = time.perf_counter()
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        total_duration = time.perf_counter() - t_start

        # Flush to get accurate on-disk size
        db.flush()
        db.close()

        # Calculate on-disk storage size
        total_disk_bytes = sum(f.stat().st_size for f in Path(db_path).glob("*") if f.is_file())

        metrics = tracker.get_summary()
        throughput = round(metrics["throughput_ops"], 2)
        print(f"    [RocksDB Result] Throughput: {throughput:,} inserts/s | p50: {metrics['p50_ms']:.3f}ms | p99: {metrics['p99_ms']:.3f}ms | Disk Size: {total_disk_bytes/(1024*1024):.2f}MB")

        return {
            "system": "RocksDB 9.10",
            "archetype": "Loại 3: Event Log",
            "variant": ordering,
            "threads": num_threads,
            "total_records": num_events,
            "duration_sec": round(total_duration, 3),
            "throughput_ops": throughput,
            "p50_ms": metrics["p50_ms"],
            "p95_ms": metrics["p95_ms"],
            "p99_ms": metrics["p99_ms"],
            "p999_ms": metrics["p999_ms"],
            "max_ms": metrics["max_ms"],
            "variance_ms2": metrics["variance_ms2"],
            "wal_bytes": total_disk_bytes,  # Total persisted bytes
            "wal_fpi": 0,                   # RocksDB uses Append-only WAL (No Full-Page Images)
            "index_size_bytes": total_disk_bytes,
        }


# ==============================================================================
# MAIN EXECUTION ORCHESTRATOR FOR PHASE 8 TASK B & MASTER AGGREGATION
# ==============================================================================
def run_phase8_event_experiment() -> Dict[str, Any]:
    print("\n=================================================================")
    print("PHASE 8 - TASK B: EVENT LOG INGESTION BENCHMARK (order_events)")
    print("=================================================================")

    # 100,000 events for crisp multi-threaded runs
    events = generate_event_stream(num_events=100_000, seed=RANDOM_SEED)

    pg_bench = PostgresEventIngestionBenchmark()
    rdb_dir = WORKSPACE_ROOT / "results" / "phase8_rdb_events"
    rdb_dir.mkdir(parents=True, exist_ok=True)
    rdb_bench = RocksDBEventIngestionBenchmark(rdb_dir)

    all_event_results: List[Dict[str, Any]] = []
    concurrency_levels = [1, 8, 16]

    for ordering in ["TIME_LEAD", "TENANT_LEAD"]:
        for th in concurrency_levels:
            # 1. PostgreSQL Run
            pg_res = pg_bench.run_ingestion(events, ordering, th)
            all_event_results.append(pg_res)

            # 2. RocksDB Run
            rdb_res = rdb_bench.run_ingestion(events, ordering, th)
            all_event_results.append(rdb_res)

    # Save JSON
    out_json = WORKSPACE_ROOT / "results" / "raw_json" / "phase8_event_ingestion_results.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_event_results, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Phase 8 Task B results saved to: {out_json.resolve()}")

    # ==========================================================================
    # COMBINE MASTER TENANTS (TASK A) & EVENT LOG (TASK B) INTO SUMMARY CSV
    # ==========================================================================
    master_json_path = WORKSPACE_ROOT / "results" / "raw_json" / "phase8_master_tenants_results.json"
    master_data: List[Dict[str, Any]] = []
    if master_json_path.exists():
        with open(master_json_path, "r", encoding="utf-8") as f:
            master_data = json.load(f)

    summary_rows: List[Dict[str, Any]] = []
    for m in master_data:
        summary_rows.append({
            "archetype": "Loại 2: Master Data",
            "system": m["engine"],
            "variant": m["variant"],
            "threads": 1,
            "operation": m["node_type"],
            "throughput_ops": m["throughput_ops"],
            "p50_ms": m["p50_ms"],
            "p95_ms": m["p95_ms"],
            "p99_ms": m["p99_ms"],
            "p999_ms": m["p999_ms"],
            "max_ms": m["max_ms"],
            "variance_ms2": m["variance_ms2"],
            "heap_fetches": 0 if m["variant"] == "I_MD_COV" or "RocksDB" in m["engine"] else 1,
            "shared_read_blocks": m["shared_read_blocks"],
            "shared_hit_blocks": m["shared_hit_blocks"],
            "wal_or_disk_bytes": 0,
        })

    for e in all_event_results:
        summary_rows.append({
            "archetype": e["archetype"],
            "system": e["system"],
            "variant": e["variant"],
            "threads": e["threads"],
            "operation": f"100% Insert Ingestion ({e['variant']})",
            "throughput_ops": e["throughput_ops"],
            "p50_ms": e["p50_ms"],
            "p95_ms": e["p95_ms"],
            "p99_ms": e["p99_ms"],
            "p999_ms": e["p999_ms"],
            "max_ms": e["max_ms"],
            "variance_ms2": e["variance_ms2"],
            "heap_fetches": 0,
            "shared_read_blocks": 0,
            "shared_hit_blocks": 0,
            "wal_or_disk_bytes": e["wal_bytes"],
        })

    summary_csv = WORKSPACE_ROOT / "results" / "summary_csv" / "phase8_master_and_events.csv"
    summary_csv.parent.mkdir(parents=True, exist_ok=True)
    if summary_rows:
        fieldnames = list(summary_rows[0].keys())
        with open(summary_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(summary_rows)
        print(f"[OK] Master & Events summary CSV written: {summary_csv.resolve()}")

    return {"event_ingestion_results": all_event_results}


if __name__ == "__main__":
    run_phase8_event_experiment()
