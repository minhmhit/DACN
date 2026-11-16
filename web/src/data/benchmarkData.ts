import rawData from './raw_data.json';
import {
  BenchmarkRow,
  CboPlanComparison,
  PerfContextTelemetry,
  RulebookItem,
  ComparisonDimension,
  ChecklistItem,
} from '../types/benchmark';

export const postgresBenchmarkData: BenchmarkRow[] = rawData.postgres as BenchmarkRow[];
export const rocksdbBenchmarkData: BenchmarkRow[] = rawData.rocksdb as BenchmarkRow[];

export const cboPlanComparisons: CboPlanComparison[] = [
  {
    parameter: 'Kế hoạch CBO được chọn (Selected Plan)',
    opt: 'Index Scan',
    inv: 'Bitmap Heap Scan',
    none: 'Gather -> Parallel Seq Scan',
    ratio: 'Chuyển dịch cấu trúc kế hoạch',
  },
  {
    parameter: 'Cấu trúc nút con (Sub-nodes)',
    opt: 'Index Scan using idx_orders_opt',
    inv: 'Bitmap Index Scan using idx_orders_inv_low',
    none: '2 Workers Parallel Seq Scan',
    ratio: 'Thay đổi thuật toán duyệt bảng',
  },
  {
    parameter: 'Điều kiện lọc chỉ mục (Index Cond)',
    opt: '(tenant_id = 42) AND (status = 1) AND (created_at BETWEEN ...)',
    inv: '(status = 1) AND (created_at BETWEEN ...)',
    none: 'Không có (Quét toàn bảng)',
    ratio: 'Mất điều kiện lọc tenant trên cây B-Tree',
  },
  {
    parameter: 'Điều kiện lọc lại trên Heap (Filter)',
    opt: 'Không có (Khớp 100% tại cây B-Tree)',
    inv: '(tenant_id = 42)',
    none: '(tenant_id = 42) AND (status = 1) AND (...)',
    ratio: 'Phát sinh bước lọc lại trên RAM',
  },
  {
    parameter: 'Chi phí khởi động (Startup Cost)',
    opt: '0.42',
    inv: '12.45',
    none: '1,000.00',
    ratio: 'Tăng 29.6×',
  },
  {
    parameter: 'Tổng chi phí ước lượng (Total Cost)',
    opt: '4.10',
    inv: '351.72',
    none: '15,430.87',
    ratio: 'Tăng 85.8× (so với I_opt)',
  },
  {
    parameter: 'Số khối đệm đọc (Shared Read Blocks)',
    opt: '3 blocks (2 Index + 1 Heap)',
    inv: '83 blocks (1 Index + 82 Heap)',
    none: '15,920 blocks (Toàn bộ heap)',
    ratio: 'Tăng 27.7× khối I/O',
  },
  {
    parameter: 'Số khối đệm trúng cache (Shared Hit)',
    opt: '2 blocks',
    inv: '14 blocks',
    none: '2,304 blocks',
    ratio: 'Tăng 7.0×',
  },
  {
    parameter: 'Thời gian đọc I/O đĩa (Read I/O Time)',
    opt: '0.012 ms',
    inv: '0.845 ms',
    none: '45.995 ms',
    ratio: 'Tăng 70.4× thời gian I/O',
  },
  {
    parameter: 'Thời gian thực thi trung bình',
    opt: '0.038 ms',
    inv: '1.215 ms',
    none: '46.372 ms',
    ratio: 'Chậm hơn 32.0×',
  },
  {
    parameter: 'Hành vi khi cạn bộ nhớ (work_mem = 64kB)',
    opt: '0 Lossy Pages (Không ảnh hưởng)',
    inv: '7,247 trang suy thoái thành Lossy',
    none: 'Quét tuần tự đĩa',
    ratio: 'Ép CPU quét kiểm tra lại 340,023 dòng',
  },
];

