#!/usr/bin/env python3
"""
Verification Script for Phase 3: PostgreSQL Empirical B-Tree & EXPLAIN Pipeline
Evaluates RQ1, RQ3 and Hypotheses GT1, GT3:
1. Bulk loads 500,000 rows for DIST_CLUSTERED (r ≈ 1.0) and DIST_UNCORRELATED (r ≈ 0.0)
2. Compares index variants (I_NONE, I_OPT, I_INV_LOW_SEL, I_INV_SKIP_LEAD)
3. Evaluates work_mem constraint (4MB vs 64kB) triggering Exact -> Lossy Bitmap Heap Scan transition
4. Saves full raw diagnostic telemetry to results/raw_json/pg_explain_verification.json
"""

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure workspace root is in python path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.common.config import (
    BASE_TIMESTAMP_MS,
    DEFAULT_NUM_TENANTS,
    WINDOW_MS,
    DataDistributionMode,
)
from src.postgres_exp.pg_explain import PostgresExplainRunner
from src.postgres_exp.pg_schema import PostgresSchemaManager


def run_phase_3_verification(num_rows: int = 500_000) -> Dict[str, Any]:
    print("\n=================================================================")
    print(f"STARTING PHASE 3 EMPIRICAL POSTGRESQL VERIFICATION ({num_rows:,} rows)")
    print("=================================================================")

    schema_mgr = PostgresSchemaManager()
    explain_runner = PostgresExplainRunner()
    verification_data: Dict[str, Any] = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "num_rows": num_rows,
            "engine": "PostgreSQL 17",
        },
        "experiments": {},
    }

    # Query templates
    # Query 1: Point Tenant + Point Status + 30-day Time Window
    query_opt_filter = """
        SELECT * FROM orders
        WHERE tenant_id = %s AND status = %s AND created_at BETWEEN %s AND %s;
    """
    # Query 2: Range/Skip Tenant (Vi phạm leftmost prefix trên I_OPT)
    query_skip_lead = """
        SELECT * FROM orders
        WHERE status = %s AND created_at BETWEEN %s AND %s;
    """
    # Query 3: Multi-tenant batch range (Wider scan)
    query_wide_range = """
        SELECT * FROM orders
        WHERE tenant_id IN (%s, %s, %s, %s, %s) AND status = %s AND created_at BETWEEN %s AND %s;
    """

    # Parameters: tenant_id=1001, status=1 (PENDING), 60-day window
    t_start = BASE_TIMESTAMP_MS + 10 * 86400 * 1000
    t_end = t_start + 60 * 86400 * 1000
    params_q1 = (1001, 1, t_start, t_end)
    params_q_skip = (1, t_start, t_end)
    params_q_wide = (1001, 1002, 1003, 1004, 1005, 1, t_start, t_end)

    # --------------------------------------------------------------------------
    # DATASET RUN 1: DIST_UNCORRELATED (r ≈ 0.0)
    # --------------------------------------------------------------------------
    print(f"\n>>> [STEP 1/2] Loading Dataset: DIST_UNCORRELATED (r ≈ 0.0)...")
    schema_mgr.init_orders_table(drop_existing=True)
    load_time_uncorr = schema_mgr.bulk_load_orders(
        num_rows=num_rows, mode=DataDistributionMode.DIST_UNCORRELATED, seed=42
    )

    uncorr_exp: Dict[str, Any] = {"load_time_sec": load_time_uncorr, "variants": {}}

    # Test each index variant under UNCORRELATED dataset
    for variant in ["I_NONE", "I_OPT", "I_INV_LOW_SEL"]:
        print(f"\n--- Testing Variant {variant} on DIST_UNCORRELATED ---")
        idx_time = schema_mgr.apply_index_variant(variant)
        stats = schema_mgr.get_pg_stats()

        # Run Query 1 under work_mem = 4MB
        plan_q1 = explain_runner.explain_query(
            query_opt_filter, params=params_q1, work_mem="4MB"
        )
        print(
            f"  [Q1 - Full Predicate @ 4MB] Node: {plan_q1.node_type:18s} | Cost: {plan_q1.total_cost:8.2f} | Rows: {plan_q1.actual_rows:4d} | ExactBlk: {plan_q1.exact_heap_blocks:4d} | SharedRead: {plan_q1.shared_read_blocks:4d} | Time: {plan_q1.execution_time_ms:6.3f}ms"
        )

        # Run Query Skip Lead (violate leftmost prefix for I_OPT)
        plan_skip = explain_runner.explain_query(
            query_skip_lead, params=params_q_skip, work_mem="4MB"
        )
        print(
            f"  [Q2 - Skip Leading @ 4MB ] Node: {plan_skip.node_type:18s} | Cost: {plan_skip.total_cost:8.2f} | Rows: {plan_skip.actual_rows:4d} | ExactBlk: {plan_skip.exact_heap_blocks:4d} | SharedRead: {plan_skip.shared_read_blocks:4d} | Time: {plan_skip.execution_time_ms:6.3f}ms"
        )

        # Run with constrained work_mem = 64kB on Query 2 (Triggering Lossy Bitmap transition)
        plan_skip_64k = explain_runner.explain_query(
            query_skip_lead, params=params_q_skip, work_mem="64kB"
        )
        print(
            f"  [Q2 - Skip Leading @ 64kB] Node: {plan_skip_64k.node_type:18s} | Cost: {plan_skip_64k.total_cost:8.2f} | Rows: {plan_skip_64k.actual_rows:4d} | ExactBlk: {plan_skip_64k.exact_heap_blocks:4d} | LossyBlk: {plan_skip_64k.lossy_heap_blocks:4d} | Time: {plan_skip_64k.execution_time_ms:6.3f}ms"
        )

        uncorr_exp["variants"][variant] = {
            "index_build_sec": idx_time,
            "catalog_stats": stats,
            "query_1_explain": plan_q1.raw_plan_tree,
            "query_skip_explain_4mb": plan_skip.raw_plan_tree,
            "query_skip_explain_64kb": plan_skip_64k.raw_plan_tree,
            "summary_metrics": {
                "q1_node": plan_q1.node_type,
                "q1_cost": plan_q1.total_cost,
                "q1_time_ms": plan_q1.execution_time_ms,
                "q1_shared_read": plan_q1.shared_read_blocks,
                "q_skip_node": plan_skip.node_type,
                "q_skip_cost": plan_skip.total_cost,
                "q_skip_exact_blocks": plan_skip.exact_heap_blocks,
                "q_skip_lossy_blocks_64kb": plan_skip_64k.lossy_heap_blocks,
            },
        }

    # Dedicated Lossy Bitmap Heap Scan Test under I_INV_LOW_SEL
    print("\n--- Dedicated Exact -> Lossy Bitmap Heap Scan Transition Test ---")
    with schema_mgr.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SET enable_seqscan = off")
            cur.execute("SET enable_indexscan = off")
            cur.execute("SET max_parallel_workers_per_gather = 0")

            # 1. work_mem = 4MB
            cur.execute("SET work_mem = '4MB'")
            cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, WAL, FORMAT JSON) {query_skip_lead}", params_q_skip)
            plan_exact = cur.fetchone()[0]
            p_ex = plan_exact[0]["Plan"]
            print(f"  [work_mem = 4MB ] Exact Heap Blocks: {p_ex.get('Exact Heap Blocks'):4d} | Lossy Heap Blocks: {p_ex.get('Lossy Heap Blocks'):4d} | Recheck Cond: {p_ex.get('Recheck Cond')}")

            # 2. work_mem = 64kB
            cur.execute("SET work_mem = '64kB'")
            cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, WAL, FORMAT JSON) {query_skip_lead}", params_q_skip)
            plan_lossy = cur.fetchone()[0]
            p_ls = plan_lossy[0]["Plan"]
            print(f"  [work_mem = 64kB] Exact Heap Blocks: {p_ls.get('Exact Heap Blocks'):4d} | Lossy Heap Blocks: {p_ls.get('Lossy Heap Blocks'):4d} | Rows Removed Recheck: {p_ls.get('Rows Removed by Index Recheck'):,d}")

            uncorr_exp["lossy_bitmap_experiment"] = {
                "work_mem_4mb": {
                    "exact_heap_blocks": p_ex.get("Exact Heap Blocks"),
                    "lossy_heap_blocks": p_ex.get("Lossy Heap Blocks"),
                    "execution_time_ms": plan_exact[0]["Execution Time"],
                },
                "work_mem_64kb": {
                    "exact_heap_blocks": p_ls.get("Exact Heap Blocks"),
                    "lossy_heap_blocks": p_ls.get("Lossy Heap Blocks"),
                    "rows_removed_by_recheck": p_ls.get("Rows Removed by Index Recheck"),
                    "execution_time_ms": plan_lossy[0]["Execution Time"],
                },
            }

    verification_data["experiments"]["DIST_UNCORRELATED"] = uncorr_exp

    # --------------------------------------------------------------------------
    # DATASET RUN 2: DIST_CLUSTERED (r ≈ 1.0)
    # --------------------------------------------------------------------------
    print(f"\n>>> [STEP 2/2] Loading Dataset: DIST_CLUSTERED (r ≈ 1.0)...")
    schema_mgr.init_orders_table(drop_existing=True)
    load_time_clust = schema_mgr.bulk_load_orders(
        num_rows=num_rows, mode=DataDistributionMode.DIST_CLUSTERED, seed=42
    )

    clust_exp: Dict[str, Any] = {"load_time_sec": load_time_clust, "variants": {}}

    for variant in ["I_NONE", "I_OPT", "I_INV_LOW_SEL"]:
        print(f"\n--- Testing Variant {variant} on DIST_CLUSTERED ---")
        idx_time = schema_mgr.apply_index_variant(variant)
        stats = schema_mgr.get_pg_stats()

        plan_q1 = explain_runner.explain_query(
            query_opt_filter, params=params_q1, work_mem="4MB"
        )
        print(
            f"  [Q1 - Full Predicate @ 4MB] Node: {plan_q1.node_type:18s} | Cost: {plan_q1.total_cost:8.2f} | Rows: {plan_q1.actual_rows:4d} | SharedHit: {plan_q1.shared_hit_blocks:4d} | SharedRead: {plan_q1.shared_read_blocks:4d} | Time: {plan_q1.execution_time_ms:6.3f}ms"
        )

        plan_skip = explain_runner.explain_query(
            query_skip_lead, params=params_q_skip, work_mem="4MB"
        )
        print(
            f"  [Q2 - Skip Leading @ 4MB ] Node: {plan_skip.node_type:18s} | Cost: {plan_skip.total_cost:8.2f} | Rows: {plan_skip.actual_rows:4d} | ExactBlk: {plan_skip.exact_heap_blocks:4d} | LossyBlk: {plan_skip.lossy_heap_blocks:4d} | Time: {plan_skip.execution_time_ms:6.3f}ms"
        )

        clust_exp["variants"][variant] = {
            "index_build_sec": idx_time,
            "catalog_stats": stats,
            "query_1_explain": plan_q1.raw_plan_tree,
            "query_skip_explain_4mb": plan_skip.raw_plan_tree,
            "summary_metrics": {
                "q1_node": plan_q1.node_type,
                "q1_cost": plan_q1.total_cost,
                "q1_time_ms": plan_q1.execution_time_ms,
                "q1_shared_read": plan_q1.shared_read_blocks,
                "q1_shared_hit": plan_q1.shared_hit_blocks,
            },
        }

    verification_data["experiments"]["DIST_CLUSTERED"] = clust_exp

    # Save complete raw JSON dump
    output_json = Path("results/raw_json/pg_explain_verification.json")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(verification_data, f, indent=2)

    print(f"\n[OK] Raw JSON diagnostic log saved to: {output_json.resolve()}")
    return verification_data


if __name__ == "__main__":
    t0 = time.perf_counter()
    results = run_phase_3_verification(num_rows=500_000)
    print(f"\n=================================================================")
    print(f"PHASE 3 VERIFICATION FINISHED IN {time.perf_counter() - t0:.2f}s")
    print("=================================================================\n")
