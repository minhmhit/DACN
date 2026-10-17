/**
 * High-Performance Native C++ RocksDB Benchmark Runner
 * Project: Empirical Study of Indexing & Key Ordering on Tail Latency
 *
 * Implements:
 * 1. 21-byte Unsigned Big-Endian Binary Composite Key Codec (K_opt vs K_inv)
 * 2. Prefix Bloom Filter (10 bits/key) with 4-byte SliceTransform
 * 3. Exact PerfContext & Statistics Telemetry Extraction
 * 4. Microsecond Latency Tracking & Quantile Percentile Computation
 */

#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <algorithm>
#include <cmath>
#include <random>
#include <sstream>

#include <rocksdb/db.h>
#include <rocksdb/options.h>
#include <rocksdb/table.h>
#include <rocksdb/filter_policy.h>
#include <rocksdb/slice_transform.h>
#include <rocksdb/perf_context.h>
#include <rocksdb/iostats_context.h>
#include <rocksdb/write_batch.h>
#include <rocksdb/statistics.h>


// Endian conversion utilities (Big-Endian network byte order)
#if defined(__linux__) || defined(__APPLE__)
#include <endian.h>
#define BE32(x) htobe32(x)
#define BE64(x) htobe64(x)
#else
#define BE32(x) __builtin_bswap32(x)
#define BE64(x) __builtin_bswap64(x)
#endif

#pragma pack(push, 1)
// K_opt: [tenant_id (4B)][status (1B)][created_at (8B)][order_id (8B)] = 21 Bytes
struct KeyOpt {
    uint32_t tenant_id;
    uint8_t  status;
    uint64_t created_at;
    uint64_t order_id;

    static KeyOpt make(uint32_t t_id, uint8_t st, uint64_t cr_at, uint64_t o_id) {
        KeyOpt k;
        k.tenant_id  = BE32(t_id);
        k.status     = st;
        k.created_at = BE64(cr_at);
        k.order_id   = BE64(o_id);
        return k;
    }

    uint32_t get_tenant_id() const { return BE32(tenant_id); }
    uint8_t  get_status() const { return status; }
    uint64_t get_created_at() const { return BE64(created_at); }
    uint64_t get_order_id() const { return BE64(order_id); }
};

// K_inv: [status (1B)][created_at (8B)][tenant_id (4B)][order_id (8B)] = 21 Bytes
struct KeyInv {
    uint8_t  status;
    uint64_t created_at;
    uint32_t tenant_id;
    uint64_t order_id;

    static KeyInv make(uint32_t t_id, uint8_t st, uint64_t cr_at, uint64_t o_id) {
        KeyInv k;
        k.status     = st;
        k.created_at = BE64(cr_at);
        k.tenant_id  = BE32(t_id);
        k.order_id   = BE64(o_id);
        return k;
    }

    uint32_t get_tenant_id() const { return BE32(tenant_id); }
    uint8_t  get_status() const { return status; }
    uint64_t get_created_at() const { return BE64(created_at); }
    uint64_t get_order_id() const { return BE64(order_id); }
};
#pragma pack(pop)

static_assert(sizeof(KeyOpt) == 21, "KeyOpt must be exactly 21 bytes");
static_assert(sizeof(KeyInv) == 21, "KeyInv must be exactly 21 bytes");

// Global Configuration Constants
constexpr uint32_t DEFAULT_NUM_TENANTS = 10000;
constexpr uint64_t BASE_TIMESTAMP_MS   = 1704067200000ULL; // 2024-01-01
constexpr uint64_t WINDOW_MS           = 365ULL * 24 * 3600 * 1000;