export const perfContextTelemetries: PerfContextTelemetry[] = [
  {
    metric: 'SSTable bị cắt tỉa bởi Bloom Filter (bloom_sst_miss_count)',
    k_opt: '182 lần',
    k_inv: '0 lần',
    ratio: '0×',
    impact: 'Vô hiệu hóa hoàn toàn 100% Prefix Bloom Filter',
  },
  {
    metric: 'SSTable phải đọc do trúng Bloom Filter (bloom_sst_hit_count)',
    k_opt: '4,818 lần',
    k_inv: '1,384 lần',
    ratio: '0.29×',
    impact: 'Bỏ qua cơ chế lọc nhanh trên RAM',
  },
  {
    metric: 'Số phép so sánh khóa trên CPU (user_key_comparisons)',
    k_opt: '58.0 / op',
    k_inv: '19,833.0 / op',
    ratio: '342.0×',
    impact: 'Bùng nổ áp lực tính toán trên CPU',
  },
  {
    metric: 'Số khối dữ liệu đọc từ đĩa (block_read_count)',
    k_opt: '1.835 / op',
    k_inv: '28.308 / op',
    ratio: '15.4×',
    impact: 'Khuếch đại đọc (Read Amplification) nghiêm trọng',
  },
  {
    metric: 'Số khối tra cứu trúng cache (block_cache_hit_count)',
    k_opt: '3.0 / op',
    k_inv: '238.1 / op',
    ratio: '79.3×',
    impact: 'Xáo trộn bộ nhớ đệm (Block Cache Thrashing)',
  },
  {
    metric: 'Thông lượng quét phạm vi thực tế (Range Scan Throughput)',
    k_opt: '15,963.2 ops/s',
    k_inv: '176.4 ops/s',
    ratio: '0.011×',
    impact: 'Thông lượng thực thi bị sụp đổ 90.5 lần',
  },
  {
    metric: 'Độ trễ trung vị (p50)',
    k_opt: '0.0428 ms (42.8 µs)',
    k_inv: '4.4304 ms',
    ratio: '103.5×',
    impact: 'Chậm hơn 103.5 lần',
  },
  {
    metric: 'Độ trễ phân vị đuôi (p99)',
    k_opt: '0.2355 ms (235.5 µs)',
    k_inv: '17.9997 ms',
    ratio: '76.4×',
    impact: 'Độ trễ đuôi sụp đổ nghiêm trọng',
  },
  {
    metric: 'Độ trễ cực đại (Max)',
    k_opt: '0.3471 ms',
    k_inv: '25.4880 ms',
    ratio: '73.4×',
    impact: 'Phát sinh các đỉnh trễ cục bộ',
  },
];

export const comparisonDimensions: ComparisonDimension[] = [
  {
    dimension: 'Mục tiêu tối ưu hóa (Optimization Goal)',
    traditional: 'Cắt giảm chi phí CBO trung bình ước lượng (Estimated Cost)',
    aiDrl: 'Cực đại hóa thông lượng trung bình (p50) hoặc tổng thời gian chạy',
    ourRulebook: 'Kiểm soát Phương sai dịch vụ σ² & Triệt tiêu độ trễ đuôi (p99, p99.9)',
  },
  {
    dimension: 'Cơ chế bảo vệ bộ nhớ work_mem',
    traditional: 'Hoàn toàn bỏ qua; giả định dung lượng RAM không giới hạn',
    aiDrl: 'Không có cơ chế phạt (Penalty) đối với kế hoạch vượt ngưỡng RAM',
    ourRulebook: 'Thiết lập công thức toán học bắt buộc định cỡ RAM chống Lossy Bitmap',
  },
  {
    dimension: 'Mã hóa khóa nhị phân (Endianness)',
    traditional: 'Không áp dụng (chỉ thiết kế chỉ mục cấp độ bảng quan hệ RDBMS)',
    aiDrl: 'Không định nghĩa (chỉ xử lý ở mức biểu thức trừu tượng SQL AST)',
    ourRulebook: 'Ép chuẩn đóng gói Unsigned Big-Endian bắt buộc ở cấp độ Byte vật lý',
  },
  {
    dimension: 'Tích hợp bộ lọc Prefix Bloom Filter',
    traditional: 'Hoàn toàn mù tịt (Blind spot); không xét đến kiến trúc LSM-Tree',
    aiDrl: 'Không mô hình hóa được xác suất dương tính giả và độ dài tiếp đầu ngữ',
    ourRulebook: 'Khớp chính xác kích thước byte với bộ trích xuất Prefix Extractor (4 Bytes)',
  },
  {
    dimension: 'Mô hình toán học bảo vệ cam kết SLA',
    traditional: 'Mô hình chi phí tĩnh Heuristic',
    aiDrl: 'Hộp đen mạng nơ-ron sâu (Deep Neural Network)',
    ourRulebook: 'Kiểm chứng thực nghiệm bằng Định lý hàng đợi Pollaczek-Khinchine (r ≥ 0.95)',
  },
];

