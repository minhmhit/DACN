#!/usr/bin/env python3
"""
RocksDB Engine Management and Benchmark Invocation Interface
Project: Empirical Study of Indexing & Key Ordering on Tail Latency
Bridges Python orchestration with high-performance C++ RocksDB runner
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from src.common.config import ROCKSDB_DEFAULT_PATH


class RocksDBEngineManager:
    """Orchestrates RocksDB native runner execution via Docker or local environment."""

    def __init__(self, base_data_dir: Optional[str | Path] = None) -> None:
        self.base_dir = Path(base_data_dir or ROCKSDB_DEFAULT_PATH)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_db_path(self, key_type: str) -> Path:
        """Returns storage directory for given key configuration (k_opt or k_inv)."""
        return self.base_dir / f"db_{key_type}"

    def run_in_docker(self, cmd: str) -> subprocess.CompletedProcess[str]:
        """Runs a shell command inside the indexing-rocksdb-runner container."""
        full_cmd = [
            "docker",
            "compose",
            "run",
            "--rm",
            "rocksdb_runner",
            "bash",
            "-c",
            cmd,
        ]
        docker_dir = Path(__file__).resolve().parents[2] / "docker"
        return subprocess.run(
            full_cmd, cwd=docker_dir, capture_output=True, text=True, check=True
        )

    def bulk_load(
        self,
        key_type: str,
        num_rows: int = 500_000,
        mode: str = "uncorrelated",
    ) -> str:
        """Invokes native C++ runner to bulk-load data into RocksDB."""
        db_path = f"/data/rocksdb_store/db_{key_type}"
        cmd = (
            f"rm -rf {db_path} && "
            f"src/rocksdb_exp/rdb_benchmark load {db_path} {key_type} {num_rows} {mode}"
        )
        print(f"[rdb_engine] Executing bulk load ({key_type}, {num_rows:,} rows)...")
        proc = self.run_in_docker(cmd)
        print(proc.stdout)
        return proc.stdout

    def run_queries(
        self,
        key_type: str,
        num_queries: int = 1_000,
        distribution: str = "zipfian",
        output_json_path: str = "results/raw_json/rocksdb_perf_tmp.json",
    ) -> Dict[str, Any]:
        """Executes read queries and extracts PerfContext & Latency telemetry."""
        db_path = f"/data/rocksdb_store/db_{key_type}"
        docker_json = f"/app/{output_json_path}"
        cmd = (
            f"src/rocksdb_exp/rdb_benchmark query {db_path} {key_type} {num_queries} "
            f"{distribution} {docker_json}"
        )
        print(f"[rdb_engine] Executing {num_queries:,} queries on {key_type} ({distribution})...")
        proc = self.run_in_docker(cmd)
        print(proc.stdout)

        # Read output JSON
        host_json_path = Path(__file__).resolve().parents[2] / output_json_path
        with open(host_json_path, "r", encoding="utf-8") as f:
            return json.load(f)
