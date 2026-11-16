import React, { useState } from 'react';
import { Database, AlertTriangle, ZoomIn, FileText, Filter, CheckCircle2, XCircle } from 'lucide-react';
import { postgresBenchmarkData, cboPlanComparisons } from '../../data/benchmarkData';
import { BenchmarkRow } from '../../types/benchmark';

interface PostgresTabProps {
  onOpenImageModal: (src: string, title: string, caption: string, analysis?: string) => void;
}

export const PostgresTab: React.FC<PostgresTabProps> = ({ onOpenImageModal }) => {
  const [filterWorkload, setFilterWorkload] = useState<string>('ALL');
  const [filterVariant, setFilterVariant] = useState<string>('ALL');
  const [filterThreads, setFilterThreads] = useState<string>('ALL');

  // Filtered rows
  const filteredData = postgresBenchmarkData.filter((r: BenchmarkRow) => {
    if (filterWorkload !== 'ALL' && r.workload !== filterWorkload) return false;
    if (filterVariant !== 'ALL' && r.variant !== filterVariant) return false;
    if (filterThreads !== 'ALL' && r.threads.toString() !== filterThreads) return false;
    return true;
  });

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* 3.4 Kết quả và Phân tích trên Kiến trúc B-Tree */}
      <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center gap-2.5 text-xs font-bold uppercase tracking-wider text-blue-700 mb-2">
          <Database className="w-4 h-4" />
          Mục 3.4 Đồ Án
        </div>
        <h2 className="text-xl font-bold text-slate-900">
          Kết Quả và Phân Tích Vi Kiến Trúc B-Tree (PostgreSQL 17)
        </h2>
        <h3 className="text-sm font-semibold text-slate-600 mt-1">
          3.4.1. Sự Dịch Chuyển Kế Hoạch Thực Thi CBO Do Vi Phạm Quy Tắc ESR
        </h3>

        {/* Narrative & Metrics */}
        <div className="mt-4 p-4 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-700 leading-relaxed space-y-3">
          <p>
            <strong>Báo cáo số liệu thực nghiệm:</strong> Dưới kịch bản tải đọc thuần túy (Workload C) ở mức 32 luồng đồng thời, 
            độ trễ phân vị đuôi <span className="font-semibold text-slate-900">p99</span> của cấu hình tối ưu tuân thủ quy tắc ESR{' '}
            <span className="font-mono text-emerald-700 font-bold">I_opt (tenant_id, status, created_at)</span> duy trì ở mức{' '}
            <span className="font-bold text-emerald-700">15.67 ms</span>. Khi đảo ngược thứ tự thuộc tính đưa cột trạng thái chọn lọc thấp lên trước{' '}
            <span className="font-mono text-red-700 font-bold">I_inv (status, created_at, tenant_id)</span>, độ trễ p99 bùng nổ lên{' '}
            <span className="font-bold text-red-700">55.49 ms</span> (tăng <span className="font-bold text-red-700">3.54 lần</span>).
          </p>
          <p>
            <strong>Khối I/O đọc ngẫu nhiên:</strong> Cấu hình <span className="font-mono text-emerald-700 font-bold">I_opt</span> chỉ tiêu tốn đúng{' '}
            <span className="font-bold text-emerald-700">3 khối bộ đệm (24KB)</span> với tổng chi phí CBO ước lượng là{' '}
            <span className="font-bold text-emerald-700">4.10</span>. Ngược lại, cấu hình vi phạm{' '}
            <span className="font-mono text-red-700 font-bold">I_inv</span> khiến lượng khối I/O đọc ngẫu nhiên tăng vọt{' '}
            <span className="font-bold text-red-700">27.7 lần</span> (lên <span className="font-bold text-red-700">83 khối đệm</span>), 
            kéo theo chi phí CBO tăng vọt <span className="font-bold text-red-700">85.8 lần</span> (lên 351.72).
          </p>
        </div>

        {/* Lossy Bitmap Deep-Dive Card */}
        <div className="mt-5 p-5 rounded-xl border border-amber-200 bg-amber-50/60 space-y-3">
          <div className="flex items-center gap-2 text-amber-900 font-bold text-sm">
            <AlertTriangle className="w-5 h-5 text-amber-600" />
            Luận Điểm Vi Kiến Trúc: Thảm Họa Suy Thoái Tràn Bộ Nhớ Lossy Bitmap Heap Scan
          </div>
          <p className="text-xs text-slate-700 leading-relaxed">
            Thuộc tính dẫn đầu <code className="text-red-700 font-bold">status</code> chỉ có 5 giá trị phân biệt (<span className="font-mono">n_distinct = 5</span>), 
            khiến mỗi nhánh trạng thái chứa tới ~100,000 con trỏ dữ liệu nằm rải rác trên toàn bộ 10,264 trang heap. 
            CBO bắt buộc từ bỏ <span className="font-semibold text-slate-800">Index Scan</span> thuần túy và chuyển sang{' '}
            <span className="font-semibold text-slate-800">Bitmap Index Scan</span>.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
            <div className="p-3 bg-white rounded-lg border border-amber-200">
              <div className="text-[10px] text-slate-400 font-bold uppercase">Cạn kiệt work_mem (64KB)</div>
              <div className="text-lg font-black text-red-700">7,247 Trang</div>
              <div className="text-[11px] text-slate-600">Suy thoái thành Lossy Page Flag</div>
            </div>
            <div className="p-3 bg-white rounded-lg border border-amber-200">
              <div className="text-[10px] text-slate-400 font-bold uppercase">CPU Phục hồi Dữ liệu</div>
              <div className="text-lg font-black text-red-700">340,023 Dòng</div>
              <div className="text-[11px] text-slate-600">Rows Rechecked by Filter</div>
            </div>
            <div className="p-3 bg-white rounded-lg border border-amber-200">
              <div className="text-[10px] text-slate-400 font-bold uppercase">Biến động Phương sai σ²</div>
              <div className="text-lg font-black text-red-700">107.85 ms²</div>
              <div className="text-[11px] text-slate-600">Bùng nổ kéo theo p99 sụp đổ</div>
            </div>
          </div>
        </div>

        {/* 2 Figures Side-by-Side */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
          {/* Figure 3.1 */}
          <div 
            onClick={() => onOpenImageModal(
              '/plots/Hinh_3_1_Postgres_Latency_Order.png',
              'Hình 3.1: So sánh Thông lượng và Độ trễ phân vị đuôi p99 trên PostgreSQL',
              'Hình 3.1: So sánh Thông lượng xử lý (Panel a) và Độ trễ phân vị đuôi p99 (Panel b) trên PostgreSQL 17 giữa cấu hình tối ưu I_opt và nghịch đảo I_inv qua các mức độ đồng thời (1 đến 32 luồng).',
              'Đồ thị chứng minh I_opt duy trì thông lượng ổn định trên 3,100 ops/s, trong khi I_inv bị nghẽn ở ~2,000 ops/s và đường cong độ trễ dốc đứng khi số luồng vượt quá 8.'
            )}
            className="group cursor-pointer rounded-xl border border-slate-200 p-3 bg-slate-50/40 hover:bg-white hover:shadow-md transition-all"
          >
            <div className="relative overflow-hidden rounded-lg bg-white border border-slate-200">
              <img
                src="/plots/Hinh_3_1_Postgres_Latency_Order.png"
                alt="Hình 3.1: Thông lượng và Độ trễ p99 PostgreSQL"
                className="w-full h-56 object-contain group-hover:scale-[1.02] transition-transform duration-200"
              />
              <span className="absolute top-2 right-2 p-1.5 rounded-lg bg-slate-900/60 text-white opacity-0 group-hover:opacity-100 transition-opacity">
                <ZoomIn className="w-4 h-4" />
              </span>
            </div>
            <div className="mt-3">
              <div className="text-xs font-bold text-slate-900 flex items-center justify-between">
                <span>Hình 3.1: Thông lượng &amp; Độ trễ p99</span>
                <span className="text-[10px] text-blue-600 font-semibold">Phóng to 300 DPI</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
                Trục X: 1, 4, 8, 16, 32 Threads. Panel (a) Throughput; Panel (b) p99 latency curve.
              </p>
            </div>
          </div>

          {/* Figure 3.2 */}
          <div 
            onClick={() => onOpenImageModal(
              '/plots/Hinh_3_2_Postgres_CBO_Correlation_Blocks.png',
              'Hình 3.2: Phân tích cơ chế suy thoái vi kiến trúc CBO và sụp đổ Bitmap Heap Scan trên PostgreSQL',
              'Hình 3.2: Cơ chế suy thoái vi kiến trúc trên PostgreSQL 17: (a) Chi phí CBO và khối đọc đệm trên thang Logarit; (b) Sự chuyển dịch từ Exact Heap Blocks sang Lossy Heap Blocks khi cạn kiệt work_mem.',
              'Panel (a) chứng minh chi phí CBO tăng 85.8× và khối đọc tăng 27.7×. Panel (b) minh họa 7,247 khối trang heap bị suy thoái thành Lossy khi work_mem = 64KB.'
            )}
            className="group cursor-pointer rounded-xl border border-slate-200 p-3 bg-slate-50/40 hover:bg-white hover:shadow-md transition-all"
          >
            <div className="relative overflow-hidden rounded-lg bg-white border border-slate-200">
              <img
                src="/plots/Hinh_3_2_Postgres_CBO_Correlation_Blocks.png"
                alt="Hình 3.2: Chi phí CBO và Suy thoái Lossy Blocks"
                className="w-full h-56 object-contain group-hover:scale-[1.02] transition-transform duration-200"
              />
              <span className="absolute top-2 right-2 p-1.5 rounded-lg bg-slate-900/60 text-white opacity-0 group-hover:opacity-100 transition-opacity">
                <ZoomIn className="w-4 h-4" />
              </span>
            </div>
            <div className="mt-3">
              <div className="text-xs font-bold text-slate-900 flex items-center justify-between">
                <span>Hình 3.2: CBO Cost &amp; Lossy Heap Scan</span>
                <span className="text-[10px] text-blue-600 font-semibold">Phóng to 300 DPI</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
                CBO Cost &amp; Shared Read Blocks (Panel a); Exact vs. Lossy Heap Blocks (Panel b).
              </p>
            </div>
          </div>
        </div>

        {/* Table 2.3.1: CBO Execution Plan Diagnosis */}
        <div className="mt-8 pt-6 border-t border-slate-100">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3 flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-600" />
            Bảng Chẩn Đoán Kế Hoạch Thực Thi CBO &amp; Khối Bộ Đệm (Truy Vấn Mẫu 1)
          </h3>
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-100 text-slate-700 border-b border-slate-200 font-bold">
                  <th className="py-2.5 px-4">Tham số vi kiến trúc CBO</th>
                  <th className="py-2.5 px-4 bg-emerald-50 text-emerald-900">Cấu hình Tối ưu (I_opt)</th>
                  <th className="py-2.5 px-4 bg-red-50 text-red-900">Cấu hình Nghịch đảo (I_inv)</th>
                  <th className="py-2.5 px-4 text-slate-600">Không chỉ mục (I_none)</th>
                  <th className="py-2.5 px-4 text-slate-800">Tỷ lệ suy thoái (I_inv / I_opt)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-600 font-sans">
                {cboPlanComparisons.map((row, idx) => (
                  <tr key={idx} className={idx % 2 === 1 ? 'bg-slate-50/50' : 'bg-white'}>
                    <td className="py-2 px-4 font-semibold text-slate-900">{row.parameter}</td>
                    <td className="py-2 px-4 font-mono font-bold text-emerald-800 bg-emerald-50/30">{row.opt}</td>
                    <td className="py-2 px-4 font-mono font-bold text-red-800 bg-red-50/30">{row.inv}</td>
                    <td className="py-2 px-4 font-mono text-slate-500">{row.none}</td>
                    <td className="py-2 px-4 font-semibold text-slate-800">{row.ratio}</td>
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
                <Database className="w-4 h-4 text-blue-600" />
                Ma Trận Thực Nghiệm Đầy Đủ (30 Điểm Đo PostgreSQL 17)
              </h3>
              <p className="text-[11px] text-slate-500">
                Hiển thị dữ liệu trích xuất chính thức từ <code className="text-blue-700">postgres_matrix_results.csv</code>
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
                <option value="ALL">Tất cả Chỉ mục</option>
                <option value="I_OPT">I_OPT (Tối ưu)</option>
                <option value="I_INV_LOW_SEL">I_INV (Nghịch đảo)</option>
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
                  <th className="py-2.5 px-3">Chỉ mục</th>
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
                  const isOpt = r.variant === 'I_OPT';
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

