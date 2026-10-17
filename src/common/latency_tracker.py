#!/usr/bin/env python3
"""
High-Precision Tail Latency Tracker
Project: Empirical Study of Indexing & Key Ordering on Tail Latency
Wraps HdrHistogram (1 us to 60,000,000 us, 3 significant figures)
Monotonic nanosecond measurement via time.perf_counter_ns()
"""

from __future__ import annotations

import csv
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, Optional, Union

from hdrh.histogram import HdrHistogram

from src.common.config import (
    HISTOGRAM_HIGHEST_VALUE_US,
    HISTOGRAM_LOWEST_VALUE_US,
    HISTOGRAM_SIGNIFICANT_FIGURES,
)


class LatencyTracker:
    """
    Thread-safe High-Resolution Latency Tracker backed by HdrHistogram.
    Records timings in microseconds and outputs publication-grade metrics in milliseconds.
    """

    def __init__(
        self,
        lowest_val_us: int = HISTOGRAM_LOWEST_VALUE_US,
        highest_val_us: int = HISTOGRAM_HIGHEST_VALUE_US,
        significant_figures: int = HISTOGRAM_SIGNIFICANT_FIGURES,
        track_wall_time: bool = True,
    ) -> None:
        self.lowest_val_us = lowest_val_us
        self.highest_val_us = highest_val_us
        self.significant_figures = significant_figures

        self.histogram = HdrHistogram(
            self.lowest_val_us, self.highest_val_us, self.significant_figures
        )
        self._lock = threading.Lock()

        self._start_time_ns: Optional[int] = None
        self._end_time_ns: Optional[int] = None
        if track_wall_time:
            self._start_time_ns = time.perf_counter_ns()

    def start(self) -> None:
        """Mark or reset the benchmark measurement start wall-clock time."""
        with self._lock:
            self._start_time_ns = time.perf_counter_ns()
            self._end_time_ns = None

    def stop(self) -> None:
        """Mark the benchmark measurement end wall-clock time."""
        with self._lock:
            self._end_time_ns = time.perf_counter_ns()

    def record_latency_ns(self, latency_ns: int) -> int:
        """
        Record operation latency in nanoseconds.
        Converts to microseconds and clamps within histogram tracking bounds.
        Returns the recorded microsecond value.
        """
        latency_us = latency_ns // 1000
        if latency_us < self.lowest_val_us:
            latency_us = self.lowest_val_us
        elif latency_us > self.highest_val_us:
            latency_us = self.highest_val_us

        with self._lock:
            self.histogram.record_value(latency_us)

        return latency_us

    def record_latency_us(self, latency_us: int) -> int:
        """Record operation latency directly in microseconds."""
        clamped_us = max(
            self.lowest_val_us, min(latency_us, self.highest_val_us)
        )
        with self._lock:
            self.histogram.record_value(clamped_us)
        return clamped_us

    @contextmanager
    def measure(self) -> Iterator[None]:
        """
        Context manager measuring execution block with monotonic nanosecond timer.
        Usage:
            with tracker.measure():
                execute_query()
        """
        t0 = time.perf_counter_ns()
        try:
            yield
        finally:
            t1 = time.perf_counter_ns()
            self.record_latency_ns(t1 - t0)

    def merge(self, other: LatencyTracker) -> None:
        """Merge counts from another LatencyTracker into this tracker."""
        with self._lock:
            with other._lock:
                self.histogram.add(other.histogram)

    def reset(self) -> None:
        """Reset all recorded metrics and timing counters."""
        with self._lock:
            self.histogram.reset()
            self._start_time_ns = time.perf_counter_ns()
            self._end_time_ns = None

    def get_summary(self) -> Dict[str, Union[int, float]]:
        """
        Computes exact statistical summary metrics.
        All latencies are converted from microseconds to milliseconds.
        """
        with self._lock:
            total_count = self.histogram.get_total_count()

            # Elapsed wall time calculation
            if self._start_time_ns is not None:
                end_time = self._end_time_ns or time.perf_counter_ns()
                elapsed_sec = max(1e-9, (end_time - self._start_time_ns) / 1e9)
            else:
                elapsed_sec = 0.0

            throughput = total_count / elapsed_sec if elapsed_sec > 0 else 0.0

            if total_count == 0:
                return {
                    "count": 0,
                    "elapsed_seconds": round(elapsed_sec, 4),
                    "throughput_ops": 0.0,
                    "mean_ms": 0.0,
                    "stddev_ms": 0.0,
                    "variance_ms2": 0.0,
                    "p50_ms": 0.0,
                    "p95_ms": 0.0,
                    "p99_ms": 0.0,
                    "p999_ms": 0.0,
                    "max_ms": 0.0,
                }

            mean_ms = round(self.histogram.get_mean_value() / 1000.0, 4)
            stddev_ms = round(self.histogram.get_stddev() / 1000.0, 4)
            variance_ms2 = round(stddev_ms ** 2, 6)

            p50_ms = round(self.histogram.get_value_at_percentile(50.0) / 1000.0, 4)
            p95_ms = round(self.histogram.get_value_at_percentile(95.0) / 1000.0, 4)
            p99_ms = round(self.histogram.get_value_at_percentile(99.0) / 1000.0, 4)
            p999_ms = round(self.histogram.get_value_at_percentile(99.9) / 1000.0, 4)
            max_ms = round(self.histogram.get_max_value() / 1000.0, 4)

            return {
                "count": total_count,
                "elapsed_seconds": round(elapsed_sec, 4),
                "throughput_ops": round(throughput, 2),
                "mean_ms": mean_ms,
                "stddev_ms": stddev_ms,
                "variance_ms2": variance_ms2,
                "p50_ms": p50_ms,
                "p95_ms": p95_ms,
                "p99_ms": p99_ms,
                "p999_ms": p999_ms,
                "max_ms": max_ms,
            }

    def export_percentiles_csv(self, filepath: Union[str, Path]) -> None:
        """
        Export detailed CDF percentile distribution to CSV file.
        Percentiles: 0 to 100 including 90, 95, 99, 99.9, 99.99.
        """
        target = Path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)

        percentiles = [
            10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0,
            90.0, 95.0, 98.0, 99.0, 99.5, 99.9, 99.99, 100.0,
        ]

        with self._lock:
            with open(target, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["percentile", "latency_ms", "latency_us", "total_count"]
                )
                for p in percentiles:
                    val_us = self.histogram.get_value_at_percentile(p)
                    val_ms = val_us / 1000.0
                    writer.writerow([p, round(val_ms, 4), val_us, self.histogram.get_total_count()])
