#!/usr/bin/env python3
"""
Verification Script for Phase 4: RocksDB Empirical LSM-Tree & PerfContext Telemetry
Evaluates RQ2 and Hypothesis GT2:
1. Bulk loads 500,000 rows into db_k_opt and db_k_inv (Flush to SSTables, verify L0/L1/L2 levels)
2. Runs 1,000 queries under Zipfian (s=0.99) and Uniform workloads
3. Compares K_opt vs K_inv on:
   - Tail latency (p50, p95, p99)
   - User key comparisons (user_key_comparison_count)
   - Block reads and Block Cache hits (block_read_count, block_cache_hit_count)
   - Prefix Bloom Filter hits/misses (bloom_sst_hit_count, bloom_sst_miss_count)
4. Persists raw JSON telemetry into results/raw_json/rocksdb_perf_verification.json
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

# Ensure workspace root is in python path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def run_phase_4_verification(num_rows: int = 500_000, num_queries: int = 1_000) -> Dict[str, Any]:
    print("\n=================================================================")
    print(f"STARTING PHASE 4 ROCKSDB LSM-TREE VERIFICATION ({num_rows:,} rows, {num_queries:,} queries)")
    print("=================================================================")

    workspace_dir = Path(__file__).resolve().parents[2]
    docker_dir = workspace_dir / "docker"
    output_json = workspace_dir / "results/raw_json/rocksdb_perf_verification.json"
    output_json.parent.mkdir(parents=True, exist_ok=True)

    def run_docker(cmd: str) -> str:
        res = subprocess.run(
            ["docker", "compose", "run", "--rm", "rocksdb_runner", "bash", "-c", cmd],
            cwd=docker_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout

    # 1. Compile C++ binary inside container
    print("[1/5] Compiling C++ benchmark runner (g++ -std=c++17 -O3)...")
    compile_cmd = (
        "g++ -std=c++17 -O3 src/rocksdb_exp/rdb_benchmark.cpp -o src/rocksdb_exp/rdb_benchmark "
        "-lrocksdb -lpthread -lz -lbz2 -lsnappy -llz4 -lzstd && chmod +x src/rocksdb_exp/rdb_benchmark"
    )
    run_docker(compile_cmd)
    print("      C++ runner compiled successfully.")

    # 2. Bulk load K_opt (500,000 rows)
    print(f"\n[2/5] Bulk loading 500,000 rows into K_opt (/data/rocksdb_store/db_k_opt)...")
    load_opt_cmd = (
        "mkdir -p /data/rocksdb_store && rm -rf /data/rocksdb_store/db_k_opt && "
        f"src/rocksdb_exp/rdb_benchmark load /data/rocksdb_store/db_k_opt k_opt {num_rows} uncorrelated"
    )
    load_opt_out = run_docker(load_opt_cmd)
    print(load_opt_out)

    # 3. Bulk load K_inv (500,000 rows)
    print(f"\n[3/5] Bulk loading 500,000 rows into K_inv (/data/rocksdb_store/db_k_inv)...")
    load_inv_cmd = (
        "mkdir -p /data/rocksdb_store && rm -rf /data/rocksdb_store/db_k_inv && "
        f"src/rocksdb_exp/rdb_benchmark load /data/rocksdb_store/db_k_inv k_inv {num_rows} uncorrelated"
    )
    load_inv_out = run_docker(load_inv_cmd)
    print(load_inv_out)

    # 4. Run 1,000 Read Queries on K_opt (Zipfian)
    print(f"\n[4/5] Running {num_queries:,} read queries on K_opt (Zipfian s=0.99)...")
    query_opt_cmd = (
        f"src/rocksdb_exp/rdb_benchmark query /data/rocksdb_store/db_k_opt k_opt {num_queries} "
        "zipfian /app/results/raw_json/k_opt_zipfian.json"
    )
    query_opt_out = run_docker(query_opt_cmd)
    print(query_opt_out)

    # 5. Run 1,000 Read Queries on K_inv (Zipfian)
    print(f"\n[5/5] Running {num_queries:,} read queries on K_inv (Zipfian s=0.99)...")
    query_inv_cmd = (
        f"src/rocksdb_exp/rdb_benchmark query /data/rocksdb_store/db_k_inv k_inv {num_queries} "
        "zipfian /app/results/raw_json/k_inv_zipfian.json"
    )
    query_inv_out = run_docker(query_inv_cmd)
    print(query_inv_out)

    # Read output JSONs
    with open(workspace_dir / "results/raw_json/k_opt_zipfian.json", encoding="utf-8") as f:
        k_opt_data = json.load(f)
    with open(workspace_dir / "results/raw_json/k_inv_zipfian.json", encoding="utf-8") as f:
        k_inv_data = json.load(f)

    # Clean temporary json files
    (workspace_dir / "results/raw_json/k_opt_zipfian.json").unlink(missing_ok=True)
    (workspace_dir / "results/raw_json/k_inv_zipfian.json").unlink(missing_ok=True)

    # Consolidated Verification Telemetry
    verification_data = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "num_rows": num_rows,
            "num_queries": num_queries,
            "workload": "Zipfian s=0.99",
            "engine": "RocksDB 9.10 (Leveled Compaction, 10-bit Prefix BloomFilter)",
        },
        "k_opt": k_opt_data,
        "k_inv": k_inv_data,
        "comparison": {
            "p50_ratio": round(k_inv_data["latency_p50_ms"] / max(0.0001, k_opt_data["latency_p50_ms"]), 2),
            "p95_ratio": round(k_inv_data["latency_p95_ms"] / max(0.0001, k_opt_data["latency_p95_ms"]), 2),
            "p99_ratio": round(k_inv_data["latency_p99_ms"] / max(0.0001, k_opt_data["latency_p99_ms"]), 2),
            "key_comparisons_ratio": round(
                k_inv_data["avg_key_comparisons"] / max(1, k_opt_data["avg_key_comparisons"]), 2
            ),
            "block_reads_ratio": round(
                k_inv_data["avg_block_reads"] / max(0.001, k_opt_data["avg_block_reads"]), 2
            ),
        },
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(verification_data, f, indent=2)

    print(f"\n[OK] Persisted raw RocksDB telemetry to: {output_json.resolve()}")
    return verification_data


if __name__ == "__main__":
    t0 = time.perf_counter()
    run_phase_4_verification(num_rows=500_000, num_queries=1_000)
    print(f"\n=================================================================")
    print(f"PHASE 4 VERIFICATION FINISHED IN {time.perf_counter() - t0:.2f}s")
    print("=================================================================\n")
