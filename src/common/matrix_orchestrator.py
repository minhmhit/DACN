#!/usr/bin/env python3
"""
Master Experimental Matrix Orchestrator
Project: Empirical Study of Indexing & Key Ordering on Tail Latency
Executes:
1. Multi-threaded Concurrency Matrix: Threads = [1, 4, 8, 16, 32]
2. YCSB Workloads:
   - Workload C: 100% Read
   - Workload B: 95% Read / 5% Write
   - Workload A: 50% Read / 50% Write (Update-heavy, Page Splits & Compaction)
3. Outputs:
   - results/summary_csv/postgres_matrix_results.csv
   - results/summary_csv/rocksdb_matrix_results.csv
   - results/summary_csv/timeseries_latency_spikes.csv
"""

from __future__ import annotations

import csv
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure workspace root is in python path
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.postgres_exp.pg_runner import PostgresWorkloadRunner, TimeSeriesSample
from src.postgres_exp.pg_schema import PostgresSchemaManager
from src.rocksdb_exp.rdb_runner import RocksDBWorkloadRunner


def save_csv(filepath: Path, rows: List[Dict[str, Any]]) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[matrix] Saved CSV table to: {filepath.resolve()}")


def load_csv(filepath: Path) -> List[Dict[str, Any]]:
    if not filepath.exists():
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_timeseries_csv(filepath: Path, samples: List[TimeSeriesSample], append: bool = False) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    if not samples:
        return
    fieldnames = [
        "second_idx",
        "system",
        "workload",
        "variant",
        "threads",
        "read_p50_ms",
        "read_p95_ms",
        "read_p99_ms",
        "read_ops",
        "write_ops",
    ]
    file_exists = filepath.exists()
    mode = "a" if (append and file_exists) else "w"
    with open(filepath, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if mode == "w":
            writer.writeheader()
        for s in samples:
            writer.writerow(s.__dict__)
    print(f"[matrix] Saved time-series logs ({len(samples)} samples) to: {filepath.resolve()}")


def run_full_matrix(
    concurrency_levels: Optional[List[int]] = None,
    warmup_sec: Optional[int] = None,
    measure_sec: Optional[int] = None,
) -> None:
    threads_list = concurrency_levels or [
        int(x)
        for x in os.environ.get("CONCURRENCY_LEVELS", "1,4,8,16,32").split(",")
    ]
    warmup = (
        warmup_sec if warmup_sec is not None else int(os.environ.get("WARMUP_SECONDS", "2"))
    )
    measure = (
        measure_sec if measure_sec is not None else int(os.environ.get("MEASURE_SECONDS", "4"))
    )

    workloads = ["Workload_C", "Workload_B", "Workload_A"]
    parser_mode = sys.argv[1] if len(sys.argv) > 1 else "--all"

    print("\n=================================================================")
    print("STARTING MULTI-THREADED EXPERIMENTAL MATRIX ORCHESTRATION")
    print(f"Mode               : {parser_mode}")
    print(f"Concurrency Levels : {threads_list}")
    print(f"Workloads          : {workloads}")
    print(f"Timing per Run     : Warm-up={warmup}s, Measurement={measure}s")
    print("=================================================================\n")

    t_total_start = time.perf_counter()
    all_timeseries: List[TimeSeriesSample] = []

    # ==========================================================================
    # 1. POSTGRESQL BENCHMARK MATRIX
    # ==========================================================================
    if parser_mode in ("--all", "--postgres-only"):
        print(">>> [PART 1/2] EXECUTING POSTGRESQL MATRIX...")
        pg_schema = PostgresSchemaManager()
        pg_runner = PostgresWorkloadRunner()
        pg_results: List[Dict[str, Any]] = []

        pg_variants = ["I_OPT", "I_INV_LOW_SEL"]

        for variant in pg_variants:
            print(f"\n#######################################################")
            print(f"Switching PostgreSQL Index Configuration to: {variant}")
            print(f"#######################################################")
            pg_schema.apply_index_variant(variant)

            for wl in workloads:
                for threads in threads_list:
                    print(
                        f"[PG] Variant: {variant:13s} | WL: {wl:10s} | Threads: {threads:2d} ... ",
                        end="",
                        flush=True,
                    )
                    res, ts = pg_runner.run_benchmark(
                        workload_name=wl,
                        index_variant=variant,
                        num_threads=threads,
                        warmup_seconds=warmup,
                        measure_seconds=measure,
                    )
                    pg_results.append(res)
                    all_timeseries.extend(ts)
                    print(
                        f"Ops: {res['total_throughput_ops']:8.1f} ops/s | p50: {res['p50_ms']:6.2f}ms | p95: {res['p95_ms']:6.2f}ms | p99: {res['p99_ms']:6.2f}ms | var: {res['variance_ms2']:8.2f}"
                    )

        save_csv(
            WORKSPACE_ROOT / "results/summary_csv/postgres_matrix_results.csv", pg_results
        )
        append_mode = (parser_mode == "--postgres-only" and (WORKSPACE_ROOT / "results/summary_csv/timeseries_latency_spikes.csv").exists())
        save_timeseries_csv(
            WORKSPACE_ROOT / "results/summary_csv/timeseries_latency_spikes.csv", all_timeseries, append=append_mode
        )

    # ==========================================================================
    # 2. ROCKSDB BENCHMARK MATRIX
    # ==========================================================================
    if parser_mode in ("--all", "--rocksdb-only"):
        print("\n>>> [PART 2/2] EXECUTING ROCKSDB MATRIX...")
        rdb_runner = RocksDBWorkloadRunner()
        rdb_results: List[Dict[str, Any]] = []
        rdb_timeseries: List[TimeSeriesSample] = []

        rdb_variants = ["k_opt", "k_inv"]

        for variant in rdb_variants:
            print(f"\n#######################################################")
            print(f"Evaluating RocksDB Key Configuration: {variant}")
            print(f"#######################################################")

            for wl in workloads:
                for threads in threads_list:
                    print(
                        f"[RDB] Variant: {variant:5s} | WL: {wl:10s} | Threads: {threads:2d} ... ",
                        end="",
                        flush=True,
                    )
                    res, ts = rdb_runner.run_benchmark(
                        workload_name=wl,
                        key_type=variant,
                        num_threads=threads,
                        warmup_seconds=warmup,
                        measure_seconds=measure,
                    )
                    rdb_results.append(res)
                    rdb_timeseries.extend(ts)
                    print(
                        f"Ops: {res['total_throughput_ops']:8.1f} ops/s | p50: {res['p50_ms']:6.3f}ms | p95: {res['p95_ms']:6.3f}ms | p99: {res['p99_ms']:6.3f}ms | var: {res['variance_ms2']:8.3f}"
                    )

        save_csv(WORKSPACE_ROOT / "results/summary_csv/rocksdb_matrix_results.csv", rdb_results)
        append_mode = (parser_mode == "--rocksdb-only" and (WORKSPACE_ROOT / "results/summary_csv/timeseries_latency_spikes.csv").exists())
        save_timeseries_csv(
            WORKSPACE_ROOT / "results/summary_csv/timeseries_latency_spikes.csv",
            rdb_timeseries,
            append=append_mode,
        )

    # ==========================================================================
    # 3. MATHEMATICAL VALIDATION & CONSISTENCY AUDIT
    # ==========================================================================
    print("\n=================================================================")
    print("AUDITING MATHEMATICAL CONSISTENCY ACROSS ALL GENERATED CSVs")
    print("=================================================================")

    pg_path = WORKSPACE_ROOT / "results/summary_csv/postgres_matrix_results.csv"
    rdb_path = WORKSPACE_ROOT / "results/summary_csv/rocksdb_matrix_results.csv"
    ts_path = WORKSPACE_ROOT / "results/summary_csv/timeseries_latency_spikes.csv"

    for name, p in [("PostgreSQL", pg_path), ("RocksDB", rdb_path)]:
        if not p.exists():
            print(f"[WARN] {p.name} not found, skipping validation.")
            continue
        data = load_csv(p)
        print(f"[{name}] Validating {len(data)} rows in {p.name}...")
        for i, row in enumerate(data):
            for k, v in row.items():
                assert v is not None and v != "" and v.lower() != "nan", f"NaN or empty value at {name} row {i}, column {k}"
            p50 = float(row["p50_ms"])
            p95 = float(row["p95_ms"])
            p99 = float(row["p99_ms"])
            p999 = float(row["p999_ms"])
            max_val = float(row["max_ms"])
            var_val = float(row["variance_ms2"])

            # Quantile monotonic property: p50 <= p95 <= p99 <= p999 <= max
            assert (
                p50 <= p95 + 1e-4 <= p99 + 2e-4 <= p999 + 3e-4 <= max_val + 1e-3
            ), f"Percentile monotonicity violated in {name} row {i}: {row}"
            # Variance non-negative
            assert var_val >= 0.0, f"Negative variance found: {var_val} in row {i}"

        print(f"[OK] {name}: 100% rows satisfy monotonicity (p50 <= p95 <= p99 <= p999 <= max) and non-negative variance.")

    if ts_path.exists():
        ts_data = load_csv(ts_path)
        print(f"[TimeSeries] Validating {len(ts_data)} samples in {ts_path.name}...")
        for i, row in enumerate(ts_data):
            for k, v in row.items():
                assert v is not None and v != "" and v.lower() != "nan", f"NaN in time-series row {i}, col {k}"
            p50 = float(row["read_p50_ms"])
            p95 = float(row["read_p95_ms"])
            p99 = float(row["read_p99_ms"])
            assert p50 <= p95 + 1e-4 <= p99 + 1e-4, f"Time-series percentile violation at row {i}: {row}"
        print(f"[OK] TimeSeries: 100% of {len(ts_data)} samples mathematically valid.")

    print(
        f"\n[OK] Matrix orchestration completed successfully in {time.perf_counter() - t_total_start:.2f} seconds."
    )


if __name__ == "__main__":
    run_full_matrix()
