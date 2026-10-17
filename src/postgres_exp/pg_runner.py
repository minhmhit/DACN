#!/usr/bin/env python3
"""
Multi-Threaded Mixed Workload Benchmark Runner for PostgreSQL
Project: Empirical Study of Indexing & Key Ordering on Tail Latency
Supports:
1. YCSB Workloads:
   - Workload C: 100% Read (Composite Range Query)
   - Workload B: 95% Read / 5% Write (Read-mostly OLTP)
   - Workload A: 50% Read / 50% Write (Update-heavy OLTP with Page Splits & WAL contention)
2. Concurrency Scaling: Threads in [1, 4, 8, 16, 32]
3. Phased Execution: Warm-up Phase (excluded) -> Measurement Phase
4. Dual Telemetry: Aggregated HdrHistogram + 1-Second Time-Series Latency Spike Monitor
"""

from __future__ import annotations

import csv
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import psycopg

from src.common.config import (
    BASE_TIMESTAMP_MS,
    DEFAULT_NUM_TENANTS,
    PG_CONFIG,
    WINDOW_MS,
)
from src.common.data_generator import FastZipfianGenerator
from src.common.latency_tracker import LatencyTracker


@dataclass
class TimeSeriesSample:
    second_idx: int
    system: str
    workload: str
    variant: str
    threads: int
    read_p50_ms: float
    read_p95_ms: float
    read_p99_ms: float
    read_ops: int
    write_ops: int


