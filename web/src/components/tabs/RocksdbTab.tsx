import React, { useState } from 'react';
import { Binary, AlertOctagon, ZoomIn, FileText, Filter, CheckCircle2, XCircle, Cpu } from 'lucide-react';
import { rocksdbBenchmarkData, perfContextTelemetries } from '../../data/benchmarkData';
import { BenchmarkRow } from '../../types/benchmark';

interface RocksdbTabProps {
  onOpenImageModal: (src: string, title: string, caption: string, analysis?: string) => void;
}

export const RocksdbTab: React.FC<RocksdbTabProps> = ({ onOpenImageModal }) => {
  const [filterWorkload, setFilterWorkload] = useState<string>('ALL');
  const [filterVariant, setFilterVariant] = useState<string>('ALL');
  const [filterThreads, setFilterThreads] = useState<string>('ALL');

  // Filtered rows
  const filteredData = rocksdbBenchmarkData.filter((r: BenchmarkRow) => {
    if (filterWorkload !== 'ALL' && r.workload !== filterWorkload) return false;
    if (filterVariant !== 'ALL' && r.variant !== filterVariant) return false;
    if (filterThreads !== 'ALL' && r.threads.toString() !== filterThreads) return false;
    return true;
  });

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* 3.5 Kết quả và Phân tích trên Kiến trúc LSM-Tree */}
      <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center gap-2.5 text-xs font-bold uppercase tracking-wider text-purple-700 mb-2">
          <Binary className="w-4 h-4" />
          Mục 3.5 Đồ Án
        </div>
        <h2 className="text-xl font-bold text-slate-900">
          Kết Quả và Phân Tích Vi Kiến Trúc LSM-Tree (RocksDB 9.10)
        </h2>
        <h3 className="text-sm font-semibold text-slate-600 mt-1">
          3.5.1. Thảm Họa Khuếch Đại Đọc Do Sai Lệch Bố Cục Khóa &amp; Endianness
        </h3>

        {/* Narrative & Metrics */}
        <div className="mt-4 p-4 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-700 leading-relaxed space-y-3">
          <p>
            <strong>Báo cáo số liệu thực nghiệm:</strong> Dưới kịch bản tải đọc thuần túy (Workload C), cấu hình khóa tối ưu{' '}
            <span className="font-mono text-emerald-700 font-bold">K_opt [tenant_id: 4B][status: 1B][created_at: 8B][order_id: 8B]</span> đạt 
            thông lượng cực đại lên tới <span className="font-bold text-emerald-700">255,264.1 ops/giây</span> tại 16 luồng và duy trì{' '}
            <span className="font-bold text-emerald-700">209,306.8 ops/giây</span> tại 32 luồng. Ngược lại, cấu hình vi phạm thứ tự khóa{' '}
            <span className="font-mono text-red-700 font-bold">K_inv [status: 1B][created_at: 8B][tenant_id: 4B][order_id: 8B]</span> chỉ đạt thông lượng vỏn vẹn{' '}
            <span className="font-bold text-red-700">589.5 ops/giây</span> tại 32 luồng — tương đương mức sụp đổ hiệu năng kinh hoàng{' '}
            <span className="font-bold text-red-700">355.0 lần</span>.
          </p>
          <p>
            <strong>Ảo tưởng độ trễ trung vị p50 và sự bùng nổ p99:</strong> Ở luồng đơn, độ trễ trung vị p50 của hai cấu hình chỉ chênh lệch nhẹ 
            (0.007ms so với 3.23ms), dễ tạo ra ảo tưởng đánh giá sai lệch trong các hệ thống giám sát nông. Tuy nhiên, khi chịu tải đồng thời 32 luồng, 
            độ trễ phân vị đuôi p99 của <span className="font-mono text-red-700 font-bold">K_inv</span> bị thổi bùng từ{' '}
            <span className="font-bold text-slate-900">0.091 ms</span> lên tới <span className="font-bold text-red-700">220.57 ms</span> (trong Workload B) 
            và <span className="font-bold text-red-700">219.20 ms</span> (trong Workload C) — tức mức tăng bùng nổ{' '}
            <span className="font-bold text-red-700">hơn 2,400 lần</span>.
          </p>
        </div>

        {/* 21-Byte Binary Key Structure Visualization */}
        <div className="mt-5 p-5 rounded-xl border border-purple-200 bg-purple-50/50 space-y-4">
          <div className="flex items-center gap-2 text-purple-900 font-bold text-sm">
            <Cpu className="w-5 h-5 text-purple-700" />
            Đặc Tả Khóa Ghép Nhị Phân 21-Byte &amp; Cơ Chế memcmp() Cấp Thấp
          </div>

          <div className="space-y-3 font-mono text-xs">
            {/* K_opt layout */}
            <div>
              <div className="text-[11px] font-sans font-bold text-emerald-800 mb-1 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                Khóa Tối Ưu (K_opt): Khớp chính xác 4-byte Prefix Bloom Filter
              </div>
              <div className="grid grid-cols-12 gap-1 text-center font-bold">
                <div className="col-span-3 p-2 rounded-lg bg-emerald-600 text-white shadow-sm border border-emerald-700">
                  <div className="text-[10px] opacity-80">[0 .. 3] 4 Bytes</div>
                  <div>tenant_id (BE)</div>
                  <div className="text-[9px] opacity-90 mt-0.5">FixedPrefixTransform(4)</div>
                </div>
                <div className="col-span-1 p-2 rounded-lg bg-blue-600 text-white shadow-sm border border-blue-700">
                  <div className="text-[10px] opacity-80">[4] 1B</div>
                  <div>status</div>
                </div>
                <div className="col-span-4 p-2 rounded-lg bg-slate-700 text-white shadow-sm border border-slate-800">
                  <div className="text-[10px] opacity-80">[5 .. 12] 8 Bytes</div>
                  <div>created_at (uint64 BE)</div>
                </div>
                <div className="col-span-4 p-2 rounded-lg bg-slate-600 text-white shadow-sm border border-slate-700">
                  <div className="text-[10px] opacity-80">[13 .. 20] 8 Bytes</div>
                  <div>order_id (uint64 BE)</div>
                </div>
              </div>
            </div>

            {/* K_inv layout */}
            <div className="pt-2">
              <div className="text-[11px] font-sans font-bold text-red-800 mb-1 flex items-center gap-1.5">
                <XCircle className="w-4 h-4 text-red-600" />
                Khóa Nghịch Đảo (K_inv): Phá hủy hoàn toàn vùng Byte Tiếp đầu ngữ
              </div>
              <div className="grid grid-cols-12 gap-1 text-center font-bold">
                <div className="col-span-1 p-2 rounded-lg bg-red-600 text-white shadow-sm border border-red-700">
                  <div className="text-[10px] opacity-80">[0] 1B</div>
                  <div>status</div>
                </div>
                <div className="col-span-4 p-2 rounded-lg bg-red-500 text-white shadow-sm border border-red-600">
                  <div className="text-[10px] opacity-80">[1 .. 8] 8 Bytes</div>
                  <div>created_at (uint64 BE)</div>
                </div>
                <div className="col-span-3 p-2 rounded-lg bg-slate-500 text-white shadow-sm border border-slate-600">
                  <div className="text-[10px] opacity-80">[9 .. 12] 4B</div>
                  <div>tenant_id (BE)</div>
                </div>
                <div className="col-span-4 p-2 rounded-lg bg-slate-600 text-white shadow-sm border border-slate-700">
                  <div className="text-[10px] opacity-80">[13 .. 20] 8 Bytes</div>
                  <div>order_id (uint64 BE)</div>
                </div>
              </div>
            </div>
          </div>

          <div className="p-3 bg-white rounded-lg border border-purple-200 text-xs text-slate-700 leading-relaxed">
            <span className="font-bold text-purple-900">Chuẩn hóa Unsigned Big-Endian:</span> RocksDB so sánh các khóa dựa trên hàm{' '}
            <code className="text-purple-700 font-bold">memcmp()</code>. Biểu diễn Big-Endian lưu byte có trọng số lớn nhất (MSB) tại địa chỉ thấp nhất, 
            bảo đảm thứ tự từ điển đồng nhất 100% với thứ tự số học. Nếu dùng Little-Endian, giá trị 256 (<span className="font-mono">0x00 0x01</span>) 
            bị coi là nhỏ hơn 1 (<span className="font-mono">0x01 0x00</span>), phá hủy hoàn toàn thuật toán quét phạm vi.
          </div>
        </div>

        {/* Microarchitectural Failure Mechanism Cards */}
        <div className="mt-5 p-5 rounded-xl border border-red-200 bg-red-50/60 space-y-3">
          <div className="flex items-center gap-2 text-red-900 font-bold text-sm">
            <AlertOctagon className="w-5 h-5 text-red-600" />
            Chuỗi Phản Ứng Dây Chuyền Khi Vô Hiệu Hóa 100% Prefix Bloom Filter
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
            <div className="p-3 bg-white rounded-lg border border-red-200">
              <div className="text-[10px] text-slate-400 font-bold uppercase">Tê Liệt Bloom Filter</div>
              <div className="text-lg font-black text-red-700">0 SSTable Miss</div>
              <div className="text-[11px] text-slate-600">Mất hoàn toàn khả năng cắt tỉa SSTable trên RAM</div>
            </div>
            <div className="p-3 bg-white rounded-lg border border-red-200">
              <div className="text-[10px] text-slate-400 font-bold uppercase">So Sánh Khóa CPU</div>
              <div className="text-lg font-black text-red-700">19,833 / op (342×)</div>
              <div className="text-[11px] text-slate-600">MergingIterator lục tung L0 → L6</div>
            </div>
            <div className="p-3 bg-white rounded-lg border border-red-200">
              <div className="text-[10px] text-slate-400 font-bold uppercase">Block Cache Thrashing</div>
              <div className="text-lg font-black text-red-700">238.1 Tra Cứu/op</div>
              <div className="text-[11px] text-slate-600">Xáo trộn đẩy dữ liệu hữu ích ra khỏi RAM</div>
            </div>
          </div>
        </div>

        {/* 2 Figures Side-by-Side */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
          {/* Figure 3.3 */}
          <div 
            onClick={() => onOpenImageModal(
              '/plots/Hinh_3_3_RocksDB_Latency_KeyOrder.png',
              'Hình 3.3: So sánh Thông lượng và Độ trễ phân vị đuôi p99 trên RocksDB',
              'Hình 3.3: So sánh hiệu năng trên RocksDB 9.10: (a) Thông lượng xử lý trên thang đo Logarit; (b) Độ trễ phân vị p50 và p99 giữa cấu hình khóa tối ưu K_opt và nghịch đảo K_inv qua các luồng thực thi.',
              'Panel (a) chứng minh K_opt đạt đỉnh 255k ops/s trong khi K_inv sụp đổ xuống dưới 600 ops/s (suy giảm 355×). Panel (b) thể hiện độ trễ p99 vọt lên 220ms trên thang Log10.'
            )}
            className="group cursor-pointer rounded-xl border border-slate-200 p-3 bg-slate-50/40 hover:bg-white hover:shadow-md transition-all"
          >
            <div className="relative overflow-hidden rounded-lg bg-white border border-slate-200">
              <img
                src="/plots/Hinh_3_3_RocksDB_Latency_KeyOrder.png"
                alt="Hình 3.3: Thông lượng và Độ trễ p99 RocksDB"
                className="w-full h-56 object-contain group-hover:scale-[1.02] transition-transform duration-200"
              />
              <span className="absolute top-2 right-2 p-1.5 rounded-lg bg-slate-900/60 text-white opacity-0 group-hover:opacity-100 transition-opacity">
                <ZoomIn className="w-4 h-4" />
              </span>
            </div>
            <div className="mt-3">
              <div className="text-xs font-bold text-slate-900 flex items-center justify-between">
                <span>Hình 3.3: Thông lượng &amp; Độ trễ RocksDB (Log10)</span>
                <span className="text-[10px] text-blue-600 font-semibold">Phóng to 300 DPI</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
                Trục X: 1, 4, 8, 16, 32 Threads. Throughput Log10 (Panel a); Latency p50 &amp; p99 (Panel b).
              </p>
            </div>
          </div>

          {/* Figure 3.4 */}
          <div 
            onClick={() => onOpenImageModal(
              '/plots/Hinh_3_4_RocksDB_BloomFilter_ReadAmp.png',
              'Hình 3.4: Bằng chứng vi kiến trúc RocksDB: Sự vô hiệu hóa Prefix Bloom Filter và Khuếch đại đọc',
              'Hình 3.4: Bằng chứng vi kiến trúc RocksDB trích xuất từ PerfContext: (a) Tương quan giữa việc vô hiệu hóa Prefix Bloom Filter (miss count = 0); (b) Sự bùng nổ so sánh khóa CPU và khuếch đại khối đọc đĩa.',
              'Minh chứng rõ ràng nhất về sự tê liệt của tầng lọc Bloom trên RAM, ép I/O đĩa cơ học phải chịu tải trực tiếp.'
            )}
            className="group cursor-pointer rounded-xl border border-slate-200 p-3 bg-slate-50/40 hover:bg-white hover:shadow-md transition-all"
          >
            <div className="relative overflow-hidden rounded-lg bg-white border border-slate-200">
              <img
                src="/plots/Hinh_3_4_RocksDB_BloomFilter_ReadAmp.png"
                alt="Hình 3.4: Bằng chứng vi kiến trúc RocksDB Bloom Filter"
                className="w-full h-56 object-contain group-hover:scale-[1.02] transition-transform duration-200"
              />
              <span className="absolute top-2 right-2 p-1.5 rounded-lg bg-slate-900/60 text-white opacity-0 group-hover:opacity-100 transition-opacity">
                <ZoomIn className="w-4 h-4" />
              </span>
            </div>
            <div className="mt-3">
              <div className="text-xs font-bold text-slate-900 flex items-center justify-between">
                <span>Hình 3.4: Bloom Filter &amp; Read Amplification</span>
                <span className="text-[10px] text-blue-600 font-semibold">Phóng to 300 DPI</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
                Chỉ số cắt tỉa SSTable (Panel a); Số phép so sánh khóa và khối đọc đĩa (Panel b).
              </p>
            </div>
          </div>
        </div>

        {/* Table 3.3: Microarchitectural PerfContext Telemetry */}
        <div className="mt-8 pt-6 border-t border-slate-100">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3 flex items-center gap-2">
            <FileText className="w-4 h-4 text-purple-600" />
            Bảng Đối Chứng Chỉ Số Vi Kiến Trúc Nội Tại RocksDB PerfContext
          </h3>
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-100 text-slate-700 border-b border-slate-200 font-bold">
                  <th className="py-2.5 px-4">Chỉ số vi kiến trúc (PerfContext)</th>
                  <th className="py-2.5 px-4 bg-emerald-50 text-emerald-900">Khóa tối ưu (K_opt)</th>
                  <th className="py-2.5 px-4 bg-red-50 text-red-900">Khóa nghịch đảo (K_inv)</th>
                  <th className="py-2.5 px-4 text-slate-700">Tỷ lệ chênh lệch</th>
                  <th className="py-2.5 px-4 text-slate-800">Tác động vi kiến trúc vật lý</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-600 font-sans">
                {perfContextTelemetries.map((row, idx) => (
                  <tr key={idx} className={idx % 2 === 1 ? 'bg-slate-50/50' : 'bg-white'}>
                    <td className="py-2 px-4 font-semibold text-slate-900">{row.metric}</td>
                    <td className="py-2 px-4 font-mono font-bold text-emerald-800 bg-emerald-50/30">{row.k_opt}</td>
                    <td className="py-2 px-4 font-mono font-bold text-red-800 bg-red-50/30">{row.k_inv}</td>
                    <td className="py-2 px-4 font-bold text-slate-800">{row.ratio}</td>
                    <td className="py-2 px-4 text-slate-700">{row.impact}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 30 Benchmark Matrix Results Interactive Table */}
        <div className="mt-8 pt-6 border-t border-slate-100">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-2">
                <Binary className="w-4 h-4 text-purple-600" />
                Ma Trận Thực Nghiệm Đầy Đủ (30 Điểm Đo RocksDB 9.10)
              </h3>
              <p className="text-[11px] text-slate-500">
                Hiển thị dữ liệu trích xuất chính thức từ <code className="text-purple-700">rocksdb_matrix_results.csv</code>
              </p>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-1 text-xs">
                <Filter className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-slate-500">Lọc:</span>
              </div>
              <select
                value={filterWorkload}
                onChange={(e) => setFilterWorkload(e.target.value)}
                className="px-2.5 py-1 text-xs font-medium rounded-lg border border-slate-200 bg-white text-slate-700"
              >
                <option value="ALL">Tất cả Workload</option>
                <option value="Workload_C">Workload C (100% R)</option>
                <option value="Workload_B">Workload B (95R/5W)</option>
                <option value="Workload_A">Workload A (50R/50W)</option>
              </select>

              <select
                value={filterVariant}
                onChange={(e) => setFilterVariant(e.target.value)}
                className="px-2.5 py-1 text-xs font-medium rounded-lg border border-slate-200 bg-white text-slate-700"
              >
                <option value="ALL">Tất cả Khóa</option>
                <option value="k_opt">K_opt (Tối ưu)</option>
                <option value="k_inv">K_inv (Nghịch đảo)</option>
              </select>

              <select
                value={filterThreads}
                onChange={(e) => setFilterThreads(e.target.value)}
                className="px-2.5 py-1 text-xs font-medium rounded-lg border border-slate-200 bg-white text-slate-700"
              >
                <option value="ALL">Tất cả Luồng</option>
                <option value="1">1 Thread</option>
                <option value="4">4 Threads</option>
                <option value="8">8 Threads</option>
                <option value="16">16 Threads</option>
                <option value="32">32 Threads</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-200 max-h-[480px]">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="sticky top-0 bg-slate-100 text-slate-700 border-b border-slate-200 font-bold z-10">
                <tr>
                  <th className="py-2.5 px-3">Workload</th>
                  <th className="py-2.5 px-3">Cấu hình khóa</th>
                  <th className="py-2.5 px-3 text-center">Threads</th>
                  <th className="py-2.5 px-3 text-right">Thông lượng (ops/s)</th>
                  <th className="py-2.5 px-3 text-right">p50 (ms)</th>
                  <th className="py-2.5 px-3 text-right">p95 (ms)</th>
                  <th className="py-2.5 px-3 text-right">p99 (ms)</th>
                  <th className="py-2.5 px-3 text-right">p99.9 (ms)</th>
                  <th className="py-2.5 px-3 text-right">Max (ms)</th>
                  <th className="py-2.5 px-3 text-right">Phương sai σ²</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono text-slate-600">
                {filteredData.map((r, idx) => {
                  const isOpt = r.variant === 'k_opt';
                  return (
                    <tr key={idx} className={isOpt ? 'hover:bg-emerald-50/40' : 'hover:bg-red-50/40'}>
                      <td className="py-2 px-3 font-sans font-medium text-slate-800">{r.workload.replace('_', ' ')}</td>
                      <td className="py-2 px-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${
                          isOpt ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {isOpt ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                          {r.variant}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-center font-bold text-slate-900">{r.threads}</td>
                      <td className="py-2 px-3 text-right font-bold text-slate-900">{r.total_throughput_ops.toLocaleString()}</td>
                      <td className="py-2 px-3 text-right">{r.p50_ms.toFixed(3)}</td>
                      <td className="py-2 px-3 text-right">{r.p95_ms.toFixed(3)}</td>
                      <td className={`py-2 px-3 text-right font-bold ${isOpt ? 'text-emerald-700' : 'text-red-700'}`}>
                        {r.p99_ms.toFixed(3)}
                      </td>
                      <td className="py-2 px-3 text-right">{r.p999_ms.toFixed(3)}</td>
                      <td className="py-2 px-3 text-right">{r.max_ms.toFixed(2)}</td>
                      <td className="py-2 px-3 text-right text-slate-700">{r.variance_ms2.toFixed(3)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
};
