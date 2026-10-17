#!/usr/bin/env python3
"""
Verification Script for Phase 2:
1. Validates 100,000 records for all 3 data distribution modes:
   - Uncorrelated (r ≈ 0.0)
   - Clustered (r ≈ 1.0)
   - Correlated Columns (AVI violation)
2. Validates Query Generators (Uniform & Zipfian s=0.99)
3. Validates LatencyTracker HdrHistogram with 10,000 samples
"""

import sys
import time
from pathlib import Path
import numpy as np

# Ensure workspace root is in python path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


from src.common.config import (
    DEFAULT_NUM_TENANTS,
    STATUS_COUNT,
    DataDistributionMode,
    QueryDistribution,
)
from src.common.data_generator import (
    FastZipfianGenerator,
    OrderDataGenerator,
    QueryWorkloadGenerator,
    UniformGenerator,
)
from src.common.latency_tracker import LatencyTracker


def verify_distributions(num_rows: int = 100_000) -> dict:
    print(f"\n=======================================================")
    print(f"TEST 1: Verifying 3 Data Distribution Modes ({num_rows:,} rows each)")
    print(f"=======================================================")

    gen = OrderDataGenerator(num_tenants=DEFAULT_NUM_TENANTS, seed=42)
    results = {}
    row_indices = np.arange(num_rows, dtype=np.float64)

    # 1.1 UNCORRELATED MODE
    print("\n--- 1.1 DIST_UNCORRELATED (Target: r ≈ 0.0) ---")
    batch_uncorr = gen.generate_batch(num_rows, mode=DataDistributionMode.DIST_UNCORRELATED)
    t_ids_uncorr = batch_uncorr["tenant_id"].astype(np.float64)
    r_uncorr = float(np.corrcoef(row_indices, t_ids_uncorr)[0, 1])

    # Status frequencies
    status_counts_uncorr = np.bincount(batch_uncorr["status"], minlength=STATUS_COUNT)
    status_pct_uncorr = (status_counts_uncorr / num_rows) * 100.0

    print(f"  Pearson Correlation r(row_index, tenant_id): {r_uncorr:+.5f}")
    print(f"  Status distribution (%): {np.round(status_pct_uncorr, 2).tolist()}")
    assert abs(r_uncorr) < 0.02, f"Correlation too high for uncorrelated: {r_uncorr}"
    assert all(18.0 < p < 22.0 for p in status_pct_uncorr), "Status distribution not uniform"
    results["uncorrelated_r"] = r_uncorr
    results["uncorrelated_status_pct"] = status_pct_uncorr.tolist()

    # 1.2 CLUSTERED MODE
    print("\n--- 1.2 DIST_CLUSTERED (Target: r ≈ 1.0) ---")
    batch_clust = gen.generate_batch(num_rows, mode=DataDistributionMode.DIST_CLUSTERED)
    t_ids_clust = batch_clust["tenant_id"].astype(np.float64)
    r_clust = float(np.corrcoef(row_indices, t_ids_clust)[0, 1])

    # Verify monotonic ordering
    is_sorted_tenant = bool(np.all(np.diff(batch_clust["tenant_id"]) >= 0))
    print(f"  Pearson Correlation r(row_index, tenant_id): {r_clust:+.5f}")
    print(f"  Is tenant_id strictly monotonically increasing: {is_sorted_tenant}")
    assert r_clust > 0.99, f"Correlation too low for clustered: {r_clust}"
    assert is_sorted_tenant, "Clustered data is not physically sorted by tenant_id"
    results["clustered_r"] = r_clust
    results["clustered_is_sorted"] = is_sorted_tenant

    # 1.3 CORRELATED COLS (AVI VIOLATION)
    print("\n--- 1.3 DIST_CORRELATED_COLS (Target: Strong AVI Violation) ---")
    batch_avi = gen.generate_batch(num_rows, mode=DataDistributionMode.DIST_CORRELATED_COLS)
    t_ids_avi = batch_avi["tenant_id"]
    stat_avi = batch_avi["status"]

    is_even = (t_ids_avi % 2) == 0
    even_count = int(np.sum(is_even))
    odd_count = num_rows - even_count

    even_stat0_pct = float(np.sum((stat_avi == 0) & is_even) / even_count) * 100.0
    odd_stat0_pct = float(np.sum((stat_avi == 0) & (~is_even)) / odd_count) * 100.0
    overall_stat0_pct = float(np.sum(stat_avi == 0) / num_rows) * 100.0

    # CBO Naive Independence Multiplier vs Actual Multiplier
    cbo_independent_prob = (1.0 / DEFAULT_NUM_TENANTS) * (overall_stat0_pct / 100.0)
    actual_even_joint_prob = (1.0 / DEFAULT_NUM_TENANTS) * (even_stat0_pct / 100.0)
    avi_discrepancy_ratio = actual_even_joint_prob / cbo_independent_prob

    print(f"  Total records: {num_rows:,} (Even tenants: {even_count:,}, Odd tenants: {odd_count:,})")
    print(f"  P(status=0 | tenant_id is EVEN): {even_stat0_pct:.2f}% (Expected ~95%)")
    print(f"  P(status=0 | tenant_id is ODD) : {odd_stat0_pct:.2f}% (Expected ~5%)")
    print(f"  Overall unconditional P(status=0): {overall_stat0_pct:.2f}%")
    print(f"  AVI Discrepancy Ratio (Actual / CBO Naive Estimate): {avi_discrepancy_ratio:.2f}x")

    assert 93.0 < even_stat0_pct < 97.0, f"Even status 0 pct unexpected: {even_stat0_pct}"
    assert 3.0 < odd_stat0_pct < 7.0, f"Odd status 0 pct unexpected: {odd_stat0_pct}"
    assert 1.8 < avi_discrepancy_ratio < 2.0, f"AVI discrepancy ratio unexpected: {avi_discrepancy_ratio}"

    results["even_stat0_pct"] = even_stat0_pct
    results["odd_stat0_pct"] = odd_stat0_pct
    results["avi_discrepancy_ratio"] = avi_discrepancy_ratio
    return results


