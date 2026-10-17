#!/usr/bin/env python3
"""
Deterministic Data & Workload Generator
Project: Empirical Study of Indexing & Key Ordering on Tail Latency
Supports:
1. 3 Physical and Logical Distribution Modes (Uncorrelated, Clustered, Correlated Columns / AVI Violation)
2. YCSB Standard Query Parameter Generators (Uniform & Zipfian s=0.99)
3. Vectorized Generation with zero-copy NumPy buffers for PostgreSQL & RocksDB
"""

from __future__ import annotations

import struct
from typing import Dict, Iterator, List, Optional, Tuple

import numpy as np

from src.common.config import (
    BASE_TIMESTAMP_MS,
    DEFAULT_NUM_TENANTS,
    MIN_AMOUNT,
    MAX_AMOUNT,
    PAYLOAD_SIZE,
    RANDOM_SEED,
    STATUS_COUNT,
    WINDOW_MS,
    DataDistributionMode,
    OrderRecord,
    QueryDistribution,
)


class FastZipfianGenerator:
    """
    Vectorized Scrambled Zipfian Generator following the YCSB specification
    (Gray et al. / Cooper et al.) with skew parameter s = theta (default 0.99).
    """

    def __init__(
        self,
        n: int = DEFAULT_NUM_TENANTS,
        theta: float = 0.99,
        seed: int = RANDOM_SEED,
    ) -> None:
        self.n = max(2, n)
        self.theta = theta
        self.rng = np.random.default_rng(seed)
        self.alpha = 1.0 / (1.0 - theta)

        # Zeta calculations
        # zeta(n) = sum_{i=1}^n 1 / (i^theta)
        # For large n, computed accurately with numpy
        i_arr = np.arange(1, min(self.n + 1, 10_000_001), dtype=np.float64)
        self.zetan = float(np.sum(1.0 / np.power(i_arr, theta)))
        self.zeta2 = float(1.0 + np.power(0.5, theta))
        self.eta = (1.0 - np.power(2.0 / self.n, 1.0 - theta)) / (
            1.0 - self.zeta2 / self.zetan
        )

    def sample(self, size: int = 1) -> np.ndarray:
        """Draw 'size' samples from the Zipfian distribution in range [1, n]."""
        u = self.rng.random(size)
        uz = u * self.zetan

        # Vectorized piece-wise mapping
        out = np.empty(size, dtype=np.int32)

        # Mask 1: uz < 1.0 -> item 1
        m1 = uz < 1.0
        out[m1] = 1

        # Mask 2: 1.0 <= uz < 1.0 + (0.5^theta) -> item 2
        m2 = (~m1) & (uz < self.zeta2)
        out[m2] = 2

        # Mask 3: general formula
        m3 = ~(m1 | m2)
        if np.any(m3):
            u_m3 = u[m3]
            v = 1.0 + self.n * np.power(self.eta * u_m3 - self.eta + 1.0, self.alpha)
            # Clip between 1 and n
            np.clip(v, 1, self.n, out=v)
            out[m3] = v.astype(np.int32)

        return out

    def next_value(self) -> int:
        """Draw a single sample."""
        return int(self.sample(1)[0])


class UniformGenerator:
    """Deterministic Uniform generator over [1, n]."""

    def __init__(self, n: int = DEFAULT_NUM_TENANTS, seed: int = RANDOM_SEED) -> None:
        self.n = max(1, n)
        self.rng = np.random.default_rng(seed)

    def sample(self, size: int = 1) -> np.ndarray:
        return self.rng.integers(1, self.n + 1, size=size, dtype=np.int32)

    def next_value(self) -> int:
        return int(self.rng.integers(1, self.n + 1))


