#!/usr/bin/env python3
"""
Multi-Threaded Mixed Workload Benchmark Runner for RocksDB
Project: Empirical Study of Indexing & Key Ordering on Tail Latency
Supports:
1. YCSB Workloads (Workload C: 100R, Workload B: 95R/5W, Workload A: 50R/50W)
2. Thread Concurrency in [1, 4, 8, 16, 32]
3. 21-byte Unsigned Big-Endian Key Encodings (K_opt vs K_inv)
4. Dual Telemetry: Aggregated HdrHistogram + 1-Second Time-Series Latency Spike Monitor
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.postgres_exp.pg_runner import TimeSeriesSample


class RocksDBWorkloadRunner:
    """Executes multi-threaded YCSB-like read/write workloads against RocksDB using native C++ runner."""

    def __init__(
        self,
        base_data_dir: Optional[str | Path] = None,
    ) -> None:
        self.base_dir = str(base_data_dir or "/data/rocksdb_store")
        self.workspace_root = Path(__file__).resolve().parents[2]

    def run_benchmark(
        self,
        workload_name: str,
        key_type: str,  # k_opt or k_inv
        num_threads: int,
        warmup_seconds: int = 3,
        measure_seconds: int = 5,
    ) -> Tuple[Dict[str, Any], List[TimeSeriesSample]]:
        """
        Runs multi-threaded RocksDB benchmark under given workload and concurrency.
        """
        raw_dir = self.workspace_root / "results" / "raw_json"
        raw_dir.mkdir(parents=True, exist_ok=True)
        json_filename = f"rdb_{workload_name}_{key_type}_t{num_threads}.json"
        host_json_path = raw_dir / json_filename
        container_json_path = f"/app/results/raw_json/{json_filename}"

        db_path = f"{self.base_dir}/db_{key_type}"

        # Determine if running inside container or on host Windows
        if os.path.exists("/data/rocksdb_store"):
            # Inside Linux container
            cmd = [
                "src/rocksdb_exp/rdb_benchmark",
                "benchmark",
                db_path,
                key_type,
                workload_name,
                str(num_threads),
                str(warmup_seconds),
                str(measure_seconds),
                str(host_json_path),
            ]
            subprocess.run(cmd, cwd=self.workspace_root, check=True)
        else:
            # On host Windows, invoke Docker
            cmd = [
                "docker",
                "compose",
                "run",
                "--rm",
                "rocksdb_runner",
                "src/rocksdb_exp/rdb_benchmark",
                "benchmark",
                db_path,
                key_type,
                workload_name,
                str(num_threads),
                str(warmup_seconds),
                str(measure_seconds),
                container_json_path,
            ]
            docker_dir = self.workspace_root / "docker"
            subprocess.run(cmd, cwd=docker_dir, check=True)

        with open(host_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        ts_samples: List[TimeSeriesSample] = []
        for ts in data.get("timeseries", []):
            sample = TimeSeriesSample(
                second_idx=ts["second_idx"],
                system="RocksDB",
                workload=workload_name,
                variant=key_type,
                threads=num_threads,
                read_p50_ms=round(ts["read_p50_ms"], 4),
                read_p95_ms=round(ts["read_p95_ms"], 4),
                read_p99_ms=round(ts["read_p99_ms"], 4),
                read_ops=ts["read_ops"],
                write_ops=ts["write_ops"],
            )
            ts_samples.append(sample)

        result_row: Dict[str, Any] = {
            "system": "RocksDB",
            "workload": workload_name,
            "variant": key_type,
            "threads": num_threads,
            "elapsed_sec": data["elapsed_sec"],
            "read_ops": data["read_ops"],
            "write_ops": data["write_ops"],
            "total_throughput_ops": data["total_throughput_ops"],
            "read_throughput_ops": data["read_throughput_ops"],
            "write_throughput_ops": data["write_throughput_ops"],
            "p50_ms": data["p50_ms"],
            "p95_ms": data["p95_ms"],
            "p99_ms": data["p99_ms"],
            "p999_ms": data["p999_ms"],
            "max_ms": data["max_ms"],
            "mean_ms": data["mean_ms"],
            "stddev_ms": data["stddev_ms"],
            "variance_ms2": data["variance_ms2"],
        }
        return result_row, ts_samples