def verify_query_generators(num_queries: int = 20_000) -> dict:
    print(f"\n=======================================================")
    print(f"TEST 2: Verifying Workload Query Generators ({num_queries:,} samples)")
    print(f"=======================================================")

    results = {}

    # Uniform Generator
    unif_gen = UniformGenerator(n=DEFAULT_NUM_TENANTS, seed=42)
    unif_samples = unif_gen.sample(num_queries)
    unif_mean = float(np.mean(unif_samples))
    unif_unique = len(np.unique(unif_samples))

    print(f"\n--- 2.1 Uniform Query Workload ---")
    print(f"  Sample count: {num_queries:,}")
    print(f"  Mean tenant_id: {unif_mean:.2f} (Theoretical: {DEFAULT_NUM_TENANTS / 2.0})")
    print(f"  Distinct tenants touched: {unif_unique:,} / {DEFAULT_NUM_TENANTS:,}")
    results["unif_mean"] = unif_mean
    results["unif_unique"] = unif_unique

    # Zipfian Generator (s = 0.99)
    zipf_gen = FastZipfianGenerator(n=DEFAULT_NUM_TENANTS, theta=0.99, seed=42)
    zipf_samples = zipf_gen.sample(num_queries)
    zipf_unique = len(np.unique(zipf_samples))

    # Top 1% tenant count
    top_1_pct_tenants = int(DEFAULT_NUM_TENANTS * 0.01)  # top 100 tenants
    top_1_pct_hits = int(np.sum(zipf_samples <= top_1_pct_tenants))
    top_1_pct_ratio = (top_1_pct_hits / num_queries) * 100.0

    top_1_tenant_hits = int(np.sum(zipf_samples == 1))
    top_1_tenant_ratio = (top_1_tenant_hits / num_queries) * 100.0

    print(f"\n--- 2.2 Scrambled Zipfian Workload (s = 0.99) ---")
    print(f"  Sample count: {num_queries:,}")
    print(f"  Distinct tenants touched: {zipf_unique:,} / {DEFAULT_NUM_TENANTS:,}")
    print(f"  Top 1% hottest tenants touched: {top_1_pct_ratio:.2f}% of all queries")
    print(f"  Single hottest tenant (#1) touched: {top_1_tenant_ratio:.2f}% of all queries")

    assert top_1_pct_ratio > 40.0, f"Zipfian skew too low: {top_1_pct_ratio}%"
    results["zipf_unique"] = zipf_unique
    results["zipf_top1_pct_ratio"] = top_1_pct_ratio
    results["zipf_top1_tenant_ratio"] = top_1_tenant_ratio
    return results


