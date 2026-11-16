import React from 'react';
import { Server, Box, Database, FileSpreadsheet, GitBranch, Layers, CheckCircle2 } from 'lucide-react';

export const OverviewTab: React.FC = () => {
  return (
    <div className="space-y-8 animate-fadeIn">
      {/* 3.1 Thiết lập Môi trường và Cấu trúc Phần cứng */}
      <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center gap-2.5 text-xs font-bold uppercase tracking-wider text-blue-700 mb-2">
          <Server className="w-4 h-4" />
          Mục 3.1 & 3.3 Đồ Án
        </div>
        <h2 className="text-xl font-bold text-slate-900">
          Thiết Lập Môi Trường, Hạ Tầng Phần Cứng & Quy Trình Đo Lường
        </h2>
        <p className="text-sm text-slate-600 mt-1 leading-relaxed">
          Toàn bộ các phép đo kiểm được chuẩn hóa và cô lập bằng công nghệ bộ chứa Docker kết hợp hệ thống kiểm soát tài nguyên 
          nhân Linux <span className="font-mono font-semibold text-slate-800">cgroup v2</span>, nhằm triệt tiêu hoàn toàn hiện tượng 
          nhiễu tài nguyên từ hệ điều hành máy chủ (Noisy Neighbors) và bảo đảm tính độc lập, có thể tái lập tuyệt đối (Reproducibility).
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
          {/* Hardware Spec */}
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50">
            <div className="flex items-center gap-2 font-bold text-sm text-slate-900 mb-3">
              <Server className="w-4 h-4 text-blue-600" />
              Máy Chủ Vật Lý (Host Server)
            </div>
            <ul className="text-xs text-slate-600 space-y-2">
              <li className="flex items-start gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0" />
                <span><strong>CPU:</strong> Vi xử lý kiến trúc x86_64 đa nhân hiện đại.</span>
              </li>
              <li className="flex items-start gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0" />
                <span><strong>Bộ nhớ RAM:</strong> 16GB DDR4 bus cao.</span>
              </li>
              <li className="flex items-start gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0" />
                <span><strong>Ổ cứng:</strong> NVMe SSD chuẩn PCIe Gen 3 (Đọc tuần tự ≥ 3,500 MB/s, IOPS ngẫu nhiên &gt; 250k).</span>
              </li>
            </ul>
          </div>

          {/* PostgreSQL 17 Spec */}
          <div className="p-4 rounded-xl border border-blue-200 bg-blue-50/40">
            <div className="flex items-center gap-2 font-bold text-sm text-blue-900 mb-3">
              <Database className="w-4 h-4 text-blue-700" />
              PostgreSQL 17 (B-Tree CBO)
            </div>
            <ul className="text-xs text-slate-600 space-y-2">
              <li className="flex items-start gap-1.5">
                <span className="font-mono text-[11px] text-blue-800 font-semibold">• cpus: 4.0</span>
                <span>/ mem_limit: 4GB</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="font-mono text-[11px] text-blue-800 font-semibold">• shared_buffers:</span>
                <span>1GB, random_page_cost: 1.2</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="font-mono text-[11px] text-red-700 font-semibold">• work_mem:</span>
                <span>4MB chuẩn (ép 64KB để kiểm chứng Lossy Bitmap)</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="font-mono text-[11px] text-blue-800 font-semibold">• fillfactor:</span>
                <span>85 (hấp thụ 15% ghi dự phòng chống page split)</span>
              </li>
            </ul>
          </div>

          {/* RocksDB 9.10 Spec */}
          <div className="p-4 rounded-xl border border-purple-200 bg-purple-50/40">
            <div className="flex items-center gap-2 font-bold text-sm text-purple-900 mb-3">
              <Box className="w-4 h-4 text-purple-700" />
              RocksDB 9.10 (Native C++ LSM)
            </div>
            <ul className="text-xs text-slate-600 space-y-2">
              <li className="flex items-start gap-1.5">
                <span className="font-mono text-[11px] text-purple-800 font-semibold">• cpus: 4.0</span>
                <span>/ mem_limit: 4GB</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="font-mono text-[11px] text-purple-800 font-semibold">• Compaction:</span>
                <span>kCompactionStyleLevel (7 tầng L0 → L6)</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="font-mono text-[11px] text-purple-800 font-semibold">• Bloom Filter:</span>
                <span>10 bits/key, xác suất p_fp ≈ 1%</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="font-mono text-[11px] text-purple-800 font-semibold">• Prefix Extractor:</span>
                <span>NewFixedPrefixTransform(4) (4 byte tenant_id)</span>
              </li>
            </ul>
          </div>
        </div>

        {/* 3-Phase Measurement Lifecycle */}
        <div className="mt-6 pt-5 border-t border-slate-100">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3">
            Quy trình Thực nghiệm 3 Giai đoạn Khép kín
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
              <span className="inline-block px-2 py-0.5 text-[10px] font-bold rounded bg-amber-100 text-amber-800 mb-1">
                GIAI ĐOẠN 1
              </span>
              <div className="text-xs font-bold text-slate-800">Làm Nóng Bộ Đệm (Warm-up)</div>
              <p className="text-[11px] text-slate-500 mt-1">
                Bắn tải liên tục trong 30 giây để nạp nóng Buffer Pool & Block Cache, triệt tiêu sai số khởi động lạnh (Cold Start).
              </p>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
              <span className="inline-block px-2 py-0.5 text-[10px] font-bold rounded bg-blue-100 text-blue-800 mb-1">
                GIAI ĐOẠN 2
              </span>
              <div className="text-xs font-bold text-slate-800">Bắn Tải Đa Luồng Đồng Thời</div>
              <p className="text-[11px] text-slate-500 mt-1">
                Đo kiểm độc lập qua 5 bậc đồng thời: 1, 4, 8, 16 và 32 threads nhằm quan sát điểm bão hòa và nghẽn hàng đợi.
              </p>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
              <span className="inline-block px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-100 text-emerald-800 mb-1">
                GIAI ĐOẠN 3
              </span>
              <div className="text-xs font-bold text-slate-800">Vi Đo Lường & Bóc Tách Telemetry</div>
              <p className="text-[11px] text-slate-500 mt-1">
                Đo nano-giây bằng HdrHistogram, trích xuất EXPLAIN JSON, pg_stat_statements và bộ đếm nội tại RocksDB PerfContext.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 3.2 Cấu trúc Dữ liệu & Bộ kịch bản */}
      <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center gap-2.5 text-xs font-bold uppercase tracking-wider text-blue-700 mb-2">
          <FileSpreadsheet className="w-4 h-4" />
          Mục 3.2 Đồ Án
        </div>
        <h2 className="text-xl font-bold text-slate-900">
          Cấu Trúc Lược Đồ Đa Người Thuê (Multi-tenant) & Bộ Tải Chuẩn YCSB
        </h2>
        <p className="text-sm text-slate-600 mt-1 leading-relaxed">
          Nguyên lý <span className="font-semibold text-slate-800">Đồng nhất Dữ liệu Logic (Data Equivalence)</span>: 
          Cả PostgreSQL và RocksDB đều tiếp nhận dữ liệu từ bộ sinh ngẫu nhiên có kiểm soát với hạt giống số học cố định 
          <span className="font-mono font-semibold text-blue-700"> RANDOM_SEED = 42</span>.
        </p>

        {/* Schema Specs */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
          {/* Orders Table */}
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50">
            <div className="flex items-center justify-between mb-3">
              <div className="font-bold text-sm text-slate-900 flex items-center gap-2">
                <Database className="w-4 h-4 text-blue-600" />
                Bảng Giao Dịch Đơn Hàng (orders)
              </div>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-800 font-semibold font-mono">
                N = 500,000 dòng (~82.1 MB)
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-400 uppercase text-[10px]">
                    <th className="py-2">Cột dữ liệu</th>
                    <th className="py-2">Kiểu</th>
                    <th className="py-2">n_distinct</th>
                    <th className="py-2">Hệ số r</th>
                    <th className="py-2">Đặc tính</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-600 font-mono">
                  <tr>
                    <td className="py-1.5 font-bold text-slate-900">order_id</td>
                    <td>BIGINT (8B)</td>
                    <td>-1.0 (Duy nhất)</td>
                    <td className="text-emerald-600">+1.0000</td>
                    <td className="font-sans text-[11px]">Primary Key, chèn tuần tự</td>
                  </tr>
                  <tr className="bg-blue-50/50">
                    <td className="py-1.5 font-bold text-blue-900">tenant_id</td>
                    <td>INT (4B)</td>
                    <td className="font-bold text-blue-800">9,977</td>
                    <td className="text-slate-500">+0.0013</td>
                    <td className="font-sans text-[11px] font-bold text-blue-800">Độ chọn lọc cao (0.01%/tenant)</td>
                  </tr>
                  <tr className="bg-red-50/50">
                    <td className="py-1.5 font-bold text-red-900">status</td>
                    <td>SMALLINT (1B)</td>
                    <td className="font-bold text-red-800">5 distinct</td>
                    <td className="text-slate-500">+0.1923</td>
                    <td className="font-sans text-[11px] font-bold text-red-800">Độ chọn lọc thấp (20%/status)</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 font-bold text-slate-900">created_at</td>
                    <td>BIGINT (8B)</td>
                    <td>-1.0</td>
                    <td className="text-slate-500">+0.0051</td>
                    <td className="font-sans text-[11px]">Epoch millis (Cửa sổ 365 ngày)</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 text-slate-800">amount</td>
                    <td>INT (4B)</td>
                    <td>-0.1724</td>
                    <td className="text-slate-500">-0.0048</td>
                    <td className="font-sans text-[11px]">100 ... 100,000</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 text-slate-800">payload</td>
                    <td>VARCHAR(100)</td>
                    <td>-1.0</td>
                    <td className="text-emerald-600">+1.0000</td>
                    <td className="font-sans text-[11px]">100 ký tự ASCII YCSB payload</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Tenants Table & Workload Skew */}
          <div className="space-y-4">
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50">
              <div className="flex items-center justify-between mb-2">
                <div className="font-bold text-sm text-slate-900 flex items-center gap-2">
                  <Layers className="w-4 h-4 text-purple-600" />
                  Bảng Danh Mục Khách Hàng (tenants)
                </div>
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-purple-100 text-purple-800 font-semibold font-mono">
                  10,000 dòng Master Data
                </span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Gồm: <code className="text-purple-700 font-bold">tenant_id (PK)</code>, <code className="text-slate-700">region_id</code>, 
                <code className="text-slate-700">tier_level</code>, <code className="text-slate-700">tenant_code</code>, 
                <code className="text-slate-700">credit_limit</code> và <code className="text-slate-700">tenant_info</code>. 
                Dùng để thực nghiệm Point Lookup, Covering Index (<code className="text-blue-700">INCLUDE</code>) và Index-Only Scan.
              </p>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50">
              <div className="font-bold text-sm text-slate-900 mb-2 flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-amber-600" />
                Phân Phối Lũy Thừa Scrambled Zipfian (s = 0.99)
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Tái tạo hiện tượng <span className="font-semibold text-slate-800">điểm nóng (hotspots)</span> trong thương mại điện tử thực tế: 
                khoảng 1% đến 5% số lượng người thuê lớn chiếm đa số tổng lưu lượng truy cập của toàn bộ hệ thống.
              </p>
              <div className="grid grid-cols-3 gap-2 mt-3 text-center">
                <div className="p-2 bg-white rounded-lg border border-slate-200">
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Workload C</div>
                  <div className="text-xs font-bold text-blue-700">100% Read</div>
                  <div className="text-[10px] text-slate-500">Đọc lọc phạm vi</div>
                </div>
                <div className="p-2 bg-white rounded-lg border border-slate-200">
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Workload B</div>
                  <div className="text-xs font-bold text-amber-700">95% R / 5% W</div>
                  <div className="text-[10px] text-slate-500">Đọc chiếm ưu thế</div>
                </div>
                <div className="p-2 bg-white rounded-lg border border-slate-200">
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Workload A</div>
                  <div className="text-xs font-bold text-red-700">50% R / 50% W</div>
                  <div className="text-[10px] text-slate-500">Cạnh tranh chốt ghi</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
