import React from 'react';
import { ZoomIn, Sigma, CheckCircle, TrendingUp } from 'lucide-react';

interface QueueingTheoryTabProps {
  onOpenImageModal: (src: string, title: string, caption: string, analysis?: string) => void;
}

export const QueueingTheoryTab: React.FC<QueueingTheoryTabProps> = ({ onOpenImageModal }) => {
  return (
    <div className="space-y-8 animate-fadeIn">
      {/* 4.1 Định lý hàng đợi Pollaczek-Khinchine */}
      <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center gap-2.5 text-xs font-bold uppercase tracking-wider text-emerald-700 mb-2">
          <Sigma className="w-4 h-4" />
          Cơ Sở Toán Học &amp; Phân Tích Chuyên Sâu
        </div>
        <h2 className="text-xl font-bold text-slate-900">
          Kiểm Chứng Định Lý Hàng Đợi Pollaczek-Khinchine (M/G/1) &amp; Độ Trễ Đuôi Nặng
        </h2>
        <p className="text-sm text-slate-600 mt-1 leading-relaxed">
          Độ trễ phân vị đuôi cực đoan (<span className="font-semibold text-slate-800">p99, p99.9</span>) trong hệ thống cơ sở dữ liệu 
          hoàn toàn không được quyết định bởi thời gian xử lý trung bình (<span className="font-serif italic font-bold">µ</span>), 
          mà bị chi phối áp đảo bởi <span className="font-bold text-emerald-700">Phương sai của thời gian phục vụ (σ²)</span> phát sinh từ các xung đột vi kiến trúc nền.
        </p>

        {/* Mathematical Formula Card */}
        <div className="mt-5 p-6 rounded-xl border border-emerald-200 bg-emerald-50/50 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="space-y-2 max-w-xl">
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-900">
              Công Thức Định Lý Pollaczek-Khinchine
            </span>
            <div className="text-2xl sm:text-3xl font-extrabold text-emerald-950 font-serif tracking-wide py-1">
              W<sub>q</sub> = <span className="inline-block text-center align-middle">
                <span className="block border-b-2 border-emerald-950 pb-0.5">λ (µ² + σ²)</span>
                <span className="block pt-0.5">2 (1 - ρ)</span>
              </span>
            </div>
            <p className="text-xs text-slate-700 leading-relaxed">
              Trong đó: <span className="font-serif italic font-semibold">λ</span> là tốc độ yêu cầu truy vấn đến; 
              <span className="font-serif italic font-semibold"> µ</span> là thời gian xử lý trung bình; 
              <span className="font-mono font-bold text-emerald-800"> σ² = Var(S)</span> là phương sai thời gian phục vụ; 
              <span className="font-serif italic font-semibold"> ρ = λµ &lt; 1</span> là cường độ sử dụng tài nguyên.
            </p>
          </div>

          <div className="p-4 bg-white rounded-xl border border-emerald-200 shadow-sm shrink-0 space-y-3 min-w-[260px]">
            <div className="text-xs font-bold text-slate-900 uppercase tracking-wider border-b border-slate-100 pb-1.5 flex items-center gap-1.5">
              <CheckCircle className="w-4 h-4 text-emerald-600" />
              Hệ Số Tương Quan Pearson r
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-600">PostgreSQL (B-Tree):</span>
              <span className="font-mono font-black text-emerald-700 text-sm">r = 0.9562</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-600">RocksDB (LSM-Tree):</span>
              <span className="font-mono font-black text-emerald-700 text-sm">r = 0.9762</span>
            </div>
            <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-100 italic">
              Chứng minh thực nghiệm 100% khớp lý thuyết xếp hàng (r ≥ 0.95).
            </div>
          </div>
        </div>

        {/* 2 Figures: Spikes and CDF */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
          {/* Figure 3.5 */}
          <div 
            onClick={() => onOpenImageModal(
              '/plots/Hinh_3_5_Timeseries_Tail_Latency_Spikes.png',
              'Hình 3.5: Chuỗi thời gian độ trễ đọc theo từng giây (Time-Series Latency Spikes)',
              'Hình 3.5: Chuỗi đo 1 giây (Workload A: 50R/50W, 32 Threads): Đỉnh nhọn độ trễ đọc p99 trên PostgreSQL (63.93ms do Page Split và chốt WAL) và RocksDB (215.41ms do xả MemTable và nén L0 -> L1).',
              'Minh chứng rõ ràng hiện tượng xung đột giữa luồng ghi nền với luồng đọc, kích hoạt các đỉnh nhọn độ trễ phá vỡ cam kết chất lượng dịch vụ SLA.'
            )}
            className="group cursor-pointer rounded-xl border border-slate-200 p-3 bg-slate-50/40 hover:bg-white hover:shadow-md transition-all"
          >
            <div className="relative overflow-hidden rounded-lg bg-white border border-slate-200">
              <img
                src="/plots/Hinh_3_5_Timeseries_Tail_Latency_Spikes.png"
                alt="Hình 3.5: Chuỗi thời gian độ trễ tức thời"
                className="w-full h-56 object-contain group-hover:scale-[1.02] transition-transform duration-200"
              />
              <span className="absolute top-2 right-2 p-1.5 rounded-lg bg-slate-900/60 text-white opacity-0 group-hover:opacity-100 transition-opacity">
                <ZoomIn className="w-4 h-4" />
              </span>
            </div>
            <div className="mt-3">
              <div className="text-xs font-bold text-slate-900 flex items-center justify-between">
                <span>Hình 3.5: Đột Biến Chuỗi Thời Gian (Latency Spikes)</span>
                <span className="text-[10px] text-blue-600 font-semibold">Phóng to 300 DPI</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
                Đỉnh nhọn p99 tại từng giây dưới tải ghi hỗn hợp 50% Read / 50% Write (32 luồng).
              </p>
            </div>
          </div>

          {/* Figure 3.6 */}
          <div 
            onClick={() => onOpenImageModal(
              '/plots/Hinh_3_6_CDF_Tail_Latency.png',
              'Hình 3.6: Phân phối tích lũy CDF của độ trễ đuôi nặng (Heavy-Tail CDF)',
              'Hình 3.6: Đường cong phân phối tích lũy CDF: Với I_opt và K_opt, 95% truy vấn hoàn tất ở mức micro-giây/mili-giây thấp. Ngược lại, với I_inv và K_inv, đuôi phân vị bị kéo dãn qua hơn 4 bậc độ lớn.',
              'Chứng minh hiện tượng phân kỳ đuôi nặng cực đoan (Heavy-Tail Latency), khẳng định độ trễ đuôi p99.9 và Max cao gấp hàng trăm lần trung vị p50.'
            )}
            className="group cursor-pointer rounded-xl border border-slate-200 p-3 bg-slate-50/40 hover:bg-white hover:shadow-md transition-all"
          >
            <div className="relative overflow-hidden rounded-lg bg-white border border-slate-200">
              <img
                src="/plots/Hinh_3_6_CDF_Tail_Latency.png"
                alt="Hình 3.6: Phân phối tích lũy CDF"
                className="w-full h-56 object-contain group-hover:scale-[1.02] transition-transform duration-200"
              />
              <span className="absolute top-2 right-2 p-1.5 rounded-lg bg-slate-900/60 text-white opacity-0 group-hover:opacity-100 transition-opacity">
                <ZoomIn className="w-4 h-4" />
              </span>
            </div>
            <div className="mt-3">
              <div className="text-xs font-bold text-slate-900 flex items-center justify-between">
                <span>Hình 3.6: Phân Phối Tích Lũy Đuôi Nặng (CDF)</span>
                <span className="text-[10px] text-blue-600 font-semibold">Phóng to 300 DPI</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
                Hàm phân phối tích lũy CDF thể hiện rõ sự dốc đứng của cấu hình tối ưu và sự dạt sang phải của cấu hình vi phạm.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 4.2 Mở rộng Archetypes (Phase 8: Master Data & Event Ingestion) */}
      <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center gap-2.5 text-xs font-bold uppercase tracking-wider text-blue-700 mb-2">
          <TrendingUp className="w-4 h-4" />
          Mở Rộng Vi Kiến Trúc (Archetypes Extension)
        </div>
        <h2 className="text-xl font-bold text-slate-900">
          Chỉ Mục Bao Phủ (Master Data) &amp; Nạp Dữ Liệu Sự Kiện (Event Log Ingestion)
        </h2>
        <p className="text-sm text-slate-600 mt-1 leading-relaxed">
          Đánh giá định lượng hai dạng bài toán phổ biến trong doanh nghiệp: Tra cứu điểm trên dữ liệu danh mục 
          và Nạp dữ liệu sự kiện ghi nối đuôi tốc độ cao.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
          {/* Figure 3.7 */}
          <div 
            onClick={() => onOpenImageModal(
              '/plots/Hinh_3_7_MasterData_IndexOnlyScan.png',
              'Hình 3.7: Master Data - So sánh Standard Index vs. Covering Index (INCLUDE - Index-Only Scan)',
              'Hình 3.7: Trên bảng tenants (10,000 bản ghi): Cấu hình Covering Index I_MD_COV (region_id, tenant_code) INCLUDE (credit_limit) đạt Heap Fetches = 0 tuyệt đối, giảm phương sai độ trễ 20% và triệt tiêu đỉnh nhọn trễ cực đại từ 17.10ms xuống 5.13ms (giảm 3.3×).',
              'Khẳng định vai trò của mệnh đề INCLUDE và Visibility Map: trả về dữ liệu trực tiếp từ lá B-Tree mà không cần chạm vào bảng Heap.'
            )}
            className="group cursor-pointer rounded-xl border border-slate-200 p-3 bg-slate-50/40 hover:bg-white hover:shadow-md transition-all"
          >
            <div className="relative overflow-hidden rounded-lg bg-white border border-slate-200">
              <img
                src="/plots/Hinh_3_7_MasterData_IndexOnlyScan.png"
                alt="Hình 3.7: Master Data Covering Index"
                className="w-full h-56 object-contain group-hover:scale-[1.02] transition-transform duration-200"
              />
              <span className="absolute top-2 right-2 p-1.5 rounded-lg bg-slate-900/60 text-white opacity-0 group-hover:opacity-100 transition-opacity">
                <ZoomIn className="w-4 h-4" />
              </span>
            </div>
            <div className="mt-3">
              <div className="text-xs font-bold text-slate-900 flex items-center justify-between">
                <span>Hình 3.7: Master Data Index-Only Scan</span>
                <span className="text-[10px] text-blue-600 font-semibold">Phóng to 300 DPI</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
                So sánh Standard vs. Covering Index (INCLUDE) kích hoạt Index-Only Scan (Heap Fetches = 0).
              </p>
            </div>
          </div>

          {/* Figure 3.8 */}
          <div 
            onClick={() => onOpenImageModal(
              '/plots/Hinh_3_8_EventLog_Ingestion_BTree_vs_LSM.png',
              'Hình 3.8: Event Log Ingestion - So sánh B-Tree vs. LSM-Tree nạp dữ liệu tuần tự',
              'Hình 3.8: Trên bảng order_events (100,000 sự kiện): Khóa thời gian dẫn đầu TIME_LEAD triệt tiêu 350 trang FPI trong WAL so với TENANT_LEAD. RocksDB LSM-Tree đạt thông lượng nạp 61,069 inserts/s (gấp 10.5× PostgreSQL) với p99 ≤ 0.042ms.',
              'Chứng minh cấu trúc MemTable của LSM-Tree hấp thụ ghi ngẫu nhiên trong RAM, vượt trội áp đảo kiến trúc ghi tại chỗ B-Tree.'
            )}
            className="group cursor-pointer rounded-xl border border-slate-200 p-3 bg-slate-50/40 hover:bg-white hover:shadow-md transition-all"
          >
            <div className="relative overflow-hidden rounded-lg bg-white border border-slate-200">
              <img
                src="/plots/Hinh_3_8_EventLog_Ingestion_BTree_vs_LSM.png"
                alt="Hình 3.8: Event Log Ingestion B-Tree vs LSM-Tree"
                className="w-full h-56 object-contain group-hover:scale-[1.02] transition-transform duration-200"
              />
              <span className="absolute top-2 right-2 p-1.5 rounded-lg bg-slate-900/60 text-white opacity-0 group-hover:opacity-100 transition-opacity">
                <ZoomIn className="w-4 h-4" />
              </span>
            </div>
            <div className="mt-3">
              <div className="text-xs font-bold text-slate-900 flex items-center justify-between">
                <span>Hình 3.8: Event Ingestion (B-Tree vs. LSM-Tree)</span>
                <span className="text-[10px] text-blue-600 font-semibold">Phóng to 300 DPI</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
                So sánh Full-Page Writes (FPI) trên PostgreSQL WAL và ưu thế vượt trội 10.5× của RocksDB MemTable.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
