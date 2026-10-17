#!/usr/bin/env python3
"""
RocksDB Smoke Test & Telemetry Verification Script
Verifies:
1. RocksDB database creation and SSTable flush at /tmp/rocksdb_smoke_test
2. BlockBasedTableFactory with 10-bit Prefix Bloom Filter and SliceTransform
3. Iterator::Seek with prefix_same_as_start
4. Extraction of internal diagnostic counters (bloom_filter, block_read, sst_read)
"""

import os
import shutil
import struct
import sys
from pathlib import Path

try:
    from rocksdict import Rdict, Options, BlockBasedOptions, SliceTransform, ReadOptions
except ImportError as err:
    sys.exit(f"Failed to import rocksdict: {err}")


def run_smoke_test(db_path: str = "/tmp/rocksdb_smoke_test") -> dict:
    target_path = Path(db_path)
    if target_path.exists():
        shutil.rmtree(target_path, ignore_errors=True)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[1] Initializing RocksDB options at: {target_path.resolve()}")
    opts = Options()
    opts.create_if_missing(True)
    opts.enable_statistics()

    # BlockBased Table Options with Bloom Filter
    table_opts = BlockBasedOptions()
    table_opts.set_bloom_filter(10, False)  # 10 bits per key
    table_opts.set_block_size(4 * 1024)     # 4KB block size
    opts.set_block_based_table_factory(table_opts)

    # Prefix transform (4 bytes tenant_id)
    opts.set_prefix_extractor(SliceTransform.create_fixed_prefix(4))

    db = Rdict(str(target_path), opts)

    print("[2] Inserting 10 keys with 4-byte prefix and flushing to SSTable...")
    # Insert 10 keys: [tenant_id (4B)][order_id (8B)]
    for i in range(1, 11):
        tenant_id = 1001
        order_id = 50000 + i
        key = struct.pack(">IQ", tenant_id, order_id)
        value = f"order_payload_val_{i}".encode("utf-8")
        db[key] = value

    # Flush to guarantee data is persisted down to SSTable on disk
    db.flush()
    print("    Flush completed successfully.")

    print("[3] Performing prefix seek with ReadOptions(prefix_same_as_start=True)...")
    read_opts = ReadOptions()
    read_opts.set_prefix_same_as_start(True)

    it = db.iter(read_opts)
    search_prefix = struct.pack(">IQ", 1001, 50005)
    it.seek(search_prefix)

    found_count = 0
    if it.valid():
        k, v = it.key(), it.value()
        t_id, o_id = struct.unpack(">IQ", k)
        print(f"    Seek match found: tenant_id={t_id}, order_id={o_id}, value={v.decode('utf-8')}")
        found_count += 1

    # Extract internal diagnostic counters from get_statistics()
    stats_raw = opts.get_statistics()
    telemetry = {}
    key_metrics = [
        "rocksdb.bloom.filter.prefix.checked",
        "rocksdb.bloom.filter.prefix.useful",
        "rocksdb.bloom.filter.useful",
        "rocksdb.block.cache.miss",
        "rocksdb.block.cache.hit",
        "rocksdb.block.cache.add",
        "rocksdb.sst.read.micros",
        "rocksdb.num.sst.read.per.level",
    ]

    print("[4] Raw RocksDB Telemetry & Statistics:")
    for line in str(stats_raw).splitlines():
        for metric in key_metrics:
            if line.startswith(metric):
                parts = line.split()
                telemetry[metric] = line
                print(f"    {line}")

    db.close()
    print("[5] RocksDB smoke test completed successfully.")
    return telemetry


if __name__ == "__main__":
    test_dir = os.environ.get("ROCKSDB_TEST_PATH", "/tmp/rocksdb_smoke_test")
    run_smoke_test(test_dir)