def verify_latency_tracker(num_samples: int = 10_000) -> dict:
    print(f"\n=======================================================")
    print(f"TEST 3: Verifying LatencyTracker & HdrHistogram ({num_samples:,} samples)")
    print(f"=======================================================")

    tracker = LatencyTracker()
    tracker.start()

    # Synthetic latency injection with precisely known percentiles:
    # 0 to 90%: 9,000 samples @ 1,000 us (1.0 ms)
    # 90 to 95%: 500 samples @ 5,000 us (5.0 ms)
    # 95 to 99%: 400 samples @ 20,000 us (20.0 ms)
    # 99 to 99.9%: 90 samples @ 100,000 us (100.0 ms)
    # 99.9 to 100%: 10 samples @ 500,000 us (500.0 ms)
    for _ in range(9_000):
        tracker.record_latency_us(1_000)
    for _ in range(500):
        tracker.record_latency_us(5_000)
    for _ in range(400):
        tracker.record_latency_us(20_000)
    for _ in range(90):
        tracker.record_latency_us(100_000)
    for _ in range(10):
        tracker.record_latency_us(500_000)

    # Context manager test
    with tracker.measure():
        time.sleep(0.002)  # 2 ms dummy execution

    tracker.stop()
    summary = tracker.get_summary()

    print("\n--- LatencyTracker Statistical Summary ---")
    for k, v in summary.items():
        print(f"  {k:18s}: {v}")

    # Percentiles validation (HdrHistogram 3 significant figures has ~1% resolution)
    assert summary["count"] == num_samples + 1, f"Count mismatch: {summary['count']}"
    assert 0.95 <= summary["p50_ms"] <= 1.05, f"p50 mismatch: {summary['p50_ms']}"
    assert 4.90 <= summary["p95_ms"] <= 5.10, f"p95 mismatch: {summary['p95_ms']}"
    assert 19.5 <= summary["p99_ms"] <= 20.5, f"p99 mismatch: {summary['p99_ms']}"
    assert 98.0 <= summary["p999_ms"] <= 102.0, f"p999 mismatch: {summary['p999_ms']}"
    assert 490.0 <= summary["max_ms"] <= 510.0, f"max_ms mismatch: {summary['max_ms']}"

    # Mathematical consistency: variance == stddev^2
    computed_var = round(summary["stddev_ms"] ** 2, 6)
    assert abs(summary["variance_ms2"] - computed_var) < 1e-4, "Variance mathematically inconsistent with stddev"
    print(f"\n  [OK] Mathematical consistency verified: stddev={summary['stddev_ms']} ms -> variance={summary['variance_ms2']} ms^2")

    # Test CSV Export
    csv_path = Path("results/summary_csv/phase_2_latency_verification.csv")
    tracker.export_percentiles_csv(csv_path)
    assert csv_path.exists(), "CSV export failed to create file"
    print(f"  [OK] Successfully exported CDF percentiles to: {csv_path.resolve()}")

    return summary


if __name__ == "__main__":
    t_start = time.perf_counter()
    dist_res = verify_distributions(100_000)
    query_res = verify_query_generators(20_000)
    latency_res = verify_latency_tracker(10_000)
    t_elapsed = time.perf_counter() - t_start

    print(f"\n=======================================================")
    print(f"ALL PHASE 2 VERIFICATIONS PASSED IN {t_elapsed:.2f} SECONDS!")
    print(f"=======================================================\n")