class OrderDataGenerator:
    """
    Deterministic dataset generator producing OrderRecord instances.
    Provides mathematically verified distributions for:
    1. DIST_UNCORRELATED (r ≈ 0.0)
    2. DIST_CLUSTERED (r ≈ 1.0)
    3. DIST_CORRELATED_COLS (AVI Violation)
    """

    def __init__(
        self,
        num_tenants: int = DEFAULT_NUM_TENANTS,
        seed: int = RANDOM_SEED,
    ) -> None:
        self.num_tenants = num_tenants
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def generate_batch(
        self,
        num_rows: int,
        mode: DataDistributionMode = DataDistributionMode.DIST_UNCORRELATED,
        start_order_id: int = 1,
    ) -> Dict[str, np.ndarray]:
        """
        Generates 'num_rows' orders as a dictionary of aligned NumPy arrays.
        """
        # Order IDs: sequential 64-bit integers
        order_ids = np.arange(
            start_order_id, start_order_id + num_rows, dtype=np.int64
        )

        # Amounts: uniformly between MIN_AMOUNT and MAX_AMOUNT
        amounts = self.rng.integers(
            MIN_AMOUNT, MAX_AMOUNT + 1, size=num_rows, dtype=np.int32
        )

        # Standard deterministic payload buffer (100 bytes each)
        # We pre-generate a fixed ASCII pattern
        payload_base = ("X" * (PAYLOAD_SIZE - 8)).encode("ascii")

        if mode == DataDistributionMode.DIST_UNCORRELATED:
            # Mode 1: Completely independent columns + random physical row order
            tenant_ids = self.rng.integers(
                1, self.num_tenants + 1, size=num_rows, dtype=np.int32
            )
            statuses = self.rng.integers(0, STATUS_COUNT, size=num_rows, dtype=np.int8)
            created_offsets = self.rng.integers(
                0, WINDOW_MS, size=num_rows, dtype=np.int64
            )
            created_ats = BASE_TIMESTAMP_MS + created_offsets

            # Ensure row ordering is randomly shuffled
            shuffle_idx = self.rng.permutation(num_rows)
            tenant_ids = tenant_ids[shuffle_idx]
            statuses = statuses[shuffle_idx]
            created_ats = created_ats[shuffle_idx]
            amounts = amounts[shuffle_idx]

        elif mode == DataDistributionMode.DIST_CLUSTERED:
            # Mode 2: Clustered physically by (tenant_id, status, created_at)
            tenant_ids = self.rng.integers(
                1, self.num_tenants + 1, size=num_rows, dtype=np.int32
            )
            statuses = self.rng.integers(0, STATUS_COUNT, size=num_rows, dtype=np.int8)
            created_offsets = self.rng.integers(
                0, WINDOW_MS, size=num_rows, dtype=np.int64
            )
            created_ats = BASE_TIMESTAMP_MS + created_offsets

            # Multi-key physical sort: primary=tenant_id, secondary=status, tertiary=created_at
            # Lexsort takes keys in reverse order (tertiary, secondary, primary)
            sort_order = np.lexsort((created_ats, statuses, tenant_ids))
            tenant_ids = tenant_ids[sort_order]
            statuses = statuses[sort_order]
            created_ats = created_ats[sort_order]
            amounts = amounts[sort_order]

        elif mode == DataDistributionMode.DIST_CORRELATED_COLS:
            # Mode 3: Strong statistical correlation violating Attribute Value Independence (AVI)
            # Even tenants have 95% probability of status=0 (OPEN), 5% distributed in 1..4
            # Odd tenants have 5% probability of status=0, 95% distributed in 1..4
            tenant_ids = self.rng.integers(
                1, self.num_tenants + 1, size=num_rows, dtype=np.int32
            )
            created_offsets = self.rng.integers(
                0, WINDOW_MS, size=num_rows, dtype=np.int64
            )
            created_ats = BASE_TIMESTAMP_MS + created_offsets

            is_even = (tenant_ids % 2) == 0
            rand_probs = self.rng.random(num_rows)

            statuses = np.empty(num_rows, dtype=np.int8)

            # For even tenants:
            even_mask = is_even
            even_stat0 = even_mask & (rand_probs < 0.95)
            even_other = even_mask & (rand_probs >= 0.95)
            statuses[even_stat0] = 0
            if np.any(even_other):
                statuses[even_other] = self.rng.integers(
                    1, STATUS_COUNT, size=int(np.sum(even_other)), dtype=np.int8
                )

            # For odd tenants:
            odd_mask = ~is_even
            odd_stat0 = odd_mask & (rand_probs < 0.05)
            odd_other = odd_mask & (rand_probs >= 0.05)
            statuses[odd_stat0] = 0
            if np.any(odd_other):
                statuses[odd_other] = self.rng.integers(
                    1, STATUS_COUNT, size=int(np.sum(odd_other)), dtype=np.int8
                )

            # Randomize physical positions
            shuffle_idx = self.rng.permutation(num_rows)
            tenant_ids = tenant_ids[shuffle_idx]
            statuses = statuses[shuffle_idx]
            created_ats = created_ats[shuffle_idx]
            amounts = amounts[shuffle_idx]

        else:
            raise ValueError(f"Unsupported DataDistributionMode: {mode}")

        return {
            "order_id": order_ids,
            "tenant_id": tenant_ids,
            "status": statuses,
            "created_at": created_ats,
            "amount": amounts,
            "payload_base": payload_base,
        }

    def iter_records(
        self,
        num_rows: int,
        mode: DataDistributionMode = DataDistributionMode.DIST_UNCORRELATED,
        chunk_size: int = 50_000,
    ) -> Iterator[List[OrderRecord]]:
        """
        Yields chunks of typed OrderRecord instances for streaming ingestion.
        """
        remaining = num_rows
        current_id = 1
        while remaining > 0:
            batch_n = min(remaining, chunk_size)
            batch = self.generate_batch(batch_n, mode=mode, start_order_id=current_id)
            records: List[OrderRecord] = []
            base_str = "X" * (PAYLOAD_SIZE - 8)

            for i in range(batch_n):
                oid = int(batch["order_id"][i])
                payload_str = f"{oid:08d}_{base_str}"[:PAYLOAD_SIZE]
                records.append(
                    OrderRecord(
                        order_id=oid,
                        tenant_id=int(batch["tenant_id"][i]),
                        status=int(batch["status"][i]),
                        created_at=int(batch["created_at"][i]),
                        amount=int(batch["amount"][i]),
                        payload=payload_str,
                    )
                )
            yield records
            remaining -= batch_n
            current_id += batch_n


