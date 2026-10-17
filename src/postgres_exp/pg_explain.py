#!/usr/bin/env python3
"""
EXPLAIN (ANALYZE, BUFFERS, WAL, FORMAT JSON) Parser & Diagnostic Evaluator
Project: Empirical Study of Indexing & Key Ordering on Tail Latency
Extracts:
1. Planner Cost & Actual Execution Metrics (Cost, Rows, Q-Error, Times)
2. Buffer & Memory Metrics (Shared Hit/Read, Exact/Lossy Heap Blocks)
3. WAL Telemetry (WAL Records, WAL Bytes)
4. Predicate & Filtering Diagnostics (Index Cond, Recheck Cond, Filter, Rows Removed)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

import psycopg

from src.common.config import PG_CONFIG


@dataclass
class ExplainMetrics:
    """Aggregated & Primary Node Metrics parsed from PostgreSQL EXPLAIN JSON."""

    # Top-level timing
    planning_time_ms: float
    execution_time_ms: float

    # Primary scan node
    node_type: str
    relation_name: Optional[str]
    index_name: Optional[str]

    # Cost-based optimizer estimates & accuracy
    startup_cost: float
    total_cost: float
    plan_rows: int
    actual_rows: int
    q_error: float  # max(plan/actual, actual/plan)

    # Predicate details
    index_cond: Optional[str]
    recheck_cond: Optional[str]
    filter_cond: Optional[str]
    rows_removed_by_filter: int
    rows_removed_by_index_recheck: int

    # Buffer & Heap Block Telemetry
    heap_fetches: int
    exact_heap_blocks: int
    lossy_heap_blocks: int
    shared_hit_blocks: int
    shared_read_blocks: int
    shared_dirtied_blocks: int
    shared_written_blocks: int
    buffer_hit_ratio: float

    # WAL Telemetry
    wal_records: int
    wal_bytes: int

    # Subnodes summary
    child_node_types: List[str]
    raw_plan_tree: Dict[str, Any]


class ExplainParser:
    """Recursive parser for PostgreSQL EXPLAIN JSON structures."""

    @staticmethod
    def parse_explain_json(raw_explain_output: List[Dict[str, Any]]) -> ExplainMetrics:
        """
        Parses the JSON structure returned by EXPLAIN (ANALYZE, BUFFERS, WAL, FORMAT JSON).
        Recursively aggregates I/O and traverses child nodes.
        """
        if not raw_explain_output or not isinstance(raw_explain_output, list):
            raise ValueError(f"Invalid EXPLAIN output format: {raw_explain_output}")

        root = raw_explain_output[0]
        planning_time = float(root.get("Planning Time", 0.0))
        execution_time = float(root.get("Execution Time", 0.0))
        plan_root = root.get("Plan", {})

        # Aggregated telemetry counters across entire plan tree
        total_shared_hit = 0
        total_shared_read = 0
        total_shared_dirtied = 0
        total_shared_written = 0
        total_wal_records = 0
        total_wal_bytes = 0
        exact_heap_blocks = 0
        lossy_heap_blocks = 0
        rows_removed_by_filter = 0
        rows_removed_by_recheck = 0
        heap_fetches = 0

        child_nodes: List[str] = []

        def traverse(node: Dict[str, Any]) -> None:
            nonlocal total_shared_hit, total_shared_read, total_shared_dirtied, total_shared_written
            nonlocal total_wal_records, total_wal_bytes, exact_heap_blocks, lossy_heap_blocks
            nonlocal rows_removed_by_filter, rows_removed_by_recheck, heap_fetches

            # Accumulate buffer metrics
            total_shared_hit += node.get("Shared Hit Blocks", 0)
            total_shared_read += node.get("Shared Read Blocks", 0)
            total_shared_dirtied += node.get("Shared Dirtied Blocks", 0)
            total_shared_written += node.get("Shared Written Blocks", 0)

            # Accumulate WAL metrics
            total_wal_records += node.get("WAL Records", 0)
            total_wal_bytes += node.get("WAL Bytes", 0)

            # Accumulate Bitmap Heap Scan metrics
            exact_heap_blocks += node.get("Exact Heap Blocks", 0)
            lossy_heap_blocks += node.get("Lossy Heap Blocks", 0)

            # Filter rows
            rows_removed_by_filter += node.get("Rows Removed by Filter", 0)
            rows_removed_by_recheck += node.get("Rows Removed by Index Recheck", 0)
            heap_fetches += node.get("Heap Fetches", 0)

            if "Plans" in node:
                for subplan in node["Plans"]:
                    child_nodes.append(subplan.get("Node Type", "Unknown"))
                    traverse(subplan)

        traverse(plan_root)

        # Primary Node attributes
        primary_node_type = plan_root.get("Node Type", "Unknown")
        rel_name = plan_root.get("Relation Name")
        idx_name = plan_root.get("Index Name")
        if not idx_name and "Plans" in plan_root:
            for child in plan_root["Plans"]:
                if "Index Name" in child:
                    idx_name = child["Index Name"]
                    break

        startup_cost = float(plan_root.get("Startup Cost", 0.0))
        total_cost = float(plan_root.get("Total Cost", 0.0))
        plan_rows = int(plan_root.get("Plan Rows", 1))
        actual_rows = int(plan_root.get("Actual Rows", 0))

        # Q-Error calculation: max(plan/actual, actual/plan)
        p_safe = max(1.0, float(plan_rows))
        a_safe = max(1.0, float(actual_rows))
        q_error = max(p_safe / a_safe, a_safe / p_safe)

        # Hit ratio calculation
        tot_blocks = total_shared_hit + total_shared_read
        hit_ratio = (
            round(total_shared_hit / tot_blocks, 4) if tot_blocks > 0 else 1.0
        )

        return ExplainMetrics(
            planning_time_ms=planning_time,
            execution_time_ms=execution_time,
            node_type=primary_node_type,
            relation_name=rel_name,
            index_name=idx_name,
            startup_cost=startup_cost,
            total_cost=total_cost,
            plan_rows=plan_rows,
            actual_rows=actual_rows,
            q_error=round(q_error, 2),
            index_cond=plan_root.get("Index Cond"),
            recheck_cond=plan_root.get("Recheck Cond"),
            filter_cond=plan_root.get("Filter"),
            rows_removed_by_filter=rows_removed_by_filter,
            rows_removed_by_index_recheck=rows_removed_by_recheck,
            heap_fetches=heap_fetches,
            exact_heap_blocks=exact_heap_blocks,
            lossy_heap_blocks=lossy_heap_blocks,
            shared_hit_blocks=total_shared_hit,
            shared_read_blocks=total_shared_read,
            shared_dirtied_blocks=total_shared_dirtied,
            shared_written_blocks=total_shared_written,
            buffer_hit_ratio=hit_ratio,
            wal_records=total_wal_records,
            wal_bytes=total_wal_bytes,
            child_node_types=child_nodes,
            raw_plan_tree=root,
        )


class PostgresExplainRunner:
    """Runs query workloads under EXPLAIN (ANALYZE, BUFFERS, WAL, FORMAT JSON)."""

    def __init__(self, db_config: Optional[Dict[str, Any]] = None) -> None:
        self.config = db_config or PG_CONFIG

    def explain_query(
        self,
        sql_query: str,
        params: Optional[Tuple[Any, ...]] = None,
        work_mem: Optional[str] = None,
        enable_seqscan: Optional[bool] = None,
    ) -> ExplainMetrics:
        """Executes query with EXPLAIN (ANALYZE, BUFFERS, WAL, FORMAT JSON) and parses result."""
        with psycopg.connect(**self.config, autocommit=True) as conn:
            with conn.cursor() as cur:
                if work_mem is not None:
                    cur.execute(f"SET work_mem = '{work_mem}'")
                if enable_seqscan is not None:
                    flag = "on" if enable_seqscan else "off"
                    cur.execute(f"SET enable_seqscan = {flag}")

                explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, WAL, FORMAT JSON) {sql_query}"
                if params:
                    cur.execute(explain_sql, params)
                else:
                    cur.execute(explain_sql)

                result = cur.fetchone()
                if not result:
                    raise RuntimeError("No output from EXPLAIN query.")

                raw_json = result[0]
                return ExplainParser.parse_explain_json(raw_json)
