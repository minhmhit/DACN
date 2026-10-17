#!/usr/bin/env python3
"""
Global Configuration & Workload Invariants
Project: Empirical Study of Indexing & Key Ordering on Tail Latency
(PostgreSQL B-Tree vs. RocksDB LSM-Tree)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Final, NamedTuple


# ==============================================================================
# 1. REPRODUCIBILITY & DETERMINISTIC SEED
# ==============================================================================
RANDOM_SEED: Final[int] = int(os.environ.get("RANDOM_SEED", "42"))


# ==============================================================================
# 2. DATA SCALE & DOMAIN CARDINALITIES
# ==============================================================================
DEFAULT_NUM_TENANTS: Final[int] = int(os.environ.get("NUM_TENANTS", "10000"))
DEFAULT_NUM_ORDERS: Final[int] = int(os.environ.get("NUM_ORDERS", "1000000"))

# Status Cardinality (Low selectivity: 5 distinct states)
STATUS_COUNT: Final[int] = 5
STATUS_NAMES: Final[Dict[int, str]] = {
    0: "OPEN",
    1: "PENDING",
    2: "PROCESSING",
    3: "CLOSED",
    4: "CANCELLED",
}

# Payload size matching standard YCSB field (100 ASCII bytes)
PAYLOAD_SIZE: Final[int] = 100

# Amount domain: 100 to 100,000 (cents or currency units)
MIN_AMOUNT: Final[int] = 100
MAX_AMOUNT: Final[int] = 100_000

# Temporal domain: 365 days window in milliseconds
BASE_TIMESTAMP_MS: Final[int] = 1704067200000  # 2024-01-01 00:00:00 UTC
WINDOW_DAYS: Final[int] = 365
WINDOW_MS: Final[int] = WINDOW_DAYS * 24 * 3600 * 1000


# ==============================================================================
# 3. TYPED DATA RECORD SPECIFICATION
# ==============================================================================
class OrderRecord(NamedTuple):
    """
    Standard Order entity schema matching both PostgreSQL table and RocksDB KV.
    Columns:
      1. order_id   : INT64 ($1 .. N$) - Unique identifier
      2. tenant_id  : INT32 ($1 .. 10,000$) - Primary partition / filter attribute
      3. status     : INT8  ($0 .. 4$) - Low cardinality discrete attribute
      4. created_at : INT64 (Epoch millis) - Range attribute
      5. amount     : INT32 ($100 .. 100,000$)
      6. payload    : str   (100 ASCII characters)
    """
    order_id: int
    tenant_id: int
    status: int
    created_at: int
    amount: int
    payload: str


# ==============================================================================
# 4. DATASET & QUERY DISTRIBUTION MODES
# ==============================================================================
class DataDistributionMode(str, Enum):
    """
    Experimental distribution modes to evaluate RQ3 & GT3:
    - UNCORRELATED: Random physical shuffle, correlation r ≈ 0.0 with row index
    - CLUSTERED: Physically sorted by (tenant_id, status, created_at), r ≈ 1.0
    - CORRELATED_COLS: Strong dependency between tenant_id and status (AVI violation)
    """
    DIST_UNCORRELATED = "uncorrelated"
    DIST_CLUSTERED = "clustered"
    DIST_CORRELATED_COLS = "correlated_cols"


class QueryDistribution(str, Enum):
    """
    Query workload skew pattern:
    - UNIFORM: Equal probability across all tenant_ids
    - ZIPFIAN: Power-law skewed access (s = 0.99, YCSB standard)
    """
    UNIFORM = "uniform"
    ZIPFIAN = "zipfian"


# ==============================================================================
# 5. HDRHISTOGRAM MEASUREMENT INVARIANTS
# ==============================================================================
# Tracking range: 1 microsecond to 60,000,000 microseconds (60 seconds)
HISTOGRAM_LOWEST_VALUE_US: Final[int] = 1
HISTOGRAM_HIGHEST_VALUE_US: Final[int] = 60_000_000
HISTOGRAM_SIGNIFICANT_FIGURES: Final[int] = 3

# Benchmark phase default timings (seconds)
DEFAULT_WARMUP_SECONDS: Final[int] = 20
DEFAULT_MEASURE_SECONDS: Final[int] = 60


# ==============================================================================
# 6. DATABASE CONNECTION CONFIGURATIONS
# ==============================================================================
PG_CONFIG: Final[Dict[str, str | int]] = {
    "host": os.environ.get("PGHOST", "localhost"),
    "port": int(os.environ.get("PGPORT", "5432")),
    "dbname": os.environ.get("PGDATABASE", "indexing_research"),
    "user": os.environ.get("PGUSER", "research"),
    "password": os.environ.get("PGPASSWORD", "research"),
}

ROCKSDB_DEFAULT_PATH: Final[str] = os.environ.get("ROCKSDB_PATH", "./results/rocksdb_store")