class QueryWorkloadGenerator:
    """
    Generates deterministic query predicates for empirical benchmarks.
    Supports Point Queries and Range Queries under Uniform or Zipfian skew.
    """

    def __init__(
        self,
        num_tenants: int = DEFAULT_NUM_TENANTS,
        distribution: QueryDistribution = QueryDistribution.ZIPFIAN,
        seed: int = RANDOM_SEED + 100,
    ) -> None:
        self.num_tenants = num_tenants
        self.distribution = distribution
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        if distribution == QueryDistribution.ZIPFIAN:
            self.tenant_gen = FastZipfianGenerator(
                n=num_tenants, theta=0.99, seed=seed
            )
        else:
            self.tenant_gen = UniformGenerator(n=num_tenants, seed=seed)

    def generate_query_params(
        self,
        count: int,
        time_window_days: int = 30,
    ) -> List[Tuple[int, int, int, int]]:
        """
        Generates query parameters: (tenant_id, status, created_at_start, created_at_end).
        - tenant_id: chosen according to workload skew (Uniform / Zipfian)
        - status: chosen uniformly [0 .. 4]
        - created_at_start, created_at_end: bounding time window
        """
        tenant_ids = self.tenant_gen.sample(count)
        statuses = self.rng.integers(0, STATUS_COUNT, size=count, dtype=np.int32)

        window_range_ms = time_window_days * 24 * 3600 * 1000
        max_start_offset = max(1, WINDOW_MS - window_range_ms)
        start_offsets = self.rng.integers(
            0, max_start_offset, size=count, dtype=np.int64
        )

        queries: List[Tuple[int, int, int, int]] = []
        for i in range(count):
            t_id = int(tenant_ids[i])
            st = int(statuses[i])
            start_ts = BASE_TIMESTAMP_MS + int(start_offsets[i])
            end_ts = start_ts + window_range_ms
            queries.append((t_id, st, start_ts, end_ts))

        return queries
