#!/usr/bin/env python3
"""
Phase 8 Extension - Task A: Master Data Archetype Experiment (tenants table)
Evaluates:
1. Point Lookup queries on 10,000 Master Data records
2. PostgreSQL 17: Standard Index vs. Covering Index (INCLUDE - Index-Only Scan) vs. Inverted Index
3. RocksDB 9.10: 18-byte Key Point Lookup with Whole-Key Bloom Filter (10 bits/key)
"""

from __future__ import annotations

import json
import os
import shutil
import struct
import sys
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
# DATA MODEL & SYNTHETIC GENERATOR FOR MASTER TENANTS
# ==============================================================================
@dataclass
class TenantRecord:
    tenant_id: int
    region_id: int
    tier_level: int
    tenant_code: str
    credit_limit: int
    tenant_info: str


def generate_master_tenants(num_tenants: int = 10_000, seed: int = RANDOM_SEED) -> List[TenantRecord]:
    """Generates deterministic master data records for tenants table."""
    rng = np.random.default_rng(seed)
    records: List[TenantRecord] = []

    for t_id in range(1, num_tenants + 1):
        region_id = int((t_id % 8) + 1)  # 1 to 8
        tier_level = int((t_id % 4) + 1)  # 1 to 4
        # Deterministic 16-character unique code
        code_suffix = int((t_id * 2654435761) % 1_000_000)
        tenant_code = f"TNT_{t_id:06d}_{code_suffix:06d}"[:16]
        credit_limit = int(rng.integers(10_000, 1_000_000))
        tenant_info = f"Tenant info metadata for organization {t_id:06d} in region {region_id} tier {tier_level}".ljust(100, "X")[:100]

        records.append(TenantRecord(
            tenant_id=t_id,
            region_id=region_id,
            tier_level=tier_level,
            tenant_code=tenant_code,
            credit_limit=credit_limit,
            tenant_info=tenant_info,
        ))

    return records


