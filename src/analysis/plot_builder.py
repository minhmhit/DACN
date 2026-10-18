#!/usr/bin/env python3
"""
Scientific Publication Chart Generator (300 DPI)
Project: Empirical Study of Indexing & Key Ordering on Tail Latency
(PostgreSQL B-Tree vs. RocksDB LSM-Tree)
Chapter 3 Benchmark Figures

Outputs:
  1. Hinh_3_1_Postgres_Latency_Order.png
  2. Hinh_3_2_Postgres_CBO_Correlation_Blocks.png
  3. Hinh_3_3_RocksDB_Latency_KeyOrder.png
  4. Hinh_3_4_RocksDB_BloomFilter_ReadAmp.png
  5. Hinh_3_5_Timeseries_Tail_Latency_Spikes.png
  6. Hinh_3_6_CDF_Tail_Latency.png
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# Set workspace root
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE_ROOT))

# Publication Styling Configuration
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Arial", "Segoe UI", "Tahoma"],
    "font.size": 10.5,
    "axes.titlesize": 12.0,
    "axes.labelsize": 11.0,
    "xtick.labelsize": 9.5,
    "ytick.labelsize": 9.5,
    "legend.fontsize": 9.0,
    "figure.titlesize": 13.0,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "axes.grid": True,
    "grid.alpha": 0.35,
    "grid.linestyle": "--",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

# Harmonious Scientific Palette
COLOR_OPT = "#1f77b4"      # Deep Sapphire Blue for I_opt / K_opt
COLOR_INV = "#d62728"      # Crimson Red for I_inv / K_inv
COLOR_NONE = "#7f7f7f"     # Slate Grey for I_none
COLOR_TEAL = "#0284c7"
COLOR_AMBER = "#f59e0b"

PLOTS_DIR = WORKSPACE_ROOT / "results" / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def load_csv(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ==============================================================================
# HÌNH 3.1: POSTGRESQL - ẢNH HƯỞNG CỦA THỨ TỰ CHỈ MỤC ĐẾN ĐỘ TRỄ VÀ THÔNG LƯỢNG
# ==============================================================================
def plot_fig_3_1_postgres_latency_order():
    pg_csv = WORKSPACE_ROOT / "results/summary_csv/postgres_matrix_results.csv"
    data = load_csv(pg_csv)

    threads = [1, 4, 8, 16, 32]
    workloads = ["Workload_C", "Workload_B", "Workload_A"]
    wl_labels = {
        "Workload_C": "Workload C (100% Read)",
        "Workload_B": "Workload B (95% Read / 5% Write)",
        "Workload_A": "Workload A (50% Read / 50% Write)",
    }

    fig, axes = plt.subplots(1, 2, figsize=(15.0, 6.8), sharex=True)
    # Ample whitespace: top=0.78 leaves substantial room below suptitle (y=0.95)
    # bottom=0.22 leaves clean space for external legends outside the chart area
    plt.subplots_adjust(top=0.78, bottom=0.22, left=0.08, right=0.96, wspace=0.22)

    markers = {"Workload_C": "o", "Workload_B": "s", "Workload_A": "^"}

    # Subplot 1: Thông lượng (Throughput)
    ax1 = axes[0]
    for wl in workloads:
        sub_opt = [r for r in data if r["workload"] == wl and r["variant"] == "I_OPT"]
        sub_opt.sort(key=lambda x: int(x["threads"]))
        tput_opt = [float(r["total_throughput_ops"]) for r in sub_opt]
        ax1.plot(
            threads, tput_opt,
            marker=markers[wl], markersize=7, linewidth=2.2,
            color=COLOR_OPT,
            label=f"$I_{{opt}}$ - {wl_labels[wl]}"
        )

        sub_inv = [r for r in data if r["workload"] == wl and r["variant"] == "I_INV_LOW_SEL"]
        sub_inv.sort(key=lambda x: int(x["threads"]))
        tput_inv = [float(r["total_throughput_ops"]) for r in sub_inv]
        ax1.plot(
            threads, tput_inv,
            marker=markers[wl], markersize=7, linewidth=2.0, linestyle="--",
            color=COLOR_INV,
            label=f"$I_{{inv}}$ - {wl_labels[wl]}"
        )

    ax1.axhline(21.5, color=COLOR_NONE, linestyle=":", linewidth=2.0, label="$I_{none}$ (Không chỉ mục: ~21.5 ops/s)")
    ax1.set_title("(a) Thông lượng xử lý theo số luồng đồng thời", pad=12, fontweight="bold")
    ax1.set_xlabel("Số luồng đồng thời (Threads)")
    ax1.set_ylabel("Thông lượng xử lý (ops/giây)")
    ax1.set_xticks(threads)
    ax1.set_ylim(bottom=0, top=4000)
    ax1.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))

    # Subplot 2: Độ trễ đuôi p99
    ax2 = axes[1]
    for wl in workloads:
        sub_opt = [r for r in data if r["workload"] == wl and r["variant"] == "I_OPT"]
        sub_opt.sort(key=lambda x: int(x["threads"]))
        p99_opt = [float(r["p99_ms"]) for r in sub_opt]
        ax2.plot(
            threads, p99_opt,
            marker=markers[wl], markersize=7, linewidth=2.2,
            color=COLOR_OPT,
            label=f"$I_{{opt}}$ - {wl_labels[wl]}"
        )

        sub_inv = [r for r in data if r["workload"] == wl and r["variant"] == "I_INV_LOW_SEL"]
        sub_inv.sort(key=lambda x: int(x["threads"]))
        p99_inv = [float(r["p99_ms"]) for r in sub_inv]
        ax2.plot(
            threads, p99_inv,
            marker=markers[wl], markersize=7, linewidth=2.0, linestyle="--",
            color=COLOR_INV,
            label=f"$I_{{inv}}$ - {wl_labels[wl]}"
        )

    ax2.axhline(46.5, color=COLOR_NONE, linestyle=":", linewidth=2.0, label="$I_{none}$ Baseline ($p_{50} = 46.5$ ms)")
    ax2.set_title("(b) Độ trễ phân vị đuôi $p_{99}$ theo số luồng đồng thời", pad=12, fontweight="bold")
    ax2.set_xlabel("Số luồng đồng thời (Threads)")
    ax2.set_ylabel("Độ trễ phân vị $p_{99}$ (mili-giây)")
    ax2.set_xticks(threads)
    ax2.set_ylim(bottom=0, top=65)

    ax2.annotate(
        "Bùng nổ $p_{99} = 55.49$ ms\n(Nghẽn quét lát rộng $I_{inv}$)",
        xy=(32, 55.487), xytext=(20, 58),
        arrowprops=dict(facecolor=COLOR_INV, shrink=0.08, width=1.5, headwidth=6),
        fontsize=8.5, fontweight="bold", color=COLOR_INV
    )

    # Place common legend outside the plots at the bottom
    handles, labels = ax1.get_legend_handles_labels()
    fig.legend(
        handles, labels,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.03),
        ncol=4,
        frameon=True,
        framealpha=0.95,
        fontsize=9.0
    )

    fig.suptitle(
        "Hình 3.1: So sánh Thông lượng và Độ trễ phân vị đuôi $p_{99}$ trên PostgreSQL (B-Tree)\ngiữa Chỉ mục tối ưu ($I_{opt}$), Chỉ mục nghịch đảo ($I_{inv}$) và Không chỉ mục ($I_{none}$)",
        y=0.95, fontweight="bold"
    )

    out_path = PLOTS_DIR / "Hinh_3_1_Postgres_Latency_Order.png"
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()
    print(f"[OK] Generated: {out_path.name}")


# ==============================================================================
# HÌNH 3.2: POSTGRESQL - CHUYỂN DỊCH KẾ HOẠCH CBO & TRÀN BỘ NHỚ BITMAP (LOSSY)
# ==============================================================================
def plot_fig_3_2_postgres_cbo_correlation_blocks():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.0, 6.8))
    plt.subplots_adjust(top=0.78, bottom=0.22, left=0.08, right=0.96, wspace=0.22)

    # Panel A: CBO Cost và Shared Read Blocks cho I_opt, I_inv, I_none
    variants = ["$I_{opt}$\n(tenant, status, time)", "$I_{inv}$\n(status, time, tenant)", "$I_{none}$\n(Không chỉ mục)"]
    cbo_costs = [4.07, 351.72, 15430.87]
    read_blocks = [3, 83, 15920]

    x = np.arange(len(variants))
    width = 0.35

    bar1 = ax1.bar(x - width/2, cbo_costs, width, label="Chi phí CBO (Total Cost)", color=COLOR_TEAL, edgecolor="black", linewidth=0.8)
    bar2 = ax1.bar(x + width/2, read_blocks, width, label="Khối đọc đĩa (Shared Read Blocks)", color=COLOR_AMBER, edgecolor="black", linewidth=0.8)

    ax1.set_yscale("log")
    ax1.set_title("(a) Chi phí CBO và Khối I/O đọc đĩa theo cấu hình chỉ mục", pad=12, fontweight="bold")
    ax1.set_ylabel("Giá trị trên thang đo Logarit (log10)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(variants, fontweight="bold")
    ax1.set_ylim(1, 400000)

    # Value labels on bars
    for rect in bar1:
        h = rect.get_height()
        ax1.text(rect.get_x() + rect.get_width()/2., h * 1.35, f"{h:,.1f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold")
    for rect in bar2:
        h = rect.get_height()
        ax1.text(rect.get_x() + rect.get_width()/2., h * 1.35, f"{int(h):,}", ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    # Clean annotation box in open space
    ax1.text(0.38, 0.75, "Chi phí tăng 86.4×\nKhối đọc tăng 27.7×", transform=ax1.transAxes,
             bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor=COLOR_INV, alpha=0.95),
             fontsize=9, color=COLOR_INV, fontweight="bold")

    # Legend outside Panel A
    ax1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, frameon=True, framealpha=0.95)

    # Panel B: Tràn bộ nhớ Bitmap (work_mem 4MB vs 64kB)
    mem_cases = ["work_mem = 4MB\n(Đủ bộ nhớ)", "work_mem = 64kB\n(Bộ nhớ cạn kiệt)"]
    exact_blocks = [8224, 977]
    lossy_blocks = [0, 7247]

    x2 = np.arange(len(mem_cases))
    w2 = 0.40

    b_exact = ax2.bar(x2, exact_blocks, w2, label="Exact Heap Blocks (Khối chính xác)", color=COLOR_OPT, edgecolor="black", linewidth=0.8)
    b_lossy = ax2.bar(x2, lossy_blocks, w2, bottom=exact_blocks, label="Lossy Heap Blocks (Khối tổn thất/suy hao)", color=COLOR_INV, edgecolor="black", linewidth=0.8)

    ax2.set_title("(b) Hiện tượng suy thoái tràn bộ nhớ Bitmap Heap Scan", pad=12, fontweight="bold")
    ax2.set_ylabel("Số lượng khối trang Heap 8KB truy cập")
    ax2.set_xticks(x2)
    ax2.set_xticklabels(mem_cases, fontweight="bold")
    ax2.set_ylim(0, 12500)
    ax2.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))

    ax2.text(x2[0], 8224 / 2, "Exact:\n8,224", ha="center", va="center", color="white", fontweight="bold", fontsize=9.5)
    ax2.text(x2[1], 977 / 2, "Exact: 977", ha="center", va="center", color="white", fontweight="bold", fontsize=8.5)
    ax2.text(x2[1], 977 + 7247 / 2, "Lossy:\n7,247 trang", ha="center", va="center", color="white", fontweight="bold", fontsize=9.5)

    ax2.annotate(
        "Tràn bộ nhớ Bitmap:\n7.247 trang bị hạ cấp thành Lossy\nÉp CPU kiểm tra lại 340.023 bản ghi!",
        xy=(x2[1], 8224), xytext=(x2[1] - 0.48, 9800),
        arrowprops=dict(facecolor=COLOR_INV, shrink=0.08, width=1.5, headwidth=6),
        fontsize=8.5, fontweight="bold", color=COLOR_INV,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=COLOR_INV)
    )

    # Legend outside Panel B
    ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, frameon=True, framealpha=0.95)

    fig.suptitle(
        "Hình 3.2: Phân tích cơ chế suy thoái vi kiến trúc trên PostgreSQL:\nChuyển dịch kế hoạch thực thi CBO và Sự sụp đổ của Bitmap Heap Scan do cạn kiệt work_mem",
        y=0.95, fontweight="bold"
    )

    out_path = PLOTS_DIR / "Hinh_3_2_Postgres_CBO_Correlation_Blocks.png"
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()
    print(f"[OK] Generated: {out_path.name}")


# ==============================================================================
# HÌNH 3.3: ROCKSDB - ĐỘ TRỄ VÀ THÔNG LƯỢNG GIỮA KHÓA THUẬN K_opt VÀ NGHỊCH ĐẢO K_inv
# ==============================================================================
def plot_fig_3_3_rocksdb_latency_key_order():
    rdb_csv = WORKSPACE_ROOT / "results/summary_csv/rocksdb_matrix_results.csv"
    data = load_csv(rdb_csv)

    threads = [1, 4, 8, 16, 32]
    workloads = ["Workload_C", "Workload_B", "Workload_A"]
    wl_labels = {
        "Workload_C": "Workload C (100% Read)",
        "Workload_B": "Workload B (95R / 5W)",
        "Workload_A": "Workload A (50R / 50W)",
    }
    markers = {"Workload_C": "o", "Workload_B": "s", "Workload_A": "^"}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.0, 6.8))
    plt.subplots_adjust(top=0.78, bottom=0.22, left=0.08, right=0.96, wspace=0.22)

    # Subplot 1: Thông lượng (Throughput) trên thang đo Logarit
    for wl in workloads:
        sub_opt = [r for r in data if r["workload"] == wl and r["variant"] == "k_opt"]
        sub_opt.sort(key=lambda x: int(x["threads"]))
        tput_opt = [float(r["total_throughput_ops"]) for r in sub_opt]
        ax1.plot(
            threads, tput_opt,
            marker=markers[wl], markersize=7, linewidth=2.2,
            color=COLOR_OPT,
            label=f"$K_{{opt}}$ - {wl_labels[wl]}"
        )

        sub_inv = [r for r in data if r["workload"] == wl and r["variant"] == "k_inv"]
        sub_inv.sort(key=lambda x: int(x["threads"]))
        tput_inv = [float(r["total_throughput_ops"]) for r in sub_inv]
        ax1.plot(
            threads, tput_inv,
            marker=markers[wl], markersize=7, linewidth=2.0, linestyle="--",
            color=COLOR_INV,
            label=f"$K_{{inv}}$ - {wl_labels[wl]}"
        )

    ax1.set_yscale("log")
    ax1.set_title("(a) Thông lượng xử lý (Logarit) theo số luồng đồng thời", pad=12, fontweight="bold")
    ax1.set_xlabel("Số luồng đồng thời (Threads)")
    ax1.set_ylabel("Thông lượng xử lý (ops/giây, log10)")
    ax1.set_xticks(threads)
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f"{y:,.0f}"))

    ax1.annotate(
        "K_opt: Đỉnh 255.264 ops/s\n(Mở rộng đa luồng mượt mà)",
        xy=(16, 255264), xytext=(12, 100000),
        arrowprops=dict(facecolor=COLOR_OPT, shrink=0.08, width=1.5, headwidth=6),
        fontsize=8.5, fontweight="bold", color=COLOR_OPT
    )
    ax1.annotate(
        "K_inv: Sụp đổ < 2.000 ops/s\n(Chậm hơn 300× - 400×)",
        xy=(32, 989.7), xytext=(18, 2500),
        arrowprops=dict(facecolor=COLOR_INV, shrink=0.08, width=1.5, headwidth=6),
        fontsize=8.5, fontweight="bold", color=COLOR_INV
    )

    # Subplot 2: Độ trễ phân vị p50 và p99 trên thang đo Logarit
    for wl, style in [("Workload_C", "-"), ("Workload_A", "-.")]:
        sub_opt = [r for r in data if r["workload"] == wl and r["variant"] == "k_opt"]
        sub_opt.sort(key=lambda x: int(x["threads"]))
        p99_opt = [float(r["p99_ms"]) for r in sub_opt]

        sub_inv = [r for r in data if r["workload"] == wl and r["variant"] == "k_inv"]
        sub_inv.sort(key=lambda x: int(x["threads"]))
        p99_inv = [float(r["p99_ms"]) for r in sub_inv]

        ax2.plot(
            threads, p99_opt,
            marker="o" if wl == "Workload_C" else "^", markersize=6.5, linewidth=2.0, linestyle=style,
            color=COLOR_OPT,
            label=f"$K_{{opt}}$ $p_{{99}}$ ({wl.replace('_', ' ')})"
        )
        ax2.plot(
            threads, p99_inv,
            marker="o" if wl == "Workload_C" else "^", markersize=6.5, linewidth=2.0, linestyle=style,
            color=COLOR_INV,
            label=f"$K_{{inv}}$ $p_{{99}}$ ({wl.replace('_', ' ')})"
        )

    ax2.set_yscale("log")
    ax2.set_title("(b) Độ trễ phân vị đuôi $p_{99}$ (Logarit) theo số luồng", pad=12, fontweight="bold")
    ax2.set_xlabel("Số luồng đồng thời (Threads)")
    ax2.set_ylabel("Độ trễ $p_{99}$ (mili-giây, log10)")
    ax2.set_xticks(threads)
    ax2.set_ylim(0.02, 700)
    ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f"{y:g} ms"))

    ax2.annotate(
        "K_inv: p99 bùng nổ 220.57 ms\n(Chậm hơn 2.400× so với K_opt!)",
        xy=(32, 219.195), xytext=(15, 360),
        arrowprops=dict(facecolor=COLOR_INV, shrink=0.08, width=1.5, headwidth=6),
        fontsize=8.5, fontweight="bold", color=COLOR_INV,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=COLOR_INV)
    )

    # Place common legend outside the plots at the bottom
    handles1, labels1 = ax1.get_legend_handles_labels()
    fig.legend(
        handles1, labels1,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.03),
        ncol=3,
        frameon=True,
        framealpha=0.95,
        fontsize=9.0
    )

    fig.suptitle(
        "Hình 3.3: So sánh Thông lượng và Độ trễ phân vị đuôi trên RocksDB (LSM-Tree)\ngiữa Khóa ghép tối ưu ($K_{opt}$) và Khóa ghép nghịch đảo ($K_{inv}$)",
        y=0.95, fontweight="bold"
    )

    out_path = PLOTS_DIR / "Hinh_3_3_RocksDB_Latency_KeyOrder.png"
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()
    print(f"[OK] Generated: {out_path.name}")


# ==============================================================================
# HÌNH 3.4: ROCKSDB - HIỆU QUẢ BLOOM FILTER & KHUẾCH ĐẠI ĐỌC (READ AMPLIFICATION)
# ==============================================================================
def plot_fig_3_4_rocksdb_bloom_read_amp():
    rdb_json = WORKSPACE_ROOT / "results/raw_json/rocksdb_perf_verification.json"
    data = load_json(rdb_json)

    k_opt = data["k_opt"]
    k_inv = data["k_inv"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.0, 6.8))
    plt.subplots_adjust(top=0.78, bottom=0.22, left=0.08, right=0.96, wspace=0.22)

    # Panel A: Prefix Bloom Filter Pruning Efficiency
    labels_filter = ["SSTable bị loại trừ\n(bloom_sst_miss_count)", "SSTable trúng bộ lọc\n(bloom_sst_hit_count)"]
    x1 = np.arange(len(labels_filter))
    w = 0.35

    opt_counts = [k_opt["total_bloom_sst_misses"], k_opt["total_bloom_sst_hits"]]
    inv_counts = [k_inv["total_bloom_sst_misses"], k_inv["total_bloom_sst_hits"]]

    b1 = ax1.bar(x1 - w/2, opt_counts, w, label="$K_{opt}$ (Khóa tối ưu)", color=COLOR_OPT, edgecolor="black", linewidth=0.8)
    b2 = ax1.bar(x1 + w/2, inv_counts, w, label="$K_{inv}$ (Khóa nghịch đảo)", color=COLOR_INV, edgecolor="black", linewidth=0.8)

    ax1.set_title("(a) Số lần kiểm tra bộ lọc Prefix Bloom Filter", pad=12, fontweight="bold")
    ax1.set_ylabel("Tổng số lần kiểm tra qua 1.000 truy vấn")
    ax1.set_xticks(x1)
    ax1.set_xticklabels(labels_filter, fontweight="bold")
    ax1.set_ylim(0, 6300)

    for rect in b1:
        h = rect.get_height()
        ax1.text(rect.get_x() + rect.get_width()/2., h + 90, f"{int(h):,}", ha="center", va="bottom", fontweight="bold", fontsize=9)
    for rect in b2:
        h = rect.get_height()
        ax1.text(rect.get_x() + rect.get_width()/2., h + 90, f"{int(h):,}", ha="center", va="bottom", fontweight="bold", fontsize=9)

    ax1.annotate(
        "K_inv: Cắt tỉa = 0!\n(Vô hiệu hóa 100% Bloom Filter)",
        xy=(x1[0] + w/2, 10), xytext=(x1[0] - 0.22, 1400),
        arrowprops=dict(facecolor=COLOR_INV, shrink=0.08, width=1.5, headwidth=6),
        fontsize=9, fontweight="bold", color=COLOR_INV,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=COLOR_INV)
    )

    ax1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, frameon=True, framealpha=0.95)

    # Panel B: Khuếch đại so sánh khóa và đọc khối đĩa
    metrics = ["So sánh khóa / op\n(user_key_comparisons)", "Đọc khối đĩa / op\n(block_read_count)", "Trúng Block Cache / op\n(block_cache_hit_count)"]
    opt_metrics = [k_opt["avg_key_comparisons"], k_opt["avg_block_reads"], k_opt["total_cache_hits"] / k_opt["num_queries"]]
    inv_metrics = [k_inv["avg_key_comparisons"], k_inv["avg_block_reads"], k_inv["total_cache_hits"] / k_inv["num_queries"]]

    x2 = np.arange(len(metrics))
    b3 = ax2.bar(x2 - w/2, opt_metrics, w, label="$K_{opt}$ (Khóa tối ưu)", color=COLOR_OPT, edgecolor="black", linewidth=0.8)
    b4 = ax2.bar(x2 + w/2, inv_metrics, w, label="$K_{inv}$ (Khóa nghịch đảo)", color=COLOR_INV, edgecolor="black", linewidth=0.8)

    ax2.set_yscale("log")
    ax2.set_title("(b) Chỉ số vi kiến trúc PerfContext trung bình mỗi truy vấn", pad=12, fontweight="bold")
    ax2.set_ylabel("Số lượng trên thang đo Logarit (log10)")
    ax2.set_xticks(x2)
    ax2.set_xticklabels(metrics, fontweight="bold")
    ax2.set_ylim(0.05, 500000)
    ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f"{y:g}"))

    for rect in b3:
        h = rect.get_height()
        ax2.text(rect.get_x() + rect.get_width()/2., h * 1.45, f"{h:,.1f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold")
    for rect in b4:
        h = rect.get_height()
        ax2.text(rect.get_x() + rect.get_width()/2., h * 1.45, f"{h:,.1f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    ax2.text(0.48, 0.78, "So sánh khóa: Tăng 342.0×\nĐọc đĩa: Tăng 15.4×\nCache thrashing: Tăng 79.3×",
             transform=ax2.transAxes,
             bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor=COLOR_INV, alpha=0.9),
             fontsize=9, color=COLOR_INV, fontweight="bold")

    ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, frameon=True, framealpha=0.95)

    fig.suptitle(
        "Hình 3.4: Bằng chứng vi kiến trúc RocksDB: Sự vô hiệu hóa Prefix Bloom Filter\nvà Khuếch đại đọc (Read Amplification) / Bùng nổ so sánh khóa trên CPU",
        y=0.95, fontweight="bold"
    )

    out_path = PLOTS_DIR / "Hinh_3_4_RocksDB_BloomFilter_ReadAmp.png"
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()
    print(f"[OK] Generated: {out_path.name}")


# ==============================================================================
# HÌNH 3.5: CHUỖI THỜI GIAN THEO TỪNG GIÂY CỦA ĐỘ TRỄ ĐUÔI (LATENCY SPIKES)
# ==============================================================================
def plot_fig_3_5_timeseries_tail_latency_spikes():
    ts_csv = WORKSPACE_ROOT / "results/summary_csv/timeseries_latency_spikes.csv"
    data = load_csv(ts_csv)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15.0, 10.5))
    # Generous top and vertical spacing
    plt.subplots_adjust(top=0.86, bottom=0.10, left=0.08, right=0.96, hspace=0.60)

    # Filter for Workload A (50/50), 32 threads, ensure read_ops > 0
    pg_opt_samples = [r for r in data if r["system"] == "PostgreSQL" and r["workload"] == "Workload_A" and r["variant"] == "I_OPT" and r["threads"] == "32" and float(r["read_ops"]) > 0]
    pg_inv_samples = [r for r in data if r["system"] == "PostgreSQL" and r["workload"] == "Workload_A" and r["variant"] == "I_INV_LOW_SEL" and r["threads"] == "32" and float(r["read_ops"]) > 0]

    rdb_opt_samples = [r for r in data if r["system"] == "RocksDB" and r["workload"] == "Workload_A" and r["variant"] == "k_opt" and r["threads"] == "32" and float(r["read_ops"]) > 0]
    rdb_inv_samples = [r for r in data if r["system"] == "RocksDB" and r["workload"] == "Workload_A" and r["variant"] == "k_inv" and r["threads"] == "32" and float(r["read_ops"]) > 0]

    # Top plot: PostgreSQL
    x_pg_opt = [i + 1 for i in range(len(pg_opt_samples))]
    y_pg_opt_p99 = [float(r["read_p99_ms"]) for r in pg_opt_samples]
    y_pg_opt_p95 = [float(r["read_p95_ms"]) for r in pg_opt_samples]

    x_pg_inv = [i + 1 for i in range(len(pg_inv_samples))]
    y_pg_inv_p99 = [float(r["read_p99_ms"]) for r in pg_inv_samples]
    y_pg_inv_p95 = [float(r["read_p95_ms"]) for r in pg_inv_samples]

    ax1.plot(x_pg_opt, y_pg_opt_p99, marker="o", markersize=7, linewidth=2.2, color=COLOR_OPT, label="$I_{opt}$ - $p_{99}$")
    ax1.plot(x_pg_opt, y_pg_opt_p95, marker="s", markersize=6, linewidth=1.8, linestyle="--", color=COLOR_TEAL, label="$I_{opt}$ - $p_{95}$")

    ax1.plot(x_pg_inv, y_pg_inv_p99, marker="o", markersize=7, linewidth=2.2, color=COLOR_INV, label="$I_{inv}$ - $p_{99}$")
    ax1.plot(x_pg_inv, y_pg_inv_p95, marker="s", markersize=6, linewidth=1.8, linestyle="--", color=COLOR_AMBER, label="$I_{inv}$ - $p_{95}$")

    ax1.set_title("(a) PostgreSQL 17: Chuỗi thời gian độ trễ đọc dưới Workload A (50% Read / 50% Write, 32 Threads)", pad=14, fontweight="bold")
    ax1.set_xlabel("Thời gian thực nghiệm (Giây thứ n)")
    ax1.set_ylabel("Độ trễ đọc (mili-giây)")
    ax1.set_xticks(range(1, max(len(x_pg_opt), len(x_pg_inv)) + 1))
    ax1.set_ylim(0, 80)
    # Legend outside below the subplot
    ax1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=4, frameon=True, framealpha=0.95)

    if y_pg_inv_p99:
        max_pg_idx = int(np.argmax(y_pg_inv_p99))
        spike_val = y_pg_inv_p99[max_pg_idx]
        ax1.annotate(
            f"Đỉnh nhọn p99 = {spike_val:.2f} ms\n(Tranh chấp chốt WAL & Page Split)",
            xy=(x_pg_inv[max_pg_idx], spike_val), xytext=(x_pg_inv[max_pg_idx] + 0.15, spike_val + 3),
            arrowprops=dict(facecolor=COLOR_INV, shrink=0.08, width=1.5, headwidth=6),
            fontsize=8.5, fontweight="bold", color=COLOR_INV,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=COLOR_INV)
        )

    # Bottom plot: RocksDB
    x_rdb_opt = [i + 1 for i in range(len(rdb_opt_samples))]
    y_rdb_opt_p99 = [float(r["read_p99_ms"]) for r in rdb_opt_samples]
    y_rdb_opt_p95 = [float(r["read_p95_ms"]) for r in rdb_opt_samples]

    x_rdb_inv = [i + 1 for i in range(len(rdb_inv_samples))]
    y_rdb_inv_p99 = [float(r["read_p99_ms"]) for r in rdb_inv_samples]
    y_rdb_inv_p95 = [float(r["read_p95_ms"]) for r in rdb_inv_samples]

    ax2.plot(x_rdb_opt, y_rdb_opt_p99, marker="o", markersize=7, linewidth=2.2, color=COLOR_OPT, label="$K_{opt}$ - $p_{99}$")
    ax2.plot(x_rdb_opt, y_rdb_opt_p95, marker="s", markersize=6, linewidth=1.8, linestyle="--", color=COLOR_TEAL, label="$K_{opt}$ - $p_{95}$")

    ax2.plot(x_rdb_inv, y_rdb_inv_p99, marker="o", markersize=7, linewidth=2.2, color=COLOR_INV, label="$K_{inv}$ - $p_{99}$")
    ax2.plot(x_rdb_inv, y_rdb_inv_p95, marker="s", markersize=6, linewidth=1.8, linestyle="--", color=COLOR_AMBER, label="$K_{inv}$ - $p_{95}$")

    ax2.set_title("(b) RocksDB 9.10: Chuỗi thời gian độ trễ đọc dưới Workload A (50% Read / 50% Write, 32 Threads)", pad=14, fontweight="bold")
    ax2.set_xlabel("Thời gian thực nghiệm (Giây thứ n)")
    ax2.set_ylabel("Độ trễ đọc (mili-giây)")
    ax2.set_xticks(range(1, max(len(x_rdb_opt), len(x_rdb_inv)) + 1))
    ax2.set_ylim(0, 270)
    # Legend outside below the subplot
    ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=4, frameon=True, framealpha=0.95)

    if y_rdb_inv_p99:
        max_rdb_idx = int(np.argmax(y_rdb_inv_p99))
        spike_rdb_val = y_rdb_inv_p99[max_rdb_idx]
        ax2.annotate(
            f"Đỉnh nhọn p99 = {spike_rdb_val:.2f} ms\n(Xả MemTable & Leveled Compaction)",
            xy=(x_rdb_inv[max_rdb_idx], spike_rdb_val), xytext=(x_rdb_inv[max_rdb_idx] - 0.95, spike_rdb_val - 45),
            arrowprops=dict(facecolor=COLOR_INV, shrink=0.08, width=1.5, headwidth=6),
            fontsize=8.5, fontweight="bold", color=COLOR_INV,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=COLOR_INV)
        )

    fig.suptitle(
        "Hình 3.5: Chuỗi thời gian độ trễ đọc theo từng giây (Time-Series Latency Spikes)\nminh họa các xung đột tài nguyên nền do Phân tách trang B-Tree và Nén gộp tầng LSM-Tree",
        y=0.96, fontweight="bold"
    )

    out_path = PLOTS_DIR / "Hinh_3_5_Timeseries_Tail_Latency_Spikes.png"
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()
    print(f"[OK] Generated: {out_path.name}")


# ==============================================================================
# HÌNH 3.6: PHÂN PHỐI TÍCH LŨY (CDF) CỦA ĐỘ TRỄ ĐUÔI NẶNG (HEAVY-TAIL DISTRIBUTION)
# ==============================================================================
def plot_fig_3_6_cdf_tail_latency():
    pg_csv = WORKSPACE_ROOT / "results/summary_csv/postgres_matrix_results.csv"
    rdb_csv = WORKSPACE_ROOT / "results/summary_csv/rocksdb_matrix_results.csv"

    pg_data = load_csv(pg_csv)
    rdb_data = load_csv(rdb_csv)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.0, 6.8))
    # Wide whitespace at top (top=0.78, suptitle at y=0.95) and bottom (0.22)
    plt.subplots_adjust(top=0.78, bottom=0.22, left=0.08, right=0.96, wspace=0.22)

    # Standard quantile levels
    quantiles = [0.50, 0.95, 0.99, 0.999, 1.00]

    # 1. PostgreSQL CDF under 32 threads, Workload A
    pg_opt_row = next(r for r in pg_data if r["variant"] == "I_OPT" and r["workload"] == "Workload_A" and r["threads"] == "32")
    pg_inv_row = next(r for r in pg_data if r["variant"] == "I_INV_LOW_SEL" and r["workload"] == "Workload_A" and r["threads"] == "32")

    pg_opt_lats = [float(pg_opt_row[k]) for k in ["p50_ms", "p95_ms", "p99_ms", "p999_ms", "max_ms"]]
    pg_inv_lats = [float(pg_inv_row[k]) for k in ["p50_ms", "p95_ms", "p99_ms", "p999_ms", "max_ms"]]

    ax1.plot(pg_opt_lats, quantiles, marker="o", markersize=6.5, linewidth=2.4, color=COLOR_OPT, label="$I_{opt}$ (Chỉ mục tối ưu)")
    ax1.plot(pg_inv_lats, quantiles, marker="s", markersize=6.5, linewidth=2.4, color=COLOR_INV, linestyle="--", label="$I_{inv}$ (Chỉ mục nghịch đảo)")

    ax1.set_title("(a) PostgreSQL (B-Tree): Phân phối tích lũy CDF\n(Workload A: 50% Read / 50% Write, 32 Threads)", pad=12, fontweight="bold")
    ax1.set_xlabel("Độ trễ thao tác đọc (mili-giây)")
    ax1.set_ylabel(r"Xác suất tích lũy $P(X \leq x)$")
    ax1.set_ylim(0.45, 1.02)
    ax1.set_xlim(0, 130)
    # Legend outside below ax1
    ax1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, frameon=True, framealpha=0.95)

    ax1.annotate(
        "Kéo dài đuôi nặng:\np99.9 vọt lên 87.55 ms\nMax = 125.12 ms!",
        xy=(pg_inv_lats[3], 0.999), xytext=(40, 0.85),
        arrowprops=dict(facecolor=COLOR_INV, shrink=0.08, width=1.5, headwidth=6),
        fontsize=8.5, fontweight="bold", color=COLOR_INV,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=COLOR_INV)
    )

    # 2. RocksDB CDF under 32 threads, Workload A (on log scale x-axis)
    rdb_opt_row = next(r for r in rdb_data if r["variant"] == "k_opt" and r["workload"] == "Workload_A" and r["threads"] == "32")
    rdb_inv_row = next(r for r in rdb_data if r["variant"] == "k_inv" and r["workload"] == "Workload_A" and r["threads"] == "32")

    rdb_opt_lats = [float(rdb_opt_row[k]) for k in ["p50_ms", "p95_ms", "p99_ms", "p999_ms", "max_ms"]]
    rdb_inv_lats = [float(rdb_inv_row[k]) for k in ["p50_ms", "p95_ms", "p99_ms", "p999_ms", "max_ms"]]

    ax2.plot(rdb_opt_lats, quantiles, marker="o", markersize=6.5, linewidth=2.4, color=COLOR_OPT, label="$K_{opt}$ (Khóa ghép tối ưu)")
    ax2.plot(rdb_inv_lats, quantiles, marker="s", markersize=6.5, linewidth=2.4, color=COLOR_INV, linestyle="--", label="$K_{inv}$ (Khóa ghép nghịch đảo)")

    ax2.set_xscale("log")
    ax2.set_title("(b) RocksDB (LSM-Tree): Phân phối tích lũy CDF\n(Workload A: 50% Read / 50% Write, 32 Threads)", pad=12, fontweight="bold")
    ax2.set_xlabel("Độ trễ thao tác đọc (mili-giây, thang đo log10)")
    ax2.set_ylabel(r"Xác suất tích lũy $P(X \leq x)$")
    ax2.set_ylim(0.45, 1.02)
    ax2.xaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f"{y:g} ms"))
    # Legend outside below ax2
    ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, frameon=True, framealpha=0.95)

    ax2.annotate(
        "K_inv: Đuôi nặng phân kỳ dữ dội\nKéo dài qua 4 bậc độ lớn đến 307.18 ms!",
        xy=(rdb_inv_lats[4], 1.0), xytext=(0.5, 0.70),
        arrowprops=dict(facecolor=COLOR_INV, shrink=0.08, width=1.5, headwidth=6),
        fontsize=8.5, fontweight="bold", color=COLOR_INV,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=COLOR_INV)
    )

    fig.suptitle(
        "Hình 3.6: Đường cong phân phối tích lũy (Cumulative Distribution Function - CDF)\nchứng minh hiện tượng kéo dài phần đuôi nặng (Heavy-Tail Latency) do sai lệch thứ tự thuộc tính",
        y=0.95, fontweight="bold"
    )

    out_path = PLOTS_DIR / "Hinh_3_6_CDF_Tail_Latency.png"
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()
    print(f"[OK] Generated: {out_path.name}")


def main():
    print("=================================================================")
    print("GENERATING CHAPTER 3 PUBLICATION BENCHMARK CHARTS (300 DPI)")
    print(f"Target Directory: {PLOTS_DIR.resolve()}")
    print("=================================================================")

    plot_fig_3_1_postgres_latency_order()
    plot_fig_3_2_postgres_cbo_correlation_blocks()
    plot_fig_3_3_rocksdb_latency_key_order()
    plot_fig_3_4_rocksdb_bloom_read_amp()
    plot_fig_3_5_timeseries_tail_latency_spikes()
    plot_fig_3_6_cdf_tail_latency()

    generated_files = list(PLOTS_DIR.glob("*.png"))
    print("\n=================================================================")
    print(f"ALL CHARTS GENERATED SUCCESSFULLY: {len(generated_files)} files")
    for f in sorted(generated_files):
        size_kb = f.stat().st_size / 1024
        print(f"  - {f.name:45s} ({size_kb:.1f} KB)")
    print("=================================================================")


if __name__ == "__main__":
    main()