export const rulebookItems: RulebookItem[] = [
  {
    id: 1,
    title: 'Quy tắc ESR và Tiêu chí Thuộc tính chọn lọc cao dẫn đầu',
    target: 'PostgreSQL, MySQL, Oracle (B-Tree RDBMS)',
    statement:
      'Khi thiết kế chỉ mục B-Tree đa cột cho các truy vấn lọc đa điều kiện, các cột đẳng thức (=) phải đứng trước các cột phạm vi (<, >, BETWEEN). Cột có độ chọn lọc cao nhất (n_distinct ≫ 1, cụ thể tenant_id) bắt buộc đặt ở vị trí dẫn đầu tuyệt đối (Leftmost Prefix).',
    empiricalProof:
      'Cấu hình I_opt giúp CBO khóa chặt kế hoạch Index Scan thuần túy, đọc đúng 3 khối bộ đệm (24KB), giữ p99 ≤ 15.67ms tại 32 luồng. Vi phạm quy tắc này (I_inv) ép CBO chuyển sang Bitmap Index Scan, làm chi phí CBO tăng 85.8×, I/O tăng 27.7× và p99 bùng nổ lên 55.49ms (tăng 3.54×).',
    riskIfViolated:
      'CBO từ bỏ Index Scan, chuyển sang Bitmap Index Scan. Khi tải cao hoặc cạn work_mem, hệ thống suy thoái thành Lossy Bitmap Heap Scan, ép CPU quét lại hàng trăm ngàn dòng.',
    checklist: [
      'Xác định cột có n_distinct cao nhất qua pg_stats hoặc INFORMATION_SCHEMA.',
      'Cấu trúc chỉ mục tuân thủ tuyệt đối: (Equality_High_Selectivity, Equality_Low_Selectivity, Range_Column).',
      'Tuyệt đối không đặt cột phạm vi vào giữa các cột đẳng thức.',
    ],
    codeSnippet: {
      language: 'sql',
      title: 'PostgreSQL DDL Chuẩn ESR',
      code: `-- Đúng chuẩn: tenant_id (chọn lọc cao) -> status (chọn lọc thấp) -> created_at (phạm vi)\nCREATE INDEX idx_orders_opt ON orders (tenant_id, status, created_at);\n\n-- Sai: Đưa cột phân biệt thấp lên đầu\n-- CREATE INDEX idx_orders_inv ON orders (status, created_at, tenant_id);`,
    },
  },
  {
    id: 2,
    title: 'Căn chỉnh Tiếp đầu ngữ cho Bộ lọc Prefix Bloom Filter',
    target: 'RocksDB, Cassandra, ScyllaDB, LevelDB (LSM-Tree Key-Value)',
    statement:
      'Trong các hệ thống lưu trữ LSM-Tree khi kích hoạt cơ chế bộ lọc tiếp đầu ngữ (PrefixTransform), thuộc tính lọc phân vùng hoặc định danh chính bắt buộc phải nằm chính xác trong N bytes đầu tiên của khóa nhị phân.',
    empiricalProof:
      'Khóa tối ưu K_opt khớp chính xác 4 byte đầu tiên với NewFixedPrefixTransform(4), cắt tỉa thành công 182 SSTables (bloom_sst_miss_count = 182) trên RAM. Đặt sai thứ tự (K_inv) khiến số lần cắt tỉa rơi về 0 tuyệt đối, làm sụp đổ thông lượng 355 lần (255,264 ops/s xuống 589 ops/s) và p99 vọt lên 220.57ms (>2,400×).',
    riskIfViolated:
      'Vô hiệu hóa 100% Prefix Bloom Filter. MergingIterator buộc phải quét nhị phân mọi SSTable từ L0 đến L6, gây bùng nổ so sánh khóa CPU 342× và khuếch đại đọc 15.4×.',
    checklist: [
      'Độ dài tiếp đầu ngữ FixedPrefixTransform(N) phải bằng đúng kích thước byte của thuộc tính lọc định danh.',
      'Đặt cờ read_options.prefix_same_as_start = true khi khởi tạo Iterator.',
      'Giám sát chỉ số rocksdb.bloom.filter.prefix.useful qua Prometheus / Grafana.',
    ],
    codeSnippet: {
      language: 'cpp',
      title: 'RocksDB C++ Configuration',
      code: `rocksdb::BlockBasedTableOptions table_options;\ntable_options.filter_policy.reset(rocksdb::NewBloomFilterPolicy(10, false));\n\nrocksdb::Options options;\noptions.table_factory.reset(rocksdb::NewBlockBasedTableFactory(table_options));\noptions.prefix_extractor.reset(rocksdb::NewFixedPrefixTransform(4)); // 4B tenant_id\n\nrocksdb::ReadOptions read_options;\nread_options.prefix_same_as_start = true;`,
    },
  },
  {
    id: 3,
    title: 'Chuẩn hóa Mã hóa Nhị phân Unsigned Big-Endian cho Khóa ghép',
    target: 'Tất cả các hệ thống lưu trữ nhị phân Key-Value (RocksDB, TiKV, BadgerDB)',
    statement:
      'Toàn bộ các trường số nguyên tham gia cấu thành khóa ghép trong cơ sở dữ liệu Key-Value phải được mã hóa theo chuẩn Unsigned Big-Endian (Network Byte Order). Tuyệt đối không dùng Little-Endian hoặc chuỗi JSON/String.',
    empiricalProof:
      'RocksDB so sánh khóa bằng hàm memcmp(). Big-Endian đặt byte có trọng số cao nhất (MSB) tại địa chỉ thấp nhất, bảo đảm tính đơn điệu từ điển hoàn hảo: Giá trị A < B ⇔ memcmp(pack(A), pack(B)) < 0. Little-Endian làm số 256 (0x00 0x01) nhỏ hơn số 1 (0x01 0x00), phá hủy toàn bộ thứ tự quét phạm vi.',
    riskIfViolated:
      'Đảo lộn thứ tự sắp xếp vật lý, biến thao tác quét phạm vi (Range Scan) thành quét ngẫu nhiên toàn bộ cơ sở dữ liệu.',
    checklist: [
      'Python: Sử dụng struct.pack(\'>IBQQ\', ...) với ký tự \'>\' bắt buộc.',
      'C++: Sử dụng hàm chuẩn htobe32() và htobe64() trước khi memcpy vào Slice.',
      'Kiểm thử đơn vị xác nhận memcmp() khớp 100% với quan hệ so sánh số học.',
    ],
    codeSnippet: {
      language: 'python',
      title: 'Binary Key Packaging Codec',
      code: `# Python 3.12+\nimport struct\n\n# ĐÚNG CHUẨN: Unsigned Big-Endian ('>')\n# [tenant_id: 4B][status: 1B][created_at: 8B][order_id: 8B] = 21 Bytes\nk_opt = struct.pack('>IBQQ', tenant_id, status, created_at, order_id)\n\n# C++ Native:\n// uint32_t t_be = htobe32(tenant_id);\n// uint64_t c_be = htobe64(created_at);`,
    },
  },
  {
    id: 4,
    title: 'Ngăn chặn suy thoái tràn bộ nhớ Bitmap (Prevent Lossy Bitmap Degradation)',
    target: 'PostgreSQL (Hệ thống OLTP đa luồng)',
    statement:
      'Trong PostgreSQL, khi truy vấn sử dụng Bitmap Index Scan, bộ nhớ work_mem của mỗi phiên phải được cấp phát tối thiểu bằng dung lượng cần thiết để lưu trữ con trỏ tuple chính xác (TID), ngăn chặn TIDBitmap suy cấp thành Lossy Page Flag.',
    empiricalProof:
      'Khi work_mem = 64kB, toàn bộ 7,247 trang heap bị suy thoái thành Lossy. CPU bị ép phải nạp lại từng khối đệm và duyệt kiểm tra lại thủ công cho 340,023 dòng dữ liệu, đẩy phương sai dịch vụ σ² từ 6.22 lên 107.85 ms² và làm sụp đổ p99.',
    riskIfViolated:
      'Cạn kiệt work_mem làm bùng nổ phương sai thời gian phục vụ σ², kéo theo thời gian chờ hàng đợi W_q tăng đột biến theo định lý Pollaczek-Khinchine.',
    checklist: [
      'Định cỡ work_mem tối thiểu theo công thức: work_mem ≥ ceil(B_table / 8192) KB.',
      'Với bảng orders gồm 10,264 trang, work_mem an toàn khuyến nghị là ≥ 4MB.',
      'Theo dõi chỉ số pg_stat_activity và EXPLAIN ANALYZE để phát hiện "Lossy Heap Blocks".',
    ],
    codeSnippet: {
      language: 'sql',
      title: 'PostgreSQL work_mem Configuration',
      code: `-- postgresql.conf\nshared_buffers = 1GB\nwork_mem = 4MB                 -- Ngăn chặn suy thoái Lossy Bitmap\nmaintenance_work_mem = 256MB\nrandom_page_cost = 1.2         -- Tối ưu cho ổ NVMe SSD`,
    },
  },
  {
    id: 5,
    title: 'Kiểm soát Phân tách trang B-Tree và Nén tầng LSM-Tree dưới tải ghi',
    target: 'PostgreSQL & RocksDB (Hệ thống hỗn hợp 50% Read / 50% Write)',
    statement:
      'Dưới áp lực tải ghi hỗn hợp, các thao tác cập nhật vật lý trên nền sẽ gây tranh chấp chốt khóa nội tại, tạo ra các xung đột độ trễ. Cần áp dụng fillfactor = 85 cho B-Tree và điều tiết luồng xả nén nền trong LSM-Tree.',
    empiricalProof:
      'Tại Workload A (32 luồng), chuỗi đo 1 giây ghi nhận đỉnh nhọn p99 vọt lên 63.93ms trên PostgreSQL do phân tách trang lá B-Tree và khóa chốt WAL. Trên RocksDB, đỉnh nhọn 215.41ms xuất hiện khi MemTable xả xuống L0 kết hợp nén tầng L0 -> L1.',
    riskIfViolated:
      'Phát sinh các đợt tăng vọt độ trễ (Latency Spikes) tức thời, gây trễ hàng đợi dây chuyền.',
    checklist: [
      'Thiết lập fillfactor = 85 cho bảng và chỉ mục B-Tree chịu tải ghi nặng.',
      'Cấu hình RocksDB write_buffer_size = 128MB, max_background_compactions = 4.',
      'Tránh để số tệp tầng L0 vượt quá level0_slowdown_writes_trigger.',
    ],
    codeSnippet: {
      language: 'sql',
      title: 'Fillfactor Tuning SQL',
      code: `ALTER TABLE orders SET (fillfactor = 85);\nALTER INDEX idx_orders_opt SET (fillfactor = 85);\n\n-- Thu hồi và sắp xếp lại không gian đĩa vật lý\nVACUUM FULL orders;\nREINDEX TABLE orders;`,
    },
  },
  {
    id: 6,
    title: 'Thiết lập SLA dựa trên Phân vị đuôi (p99/p99.9) và Phương sai thời gian phục vụ σ²',
    target: 'Toàn bộ hạ tầng cơ sở dữ liệu phân tán',
    statement:
      'Tuyệt đối không sử dụng độ trễ trung bình (p50 hoặc mean) làm chỉ số cam kết SLA. Theo Định lý Pollaczek-Khinchine, chất lượng dịch vụ và độ dài hàng đợi bị chi phối áp đảo bởi Phương sai thời gian phục vụ σ².',
    empiricalProof:
      'Hệ số tương quan tuyến tính Pearson r(σ², p99) đạt 0.9562 trên PostgreSQL và 0.9762 trên RocksDB. Dưới K_inv, σ² nổ tung lên 2,480.05 ms², trực tiếp đẩy p99 lên 220.57ms dù p50 ở luồng đơn chỉ là 3.23ms.',
    riskIfViolated:
      'Chỉ số trung bình che giấu hoàn toàn các đợt sập hiệu năng, khiến hệ thống rơi vào trạng thái quá tải dây chuyền mà không kịp cảnh báo.',
    checklist: [
      'Đặt ngưỡng SLA cam kết tại phân vị: SLA Threshold ≥ p99.9.',
      'Cảnh báo sớm nguy cơ sập hiệu năng khi Phương sai dịch vụ σ² > 10 ms².',
      'Tích hợp thư viện HdrHistogram với độ phân giải nano-giây vào telemetry.',
    ],
    codeSnippet: {
      language: 'python',
      title: 'HdrHistogram Monotonic Measurement',
      code: `import time\nfrom hdrh.histogram import HdrHistogram\n\nhist = HdrHistogram(1, 60_000_000, 3) # 1µs to 60s\n\nt0 = time.perf_counter_ns()\nexecute_query()\nt1 = time.perf_counter_ns()\n\nlatency_us = (t1 - t0) // 1_000\nhist.record_value(latency_us)\n\np99 = hist.get_value_at_percentile(99.0) / 1000.0\nvariance = hist.get_std_deviation() ** 2 / 1_000_000.0`,
    },
  },
  {
    id: 7,
    title: 'Thiết kế Chỉ mục Bao phủ (Covering Index) và Visibility Map cho Bảng Danh mục',
    target: 'Bảng Master Data (10,000 bản ghi, 100% Point Lookup)',
    statement:
      'Đối với các bảng danh mục đọc thường xuyên, đưa các cột kết quả vào mệnh đề INCLUDE và duy trì all-visible flag trong Visibility Map qua VACUUM ANALYZE để kích hoạt Index Only Scan với Heap Fetches = 0.',
    empiricalProof:
      'Thực nghiệm trên bảng tenants: Cấu hình Covering Index I_MD_COV (region_id, tenant_code) INCLUDE (credit_limit) đạt Heap Fetches = 0 tuyệt đối, giảm phương sai độ trễ 20% và triệt tiêu đỉnh nhọn độ trễ từ 17.10ms xuống 5.13ms (giảm 3.3×). RocksDB đạt 139,121 ops/s và p99 = 12µs nhờ Whole-Key Bloom Filter.',
    riskIfViolated:
      'Phát sinh Heap Fetches đọc thêm trang dữ liệu, gây biến động độ trễ và cạnh tranh bộ đệm cache.',
    checklist: [
      'Đưa các cột chỉ xuất hiện ở mệnh đề SELECT vào INCLUDE (...) thay vì khóa chính chỉ mục.',
      'Thiết lập tác vụ chạy VACUUM định kỳ để duy trì all-visible flag.',
    ],
    codeSnippet: {
      language: 'sql',
      title: 'Covering Index DDL',
      code: `-- Tạo Covering Index kích hoạt Index Only Scan (Heap Fetches = 0)\nCREATE INDEX idx_tenants_covering \nON tenants (region_id, tenant_code) \nINCLUDE (credit_limit, tenant_info);\n\n-- Cập nhật Visibility Map\nVACUUM ANALYZE tenants;`,
    },
  },
  {
    id: 8,
    title: 'Chiến lược Khóa Thời gian Dẫn đầu (Time-Leading) cho Bảng Sự kiện Nạp Thuần túy',
    target: 'Bảng Event Log Ingestion (100,000 sự kiện nạp tuần tự)',
    statement:
      'Đối với bảng nhật ký sự kiện ghi nối đuôi (Append-Only), thuộc tính mốc thời gian tăng đơn điệu (event_ts) bắt buộc phải dẫn đầu chỉ mục B-Tree để chèn vào lá cực phải, ngăn ngừa phân tách trang ngẫu nhiên và bùng nổ FPI trong WAL. Với lưu lượng cực lớn, ưu tiên kiến trúc LSM-Tree.',
    empiricalProof:
      'Cấu hình TENANT_LEAD trên PostgreSQL bùng nổ 350 trang Full-Page Images (FPI) trong WAL (tăng 175×) do 10,000 tenant chèn ngẫu nhiên làm tách trang liên tục. Cấu hình TIME_LEAD chỉ sinh 0 - 2 trang FPI. RocksDB đạt thông lượng nạp 61,069 inserts/s (vượt trội 10.5× so với PostgreSQL), p99 ≤ 0.042ms và dung lượng đĩa chỉ 3MB (so với 26MB của PostgreSQL).',
    riskIfViolated:
      'Bùng nổ ghi nhật ký toàn trang (FPI), nghẽn I/O ghi trên tiến trình WAL Writer và làm phân mảnh cấu trúc B-Tree.',
    checklist: [
      'Đặt chỉ mục dạng (event_ts, tenant_id) hoặc sử dụng Declarative Partitioning theo khoảng thời gian.',
      'Với luồng sự kiện viễn thông/IoT trên 10,000 events/giây, sử dụng LSM-Tree Store (RocksDB) làm buffer.',
    ],
    codeSnippet: {
      language: 'sql',
      title: 'Time-Leading Append-Only Index',
      code: `-- Khóa thời gian tăng liên tục cho phép chèn nối đuôi vào lá cực phải\nCREATE INDEX idx_events_time_leading \nON order_events (event_ts, tenant_id);\n\n-- Tránh chỉ mục ngẫu nhiên gây phân tách lá:\n-- CREATE INDEX idx_events_bad ON order_events (tenant_id, event_ts);`,
    },
  },
];