class PostgresWorkloadRunner:
    """Executes multi-threaded YCSB-like read/write workloads against PostgreSQL."""

    def __init__(
        self,
        db_config: Optional[Dict[str, Any]] = None,
        num_tenants: int = DEFAULT_NUM_TENANTS,
        seed: int = 42,
    ) -> None:
        self.config = db_config or PG_CONFIG
        self.num_tenants = num_tenants
        self.seed = seed
        self.zipf_gen = FastZipfianGenerator(n=num_tenants, theta=0.99, seed=seed)

        # Global atomic order_id generator for INSERT writes (queried from DB)
        self._next_order_id = 1_000_000
        self._order_id_lock = threading.Lock()
        self._init_next_order_id()

    def _init_next_order_id(self) -> None:
        try:
            with psycopg.connect(**self.config, autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COALESCE(MAX(order_id), 500000) FROM orders;")
                    row = cur.fetchone()
                    val = row[0] if row else 500000
                    self._next_order_id = val + 1000
        except Exception:
            self._next_order_id = 2_000_000

    def _get_next_order_id(self) -> int:
        with self._order_id_lock:
            oid = self._next_order_id
            self._next_order_id += 1
            return oid

    def run_benchmark(
        self,
        workload_name: str,
        index_variant: str,
        num_threads: int,
        warmup_seconds: int = 5,
        measure_seconds: int = 15,
    ) -> Tuple[Dict[str, Any], List[TimeSeriesSample]]:
        """
        Runs a single benchmark configuration with thread pool and time-series monitoring.
        """
        # Determine read/write probabilities
        if workload_name in ("Workload_C", "100_READ"):
            read_prob = 1.0
        elif workload_name in ("Workload_B", "95_READ_5_WRITE"):
            read_prob = 0.95
        elif workload_name in ("Workload_A", "50_READ_50_WRITE"):
            read_prob = 0.50
        else:
            raise ValueError(f"Unknown workload: {workload_name}")

        # Shared measurement trackers
        read_tracker = LatencyTracker()
        total_read_ops = 0
        total_write_ops = 0
        ops_lock = threading.Lock()

        # Interval statistics for time-series logging
        interval_read_latencies: List[int] = []
        interval_read_count = 0
        interval_write_count = 0
        interval_lock = threading.Lock()

        time_series: List[TimeSeriesSample] = []
        stop_signal = threading.Event()
        is_measuring = threading.Event()

        # Query templates
        read_sql = """
            SELECT order_id, tenant_id, status, created_at, amount, payload
            FROM orders
            WHERE tenant_id = %s AND status = %s AND created_at BETWEEN %s AND %s;
        """
        insert_sql = """
            INSERT INTO orders (order_id, tenant_id, status, created_at, amount, payload)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (order_id) DO NOTHING;
        """
        update_sql = """
            UPDATE orders
            SET amount = amount + %s
            WHERE order_id = %s;
        """

        def worker_loop(thread_id: int) -> None:
            nonlocal total_read_ops, total_write_ops
            nonlocal interval_read_count, interval_write_count

            # Dedicated database connection per worker
            conn = psycopg.connect(**self.config, autocommit=True)
            rng = np.random.default_rng(self.seed + thread_id * 1000 + 7)
            cur = conn.cursor()

            try:
                while not stop_signal.is_set():
                    is_read = rng.random() < read_prob

                    if is_read:
                        # Draw parameters
                        t_id = int(self.zipf_gen.next_value())
                        st = int(rng.integers(0, 5))
                        w_span = 30 * 86400 * 1000  # 30-day window
                        max_start = WINDOW_MS - w_span
                        start_ts = BASE_TIMESTAMP_MS + int(rng.integers(0, max_start))
                        end_ts = start_ts + w_span

                        t0 = time.perf_counter_ns()
                        cur.execute(read_sql, (t_id, st, start_ts, end_ts))
                        _ = cur.fetchall()
                        t1 = time.perf_counter_ns()
                        lat_ns = t1 - t0

                        if is_measuring.is_set():
                            lat_us = lat_ns // 1000
                            read_tracker.record_latency_ns(lat_ns)
                            with interval_lock:
                                interval_read_latencies.append(lat_us)
                                interval_read_count += 1
                            with ops_lock:
                                total_read_ops += 1

                    else:
                        # Write operation: 50% INSERT (Page Split & Index Update), 50% UPDATE (Heap update & WAL)
                        is_insert = rng.random() < 0.50
                        try:
                            if is_insert:
                                new_oid = self._get_next_order_id()
                                t_id = int(self.zipf_gen.next_value())
                                st = int(rng.integers(0, 5))
                                cr_at = BASE_TIMESTAMP_MS + int(rng.integers(0, WINDOW_MS))
                                amt = int(rng.integers(100, 100000))
                                payload = "X" * 100
                                cur.execute(insert_sql, (new_oid, t_id, st, cr_at, amt, payload))
                            else:
                                upd_oid = int(rng.integers(1, 500000))
                                amt_delta = int(rng.integers(1, 100))
                                cur.execute(update_sql, (amt_delta, upd_oid))
                        except Exception:
                            continue

                        if is_measuring.is_set():
                            with interval_lock:
                                interval_write_count += 1
                            with ops_lock:
                                total_write_ops += 1

            finally:
                cur.close()
                conn.close()

        def time_series_monitor() -> None:
            nonlocal interval_read_count, interval_write_count, interval_read_latencies
            second_counter = 0

            while not stop_signal.is_set():
                time.sleep(1.0)
                if not is_measuring.is_set():
                    continue

                second_counter += 1
                with interval_lock:
                    r_count = interval_read_count
                    w_count = interval_write_count
                    lats = list(interval_read_latencies)
                    interval_read_count = 0
                    interval_write_count = 0
                    interval_read_latencies.clear()

                if lats:
                    lats.sort()
                    p50 = np.percentile(lats, 50) / 1000.0
                    p95 = np.percentile(lats, 95) / 1000.0
                    p99 = np.percentile(lats, 99) / 1000.0
                else:
                    p50 = p95 = p99 = 0.0

                sample = TimeSeriesSample(
                    second_idx=second_counter,
                    system="PostgreSQL",
                    workload=workload_name,
                    variant=index_variant,
                    threads=num_threads,
                    read_p50_ms=round(p50, 4),
                    read_p95_ms=round(p95, 4),
                    read_p99_ms=round(p99, 4),
                    read_ops=r_count,
                    write_ops=w_count,
                )
                time_series.append(sample)

        # Launch workers and monitor
        workers = [
            threading.Thread(target=worker_loop, args=(i,), daemon=True)
            for i in range(num_threads)
        ]
        monitor = threading.Thread(target=time_series_monitor, daemon=True)

        for w in workers:
            w.start()
        monitor.start()

        # 1. Warm-up Phase
        time.sleep(warmup_seconds)

        # 2. Measurement Phase
        read_tracker.start()
        is_measuring.set()
        time.sleep(measure_seconds)
        is_measuring.clear()
        read_tracker.stop()

        # Stop workers
        stop_signal.set()
        for w in workers:
            w.join(timeout=2.0)

        # Compile final summary
        summary = read_tracker.get_summary()
        elapsed_sec = summary["elapsed_seconds"]
        read_throughput = round(total_read_ops / elapsed_sec, 2)
        write_throughput = round(total_write_ops / elapsed_sec, 2)
        total_throughput = round((total_read_ops + total_write_ops) / elapsed_sec, 2)

        result_row: Dict[str, Any] = {
            "system": "PostgreSQL",
            "workload": workload_name,
            "variant": index_variant,
            "threads": num_threads,
            "elapsed_sec": elapsed_sec,
            "read_ops": total_read_ops,
            "write_ops": total_write_ops,
            "total_throughput_ops": total_throughput,
            "read_throughput_ops": read_throughput,
            "write_throughput_ops": write_throughput,
            "p50_ms": summary["p50_ms"],
            "p95_ms": summary["p95_ms"],
            "p99_ms": summary["p99_ms"],
            "p999_ms": summary["p999_ms"],
            "max_ms": summary["max_ms"],
            "mean_ms": summary["mean_ms"],
            "stddev_ms": summary["stddev_ms"],
            "variance_ms2": summary["variance_ms2"],
        }
        return result_row, time_series