// Setup standard RocksDB Options
rocksdb::Options GetOptions() {
    rocksdb::Options options;
    options.create_if_missing = true;
    options.compaction_style  = rocksdb::kCompactionStyleLevel;

    // Buffer and compaction sizes matching experimental protocol
    options.write_buffer_size          = 16 * 1024 * 1024;      // 16MB MemTable
    options.max_bytes_for_level_base   = 64 * 1024 * 1024;      // 64MB Level 1
    options.max_bytes_for_level_multiplier = 10.0;             // Factor T = 10
    options.target_file_size_base      = 8 * 1024 * 1024;       // 8MB SSTable files

    // Prefix Bloom Filter (10 bits/key) & Prefix Extractor (4 bytes)
    rocksdb::BlockBasedTableOptions table_options;
    table_options.filter_policy.reset(rocksdb::NewBloomFilterPolicy(10, false));
    table_options.block_size           = 4 * 1024;              // 4KB blocks
    table_options.block_cache          = rocksdb::NewLRUCache(256 * 1024 * 1024); // 256MB cache
    options.table_factory.reset(rocksdb::NewBlockBasedTableFactory(table_options));

    // Fixed prefix transform on the first 4 bytes
    options.prefix_extractor.reset(rocksdb::NewFixedPrefixTransform(4));

    // DB Internal Statistics
    options.statistics = rocksdb::CreateDBStatistics();

    return options;
}

// Deterministic Pseudo-Random Generator (PCG-like / XorShift64)
struct FastRng {
    uint64_t state;
    FastRng(uint64_t seed = 42) : state(seed ? seed : 42) {}
    uint64_t next() {
        uint64_t x = state;
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        return state = x;
    }
    uint32_t next_u32(uint32_t min_v, uint32_t max_v) {
        return min_v + (next() % (max_v - min_v + 1));
    }
};

// Fast YCSB Scrambled Zipfian Generator (theta = 0.99)
class ZipfianGenerator {
    uint32_t n;
    double theta;
    double alpha;
    double zetan;
    double zeta2;
    double eta;
    FastRng rng;

public:
    ZipfianGenerator(uint32_t n_items = DEFAULT_NUM_TENANTS, double s = 0.99, uint64_t seed = 42)
        : n(n_items), theta(s), rng(seed) {
        alpha = 1.0 / (1.0 - theta);
        zetan = 0.0;
        for (uint32_t i = 1; i <= n; ++i) {
            zetan += 1.0 / std::pow(static_cast<double>(i), theta);
        }
        zeta2 = 1.0 + std::pow(0.5, theta);
        eta   = (1.0 - std::pow(2.0 / static_cast<double>(n), 1.0 - theta)) /
                (1.0 - zeta2 / zetan);
    }

    uint32_t next_value() {
        double u = static_cast<double>(rng.next() % 1000000000ULL) / 1000000000.0;
        double uz = u * zetan;
        if (uz < 1.0) return 1;
        if (uz < zeta2) return 2;
        double val = 1.0 + static_cast<double>(n) * std::pow(eta * u - eta + 1.0, alpha);
        uint32_t res = static_cast<uint32_t>(val);
        return std::max(1U, std::min(n, res));
    }
};

