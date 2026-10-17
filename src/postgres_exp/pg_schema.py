#!/usr/bin/env python3
"""
PostgreSQL Schema, Bulk Streaming Ingestion, and Index Management
Project: Empirical Study of Indexing & Key Ordering on Tail Latency
Supports:
1. Dynamic Index Configuration Switching (I_NONE, I_OPT, I_INV_LOW_SEL)
2. High-speed Streaming COPY Ingestion
3. Statistical Metadata Extraction (pg_stats: correlation, n_distinct, null_frac)
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psycopg
from psycopg import sql

from src.common.config import PG_CONFIG, DataDistributionMode, OrderRecord
from src.common.data_generator import OrderDataGenerator


# ==============================================================================
# INDEX VARIANT DEFINITIONS
# ==============================================================================
INDEX_VARIANTS: Dict[str, Optional[str]] = {
    "I_NONE": None,
    "I_OPT": "CREATE INDEX idx_orders_opt ON orders (tenant_id, status, created_at)",
    "I_INV_LOW_SEL": "CREATE INDEX idx_orders_inv_low ON orders (status, created_at, tenant_id)",
}


class PostgresSchemaManager:
    """Manages table creation, streaming ingestion, indexing, and catalog inspection."""

    def __init__(self, db_config: Optional[Dict[str, Any]] = None) -> None:
        self.config = db_config or PG_CONFIG

    def get_connection(self, autocommit: bool = True) -> psycopg.Connection:
        return psycopg.connect(**self.config, autocommit=autocommit)

    def init_orders_table(self, drop_existing: bool = True) -> None:
        """Create orders table with standard schema."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                if drop_existing:
                    cur.execute("DROP TABLE IF EXISTS orders CASCADE")

                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS orders (
                        order_id    BIGINT PRIMARY KEY,
                        tenant_id   INT NOT NULL,
                        status      SMALLINT NOT NULL,
                        created_at  BIGINT NOT NULL,
                        amount      INT NOT NULL,
                        payload     VARCHAR(100) NOT NULL
                    );
                    """
                )
                print("[pg_schema] Table 'orders' initialized successfully.")

    def bulk_load_orders(
        self,
        num_rows: int,
        mode: DataDistributionMode = DataDistributionMode.DIST_UNCORRELATED,
        chunk_size: int = 50_000,
        seed: int = 42,
    ) -> float:
        """
        Fast bulk loading using psycopg3 streaming COPY protocol.
        Returns elapsed loading time in seconds.
        """
        generator = OrderDataGenerator(seed=seed)
        print(
            f"[pg_schema] Bulk streaming {num_rows:,} rows (Mode: {mode.value}) into 'orders'..."
        )

        t0 = time.perf_counter()
        with self.get_connection(autocommit=True) as conn:
            with conn.cursor() as cur:
                copy_sql = (
                    "COPY orders (order_id, tenant_id, status, created_at, amount, payload) "
                    "FROM STDIN"
                )
                with cur.copy(copy_sql) as copy:
                    for chunk in generator.iter_records(
                        num_rows=num_rows, mode=mode, chunk_size=chunk_size
                    ):
                        for r in chunk:
                            copy.write_row(
                                (
                                    r.order_id,
                                    r.tenant_id,
                                    r.status,
                                    r.created_at,
                                    r.amount,
                                    r.payload,
                                )
                            )

        elapsed = time.perf_counter() - t0
        print(
            f"[pg_schema] Loaded {num_rows:,} rows in {elapsed:.2f}s ({num_rows / elapsed:,.0f} rows/s)."
        )
        return elapsed

    def apply_index_variant(self, variant: str) -> float:
        """
        Switches index configuration cleanly:
        1. Drops existing secondary indexes on orders
        2. Applies the requested index variant (if not I_NONE)
        3. Executes VACUUM ANALYZE orders to refresh statistics
        Returns time taken in seconds.
        """
        if variant not in INDEX_VARIANTS:
            raise ValueError(
                f"Unknown index variant '{variant}'. Supported: {list(INDEX_VARIANTS.keys())}"
            )

        print(f"[pg_schema] Applying index variant: {variant}...")
        t0 = time.perf_counter()
        with self.get_connection(autocommit=True) as conn:
            with conn.cursor() as cur:
                # Drop existing composite indexes
                cur.execute("DROP INDEX IF EXISTS idx_orders_opt")
                cur.execute("DROP INDEX IF EXISTS idx_orders_inv_low")

                create_stmt = INDEX_VARIANTS[variant]
                if create_stmt:
                    print(f"  Executing: {create_stmt}")
                    cur.execute(create_stmt)
                else:
                    print("  I_NONE selected: No secondary index created.")

                # Always VACUUM ANALYZE after schema changes
                print("  Executing VACUUM ANALYZE orders...")
                cur.execute("VACUUM ANALYZE orders")

        elapsed = time.perf_counter() - t0
        print(f"[pg_schema] Index variant {variant} applied in {elapsed:.2f}s.")
        return elapsed

    def get_pg_stats(self) -> List[Dict[str, Any]]:
        """
        Extracts column statistics from pg_stats for 'orders'.
        Fields: attname, null_frac, n_distinct, correlation.
        """
        stats: List[Dict[str, Any]] = []
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 
                        attname,
                        null_frac,
                        n_distinct,
                        correlation
                    FROM pg_stats
                    WHERE tablename = 'orders' AND schemaname = 'public'
                    ORDER BY attname;
                    """
                )
                for row in cur.fetchall():
                    stats.append(
                        {
                            "column": row[0],
                            "null_frac": float(row[1]) if row[1] is not None else 0.0,
                            "n_distinct": float(row[2]) if row[2] is not None else 0.0,
                            "correlation": (
                                round(float(row[3]), 5) if row[3] is not None else None
                            ),
                        }
                    )
        return stats

    def export_stats_json(self, output_path: str | Path) -> None:
        """Export pg_stats snapshot to a JSON file."""
        stats = self.get_pg_stats()
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
        print(f"[pg_schema] Exported catalog stats to: {target.resolve()}")