export const productionChecklist: ChecklistItem[] = [
  {
    category: 'B-Tree Leading Column',
    standard: 'Cột có n_distinct lớn nhất (tenant_id) đứng đầu chỉ mục',
    risk: 'CBO chuyển sang Bitmap Scan, I/O tăng 27.7×, chi phí CBO tăng 85.8×',
    action: 'Tái tạo chỉ mục tuân thủ quy tắc ESR: (tenant_id, status, created_at)',
  },
  {
    category: 'Prefix Bloom Filter',
    standard: '4 Bytes đầu tiên của khóa nhị phân khớp chính xác FixedPrefixTransform',
    risk: 'Vô hiệu hóa 100% Bloom Filter, CPU so sánh khóa tăng 342×, tput sụt 355×',
    action: 'Sắp xếp lại struct nhị phân với tenant_id đặt tại offset [0..3]',
  },
  {
    category: 'Binary Key Encoding',
    standard: 'Chuẩn Unsigned Big-Endian (>IBQQ, htobe32/htobe64)',
    risk: 'Sai lệch thứ tự từ điển với memcmp(), Range Scan biến thành Full Scan',
    action: 'Ép kiểu nhị phân Unsigned Big-Endian cho toàn bộ trường số nguyên',
  },
  {
    category: 'PostgreSQL work_mem',
    standard: 'work_mem ≥ ceil(B_table / 8192) KB (tối thiểu 4MB)',
    risk: '7,247 trang suy thoái thành Lossy, CPU quét kiểm tra lại 340,023 dòng',
    action: 'Tăng tham số work_mem trong postgresql.conf lên ≥ 4MB',
  },
  {
    category: 'B-Tree Fillfactor',
    standard: 'fillfactor = 80..85% cho các bảng chịu tải ghi hỗn hợp',
    risk: 'Gây phân tách trang lá B-Tree ngẫu nhiên và nghẽn chốt độc quyền WAL',
    action: 'Thiết lập ALTER TABLE ... SET (fillfactor = 85) và REINDEX',
  },
  {
    category: 'Hệ thống giám sát SLA',
    standard: 'Thu thập vi đo lường p99, p99.9 và Phương sai dịch vụ σ²',
    risk: 'Độ trễ trung bình che giấu các đợt sập hiệu năng do xung đột vi kiến trúc',
    action: 'Tích hợp HdrHistogram phân giải micro-giây, cảnh báo khi σ² > 10 ms²',
  },
  {
    category: 'Covering Index (Master)',
    standard: 'Mệnh đề INCLUDE (payload) kết hợp Visibility Map all-visible',
    risk: 'Phát sinh Heap Fetches đọc thêm trang bảng heap, phương sai độ trễ tăng',
    action: 'Thêm mệnh đề INCLUDE và thiết lập VACUUM ANALYZE định kỳ',
  },
  {
    category: 'Event Log Key Order',
    standard: 'Mốc thời gian đơn điệu (event_ts) dẫn đầu chỉ mục ghi chèn',
    risk: 'Bùng nổ 350 trang Full-Page Writes (FPI) trong WAL, phân mảnh lá',
    action: 'Đặt event_ts dẫn đầu chỉ mục hoặc sử dụng LSM-Tree Store (RocksDB)',
  },
];