// Bulk Loading Function
int DoLoad(const std::string& db_path, const std::string& key_type, uint64_t num_rows, const std::string& mode) {
    std::cout << "[load] Opening RocksDB at: " << db_path << " (" << key_type << ", " << mode << ")...\n";
    rocksdb::Options options = GetOptions();
    rocksdb::DB* db = nullptr;
    rocksdb::Status s = rocksdb::DB::Open(options, db_path, &db);
    if (!s.ok()) {
        std::cerr << "[error] Failed to open DB: " << s.ToString() << "\n";
        return 1;
    }

    std::cout << "[load] Ingesting " << num_rows << " records...\n";
    auto t0 = std::chrono::steady_clock::now();

    constexpr size_t BATCH_SIZE = 10000;
    rocksdb::WriteBatch batch;
    rocksdb::WriteOptions write_options;
    write_options.disableWAL = false;

    FastRng rng(42);
    char payload_buf[104];
    std::memset(payload_buf, 'X', 104);

    for (uint64_t i = 1; i <= num_rows; ++i) {
        uint32_t tenant_id  = rng.next_u32(1, DEFAULT_NUM_TENANTS);
        uint8_t  status     = static_cast<uint8_t>(rng.next_u32(0, 4));
        uint64_t created_at = BASE_TIMESTAMP_MS + (rng.next() % WINDOW_MS);
        uint64_t order_id   = i;

        // Populate payload buffer with amount (4B) and payload (100B)
        uint32_t amount = BE32(rng.next_u32(100, 100000));
        std::memcpy(payload_buf, &amount, 4);

        if (key_type == "k_opt") {
            KeyOpt k = KeyOpt::make(tenant_id, status, created_at, order_id);
            rocksdb::Slice k_slice(reinterpret_cast<const char*>(&k), sizeof(k));
            rocksdb::Slice v_slice(payload_buf, sizeof(payload_buf));
            batch.Put(k_slice, v_slice);
        } else {
            KeyInv k = KeyInv::make(tenant_id, status, created_at, order_id);
            rocksdb::Slice k_slice(reinterpret_cast<const char*>(&k), sizeof(k));
            rocksdb::Slice v_slice(payload_buf, sizeof(payload_buf));
            batch.Put(k_slice, v_slice);
        }

        if (i % BATCH_SIZE == 0) {
            db->Write(write_options, &batch);
            batch.Clear();
        }
    }
    if (batch.Count() > 0) {
        db->Write(write_options, &batch);
    }

    auto t1 = std::chrono::steady_clock::now();
    double load_sec = std::chrono::duration<double>(t1 - t0).count();
    std::cout << "[load] Ingestion complete in " << load_sec << "s (" << (num_rows / load_sec) << " rows/s).\n";

    // Explicit Flush to form SSTables on disk
    std::cout << "[load] Flushing MemTable to SSTables...\n";
    rocksdb::FlushOptions flush_options;
    flush_options.wait = true;
    db->Flush(flush_options);

    // Print Level Statistics
    std::string l0_files, l1_files, l2_files;
    db->GetProperty("rocksdb.num-files-at-level0", &l0_files);
    db->GetProperty("rocksdb.num-files-at-level1", &l1_files);
    db->GetProperty("rocksdb.num-files-at-level2", &l2_files);
    std::cout << "[load] SSTables: L0=" << l0_files << ", L1=" << l1_files << ", L2=" << l2_files << "\n";

    delete db;
    return 0;
}