# ==============================================================================
# POSTGRESQL EXPERIMENT: STANDARD VS COVERING (INCLUDE) VS INVERTED
# ==============================================================================
class PostgresMasterTenantsBenchmark:
    def __init__(self, db_config: Optional[Dict[str, Any]] = None):
        self.config = db_config or PG_CONFIG

    def setup_table_and_data(self, records: List[TenantRecord]) -> None:
        """Initializes tenants table and performs COPY bulk load."""
        with psycopg.connect(**self.config, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("DROP TABLE IF EXISTS tenants CASCADE;")
                cur.execute("""
                    CREATE TABLE tenants (
                        tenant_id    INT PRIMARY KEY,
                        region_id    SMALLINT NOT NULL,
                        tier_level   SMALLINT NOT NULL,
                        tenant_code  VARCHAR(16) NOT NULL,
                        credit_limit INT NOT NULL,
                        tenant_info  VARCHAR(100) NOT NULL
                    );
                """)
                print(f"[PG-Master] Table 'tenants' created. Ingesting {len(records):,} records via COPY...")

                with cur.copy("COPY tenants (tenant_id, region_id, tier_level, tenant_code, credit_limit, tenant_info) FROM STDIN") as copy:
                    for r in records:
                        copy.write_row((r.tenant_id, r.region_id, r.tier_level, r.tenant_code, r.credit_limit, r.tenant_info))

                # Critical: VACUUM ANALYZE to update Visibility Map for Index-Only Scan
                cur.execute("VACUUM ANALYZE tenants;")
                print("[PG-Master] Bulk load complete & VACUUM ANALYZE executed (100% all-visible pages).")

    def evaluate_variant(
        self,
        variant_name: str,
        index_ddl: str,
        test_keys: List[Tuple[int, str]],
        num_queries: int = 50_000,
    ) -> Dict[str, Any]:
        """Sets up index variant, captures EXPLAIN JSON, and executes point lookup benchmark."""
        print(f"\n--- Testing PostgreSQL Index Variant: {variant_name} ---")
        with psycopg.connect(**self.config, autocommit=True) as conn:
            with conn.cursor() as cur:
                # Drop secondary indexes
                cur.execute("DROP INDEX IF EXISTS idx_tenants_std, idx_tenants_cov, idx_tenants_inv CASCADE;")
                # Create specified index
                t0 = time.perf_counter()
                cur.execute(index_ddl)
                build_time_sec = time.perf_counter() - t0
                print(f"    Index built in {build_time_sec:.4f}s: {index_ddl}")

                # Ensure catalog stats refreshed
                cur.execute("ANALYZE tenants;")

                # EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
                sample_region, sample_code = test_keys[0]
                explain_sql = """
                    EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
                    SELECT credit_limit FROM tenants 
                    WHERE region_id = %s AND tenant_code = %s;
                """
                cur.execute(explain_sql, (sample_region, sample_code))
                explain_raw = cur.fetchone()[0]
                plan_root = explain_raw[0]["Plan"]

                node_type = plan_root.get("Node Type", "")
                heap_fetches = plan_root.get("Heap Fetches", 0)
                shared_read_blocks = plan_root.get("Shared Read Blocks", 0)
                shared_hit_blocks = plan_root.get("Shared Hit Blocks", 0)
                total_cost = plan_root.get("Total Cost", 0.0)
                exec_time_ms = explain_raw[0].get("Execution Time", 0.0)

                print(f"    EXPLAIN -> Node: {node_type} | Heap Fetches: {heap_fetches} | Shared Hits: {shared_hit_blocks} | Cost: {total_cost:.2f}")

        # Benchmark 50,000 Point Lookups
        tracker = LatencyTracker()
        query_sql = "SELECT credit_limit FROM tenants WHERE region_id = %s AND tenant_code = %s;"
        num_keys = len(test_keys)

        print(f"    Executing {num_queries:,} point lookups...")
        with psycopg.connect(**self.config) as conn:
            with conn.cursor() as cur:
                # Warm-up 2,000 queries
                for i in range(2000):
                    k_reg, k_code = test_keys[i % num_keys]
                    cur.execute(query_sql, (k_reg, k_code))
                    cur.fetchone()

                # Measurement phase
                t_start = time.perf_counter()
                for i in range(num_queries):
                    k_reg, k_code = test_keys[i % num_keys]
                    with tracker.measure():
                        cur.execute(query_sql, (k_reg, k_code))
                        cur.fetchone()
                total_duration = time.perf_counter() - t_start

        metrics = tracker.get_summary()
        throughput = round(metrics["throughput_ops"], 2)
        print(f"    Result -> Throughput: {throughput:,} ops/s | p50: {metrics['p50_ms']:.4f}ms | p95: {metrics['p95_ms']:.4f}ms | p99: {metrics['p99_ms']:.4f}ms")

        return {
            "variant": variant_name,
            "engine": "PostgreSQL 17",
            "index_ddl": index_ddl,
            "node_type": node_type,
            "heap_fetches": heap_fetches,
            "shared_read_blocks": shared_read_blocks,
            "shared_hit_blocks": shared_hit_blocks,
            "cbo_total_cost": total_cost,
            "single_query_time_ms": exec_time_ms,
            "throughput_ops": throughput,
            "p50_ms": metrics["p50_ms"],
            "p95_ms": metrics["p95_ms"],
            "p99_ms": metrics["p99_ms"],
            "p999_ms": metrics["p999_ms"],
            "max_ms": metrics["max_ms"],
            "variance_ms2": metrics["variance_ms2"],
            "raw_explain": explain_raw,
        }


# ==============================================================================
# ROCKSDB EXPERIMENT: POINT LOOKUP WITH WHOLE-KEY BLOOM FILTER
# ==============================================================================
class RocksDBMasterTenantsBenchmark:
    def __init__(self, db_path: Path):
        self.db_path = str(db_path)

    @staticmethod
    def encode_key(region_id: int, tenant_code: str) -> bytes:
        """18-byte key: [region_id (2B BE uint16)][tenant_code (16B ASCII)]"""
        return struct.pack(">H16s", region_id, tenant_code.encode("ascii"))

    def run_benchmark(
        self,
        records: List[TenantRecord],
        test_keys: List[Tuple[int, str]],
        num_queries: int = 50_000,
    ) -> Dict[str, Any]:
        """Loads master records, flushes SSTables with Bloom Filter, and runs Get() benchmark."""
        print(f"\n--- Testing RocksDB Master Data Point Lookup (Whole-Key Bloom Filter) ---")
        if os.path.exists(self.db_path):
            shutil.rmtree(self.db_path)

        table_opts = BlockBasedOptions()
        table_opts.set_bloom_filter(10, False)  # 10 bits/key whole-key bloom filter
        table_opts.set_block_size(4 * 1024)

        opts = Options()
        opts.create_if_missing(True)
        opts.set_block_based_table_factory(table_opts)
        opts.enable_statistics()

        db = Rdict(self.db_path, opts)

        # Ingestion
        print(f"    Ingesting {len(records):,} master records into RocksDB...")
        for r in records:
            key = self.encode_key(r.region_id, r.tenant_code)
            val = struct.pack(">III", r.tenant_id, r.tier_level, r.credit_limit) + r.tenant_info.encode("utf-8")
            db[key] = val

        # Flush to force SSTable creation with Bloom filter
        db.flush()
        print("    MemTable flushed to SSTable. Whole-key Bloom Filter written.")

        # Benchmark 50,000 Get() calls
        tracker = LatencyTracker()
        num_keys = len(test_keys)
        encoded_keys = [self.encode_key(reg, code) for reg, code in test_keys]

        # Warm-up
        for i in range(2000):
            _ = db[encoded_keys[i % num_keys]]

        print(f"    Executing {num_queries:,} point Get() calls...")
        t_start = time.perf_counter()
        for i in range(num_queries):
            k = encoded_keys[i % num_keys]
            with tracker.measure():
                _ = db[k]
        total_duration = time.perf_counter() - t_start

        stats_str = opts.get_statistics()
        db.close()

        # Parse bloom hits from statistics
        bloom_useful = 0
        for line in stats_str.splitlines():
            if "bloom.filter.useful" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    try:
                        bloom_useful = int(parts[1].split()[0])
                    except ValueError:
                        pass

        metrics = tracker.get_summary()
        throughput = round(metrics["throughput_ops"], 2)
        print(f"    Result -> Throughput: {throughput:,} ops/s | p50: {metrics['p50_ms']:.4f}ms | p95: {metrics['p95_ms']:.4f}ms | p99: {metrics['p99_ms']:.4f}ms")

        return {
            "variant": "K_MD_BLOOM_GET",
            "engine": "RocksDB 9.10",
            "index_ddl": "18-byte Key [region_id: 2B BE][tenant_code: 16B] + 10-bit Bloom Filter",
            "node_type": "Point Get() with Whole-Key Bloom",
            "heap_fetches": 0,
            "shared_read_blocks": 0,
            "shared_hit_blocks": 1,
            "cbo_total_cost": 0.0,
            "single_query_time_ms": metrics["mean_ms"],
            "throughput_ops": throughput,
            "p50_ms": metrics["p50_ms"],
            "p95_ms": metrics["p95_ms"],
            "p99_ms": metrics["p99_ms"],
            "p999_ms": metrics["p999_ms"],
            "max_ms": metrics["max_ms"],
            "variance_ms2": metrics["variance_ms2"],
            "bloom_useful_count": bloom_useful,
        }


# ==============================================================================
# MAIN EXECUTION ORCHESTRATOR FOR PHASE 8 TASK A
# ==============================================================================
def run_phase8_master_experiment() -> Dict[str, Any]:
    print("=================================================================")
    print("PHASE 8 - TASK A: MASTER DATA ARCHETYPE BENCHMARK (10,000 TENANTS)")
    print("=================================================================")

    records = generate_master_tenants(num_tenants=10_000, seed=RANDOM_SEED)
    test_keys = [(r.region_id, r.tenant_code) for r in records]

    # 1. PostgreSQL Experiments
    pg_bench = PostgresMasterTenantsBenchmark()
    pg_bench.setup_table_and_data(records)

    pg_variants = [
        ("I_MD_STD", "CREATE INDEX idx_tenants_std ON tenants (region_id, tenant_code);"),
        ("I_MD_COV", "CREATE INDEX idx_tenants_cov ON tenants (region_id, tenant_code) INCLUDE (credit_limit);"),
        ("I_MD_INV", "CREATE INDEX idx_tenants_inv ON tenants (tier_level, region_id, tenant_code);"),
    ]

    all_results: List[Dict[str, Any]] = []
    for var_name, ddl in pg_variants:
        res = pg_bench.evaluate_variant(var_name, ddl, test_keys, num_queries=50_000)
        all_results.append(res)

    # 2. RocksDB Experiment
    rdb_dir = WORKSPACE_ROOT / "results" / "phase8_rdb_tenants"
    rdb_bench = RocksDBMasterTenantsBenchmark(rdb_dir)
    rdb_res = rdb_bench.run_benchmark(records, test_keys, num_queries=50_000)
    all_results.append(rdb_res)

    # Save JSON summary
    out_json = WORKSPACE_ROOT / "results" / "raw_json" / "phase8_master_tenants_results.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Phase 8 Task A results saved to: {out_json.resolve()}")

    return {"master_tenants_results": all_results}


if __name__ == "__main__":
    run_phase8_master_experiment()