// Query Execution & Telemetry Function
int DoQuery(const std::string& db_path, const std::string& key_type, uint32_t num_queries,
            const std::string& dist, const std::string& output_json) {
    std::cout << "[query] Opening RocksDB at: " << db_path << " for " << num_queries << " queries...\n";
    rocksdb::Options options = GetOptions();
    rocksdb::DB* db = nullptr;
    rocksdb::Status s = rocksdb::DB::Open(options, db_path, &db);
    if (!s.ok()) {
        std::cerr << "[error] Failed to open DB: " << s.ToString() << "\n";
        return 1;
    }

    // Enable high-precision internal PerfContext profiling
    rocksdb::SetPerfLevel(rocksdb::PerfLevel::kEnableTimeExceptForMutex);

    ZipfianGenerator zipf_gen(DEFAULT_NUM_TENANTS, 0.99, 12345);
    FastRng rng(6789);

    std::vector<double> latencies_us;
    latencies_us.reserve(num_queries);

    uint64_t total_key_comparisons = 0;
    uint64_t total_cache_hits       = 0;
    uint64_t total_block_reads      = 0;
    uint64_t total_block_read_bytes = 0;
    uint64_t total_bloom_sst_hits   = 0;
    uint64_t total_bloom_sst_misses = 0;
    uint64_t total_records_found    = 0;

    auto benchmark_start = std::chrono::steady_clock::now();

    for (uint32_t q = 0; q < num_queries; ++q) {
        uint32_t target_tenant = (dist == "zipfian") ? zipf_gen.next_value() : rng.next_u32(1, DEFAULT_NUM_TENANTS);
        uint8_t  target_status = static_cast<uint8_t>(rng.next_u32(0, 4));

        // 30-day window
        uint64_t window_span = 30ULL * 24 * 3600 * 1000;
        uint64_t max_offset  = WINDOW_MS - window_span;
        uint64_t start_time  = BASE_TIMESTAMP_MS + (rng.next() % max_offset);
        uint64_t end_time    = start_time + window_span;

        // Reset telemetry context before query
        rocksdb::get_perf_context()->Reset();
        rocksdb::get_iostats_context()->Reset();

        auto q_start = std::chrono::steady_clock::now();
        uint32_t matched_count = 0;

        if (key_type == "k_opt") {
            // K_opt: Prefix is first 4 bytes (tenant_id)
            KeyOpt start_k = KeyOpt::make(target_tenant, target_status, start_time, 0);
            KeyOpt end_k   = KeyOpt::make(target_tenant, target_status, end_time, 0xFFFFFFFFFFFFFFFFULL);

            rocksdb::Slice start_slice(reinterpret_cast<const char*>(&start_k), sizeof(start_k));
            rocksdb::Slice end_slice(reinterpret_cast<const char*>(&end_k), sizeof(end_k));

            rocksdb::ReadOptions read_options;
            read_options.prefix_same_as_start = true;
            read_options.iterate_upper_bound  = &end_slice;

            rocksdb::Iterator* it = db->NewIterator(read_options);
            for (it->Seek(start_slice); it->Valid(); it->Next()) {
                const KeyOpt* curr = reinterpret_cast<const KeyOpt*>(it->key().data());
                if (curr->get_tenant_id() != target_tenant || curr->get_status() != target_status) {
                    break;
                }
                matched_count++;
            }
            delete it;

        } else {
            // K_inv: Status is first byte, followed by created_at. tenant_id is at byte 9..12
            // Iterator must scan range [status, start_time] to [status, end_time] and compare tenant_id in userspace!
            KeyInv start_k = KeyInv::make(0, target_status, start_time, 0);
            KeyInv end_k   = KeyInv::make(0xFFFFFFFFU, target_status, end_time, 0xFFFFFFFFFFFFFFFFULL);

            rocksdb::Slice start_slice(reinterpret_cast<const char*>(&start_k), sizeof(start_k));
            rocksdb::Slice end_slice(reinterpret_cast<const char*>(&end_k), sizeof(end_k));

            rocksdb::ReadOptions read_options;
            read_options.iterate_upper_bound = &end_slice;

            rocksdb::Iterator* it = db->NewIterator(read_options);
            for (it->Seek(start_slice); it->Valid(); it->Next()) {
                const KeyInv* curr = reinterpret_cast<const KeyInv*>(it->key().data());
                if (curr->get_status() != target_status || curr->get_created_at() > end_time) {
                    break;
                }
                // Check tenant_id in userspace
                if (curr->get_tenant_id() == target_tenant) {
                    matched_count++;
                }
            }
            delete it;
        }

        auto q_end = std::chrono::steady_clock::now();
        double lat_us = std::chrono::duration<double, std::micro>(q_end - q_start).count();
        latencies_us.push_back(lat_us);

        // Accumulate PerfContext telemetry
        auto* perf = rocksdb::get_perf_context();
        total_key_comparisons += perf->user_key_comparison_count;
        total_cache_hits       += perf->block_cache_hit_count;
        total_block_reads      += perf->block_read_count;
        total_block_read_bytes += perf->block_read_byte;
        total_bloom_sst_hits   += perf->bloom_sst_hit_count;
        total_bloom_sst_misses += perf->bloom_sst_miss_count;
        total_records_found    += matched_count;
    }

    auto benchmark_end = std::chrono::steady_clock::now();
    double total_sec = std::chrono::duration<double>(benchmark_end - benchmark_start).count();

    // Compute Latency Percentiles
    std::sort(latencies_us.begin(), latencies_us.end());
    auto get_p = [&](double p) -> double {
        size_t idx = static_cast<size_t>((p / 100.0) * latencies_us.size());
        idx = std::min(idx, latencies_us.size() - 1);
        return latencies_us[idx];
    };

    double p50_us = get_p(50.0);
    double p95_us = get_p(95.0);
    double p99_us = get_p(99.0);
    double max_us = latencies_us.back();
    double sum_us = 0.0;
    for (double v : latencies_us) sum_us += v;
    double mean_us = sum_us / latencies_us.size();

    std::cout << "\n=======================================================\n";
    std::cout << "RocksDB Query Benchmark Summary (" << key_type << ")\n";
    std::cout << "=======================================================\n";
    std::cout << "  Queries executed       : " << num_queries << "\n";
    std::cout << "  Throughput             : " << std::fixed << std::setprecision(1) << (num_queries / total_sec) << " ops/sec\n";
    std::cout << "  Latency Mean           : " << std::setprecision(3) << (mean_us / 1000.0) << " ms\n";
    std::cout << "  Latency p50            : " << (p50_us / 1000.0) << " ms (" << p50_us << " us)\n";
    std::cout << "  Latency p95            : " << (p95_us / 1000.0) << " ms (" << p95_us << " us)\n";
    std::cout << "  Latency p99            : " << (p99_us / 1000.0) << " ms (" << p99_us << " us)\n";
    std::cout << "  Latency Max            : " << (max_us / 1000.0) << " ms\n";
    std::cout << "  Avg Key Comparisons/op : " << (total_key_comparisons / num_queries) << "\n";
    std::cout << "  Avg Block Reads/op     : " << static_cast<double>(total_block_reads) / num_queries << "\n";
    std::cout << "  Avg Cache Hits/op      : " << static_cast<double>(total_cache_hits) / num_queries << "\n";
    std::cout << "  Total Bloom SST Hits   : " << total_bloom_sst_hits << "\n";
    std::cout << "  Total Bloom SST Misses : " << total_bloom_sst_misses << "\n";

    // Write Output JSON
    std::ofstream out(output_json);
    out << "{\n"
        << "  \"key_type\": \"" << key_type << "\",\n"
        << "  \"num_queries\": " << num_queries << ",\n"
        << "  \"distribution\": \"" << dist << "\",\n"
        << "  \"throughput_ops\": " << (num_queries / total_sec) << ",\n"
        << "  \"latency_p50_ms\": " << (p50_us / 1000.0) << ",\n"
        << "  \"latency_p95_ms\": " << (p95_us / 1000.0) << ",\n"
        << "  \"latency_p99_ms\": " << (p99_us / 1000.0) << ",\n"
        << "  \"latency_max_ms\": " << (max_us / 1000.0) << ",\n"
        << "  \"latency_mean_ms\": " << (mean_us / 1000.0) << ",\n"
        << "  \"total_key_comparisons\": " << total_key_comparisons << ",\n"
        << "  \"avg_key_comparisons\": " << (total_key_comparisons / num_queries) << ",\n"
        << "  \"total_block_reads\": " << total_block_reads << ",\n"
        << "  \"avg_block_reads\": " << (static_cast<double>(total_block_reads) / num_queries) << ",\n"
        << "  \"total_cache_hits\": " << total_cache_hits << ",\n"
        << "  \"total_bloom_sst_hits\": " << total_bloom_sst_hits << ",\n"
        << "  \"total_bloom_sst_misses\": " << total_bloom_sst_misses << "\n"
        << "}\n";
    out.close();

    delete db;
    return 0;
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: rdb_benchmark <load|query> [args...]\n";
        return 1;
    }
    std::string cmd = argv[1];
    if (cmd == "load") {
        if (argc < 6) {
            std::cerr << "Usage: rdb_benchmark load <db_path> <k_opt|k_inv> <num_rows> <mode>\n";
            return 1;
        }
        return DoLoad(argv[2], argv[3], std::stoull(argv[4]), argv[5]);
    } else if (cmd == "query") {
        if (argc < 7) {
            std::cerr << "Usage: rdb_benchmark query <db_path> <k_opt|k_inv> <num_queries> <uniform|zipfian> <output_json>\n";
            return 1;
        }
        return DoQuery(argv[2], argv[3], std::stoul(argv[4]), argv[5], argv[6]);
    }
    std::cerr << "Unknown command: " << cmd << "\n";
    return 1;
}
