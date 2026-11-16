import React from 'react';
import { Database, Cpu, Activity, ShieldAlert, Sparkles, BookOpen, Layers } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-40 shadow-sm backdrop-blur-md bg-white/95">
      {/* Top Academic Banner */}
      <div className="bg-slate-900 text-slate-200 py-1.5 px-4 text-xs font-mono">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-slate-400">ĐỀ TÀI ĐỒ ÁN CHUYÊN NGÀNH CƠ SỞ DỮ LIỆU</span>
          </div>
          <div className="flex items-center gap-4 text-slate-400">
            <span>PostgreSQL 17 (B-Tree CBO)</span>
            <span>vs.</span>
            <span>RocksDB 9.10 (LSM-Tree Key-Value)</span>
          </div>
        </div>
      </div>

      {/* Main Title & Hero Intro */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2 max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-800 text-xs font-semibold">
              <Sparkles className="w-3.5 h-3.5 text-blue-600" />
              Báo cáo Thực nghiệm & Dashboard Vi kiến trúc CSDL
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight leading-tight">
              Nghiên cứu & Thực nghiệm Ảnh hưởng của Đánh Chỉ mục đến Hiệu năng Truy vấn
            </h1>
            <p className="text-sm sm:text-base text-slate-600 font-sans leading-relaxed">
              Giải mã cơ chế vật lý dẫn đến sự bùng nổ độ trễ đuôi (<span className="font-semibold text-slate-800">p99 / p99.9</span>)
              và kiểm chứng thực nghiệm bằng <span className="font-semibold text-blue-700">Định lý hàng đợi Pollaczek-Khinchine</span>.
            </p>
          </div>

          <div className="flex items-center gap-2 self-start lg:self-center">
            <a
              href="#rulebook"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-700 hover:bg-blue-800 text-white text-xs font-bold shadow-md shadow-blue-700/20 transition-all hover:shadow-lg hover:-translate-y-0.5"
            >
              <BookOpen className="w-4 h-4" />
              Tra cứu Rulebook
            </a>
            <a
              href="#calculator"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold border border-slate-300 transition-colors"
            >
              <Layers className="w-4 h-4 text-slate-600" />
              So sánh Cấu hình
            </a>
          </div>
        </div>

        {/* 4 Highlight Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
          {/* Card 1 */}
          <div className="p-4 rounded-xl bg-red-50/70 border border-red-200 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold text-red-900 uppercase tracking-wide">RocksDB Thông Lượng</span>
              <span className="p-1.5 rounded-lg bg-red-100 text-red-700">
                <ShieldAlert className="w-4 h-4" />
              </span>
            </div>
            <div className="text-2xl font-black text-red-700">Sụp đổ 355×</div>
            <p className="text-xs text-slate-600 mt-1">
              Từ <span className="font-semibold text-slate-800">255,264 ops/s</span> xuống <span className="font-semibold text-red-700">589 ops/s</span> do vô hiệu hóa Prefix Bloom Filter.
            </p>
          </div>

          {/* Card 2 */}
          <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-200 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold text-amber-900 uppercase tracking-wide">Độ Trễ Đuôi p99</span>
              <span className="p-1.5 rounded-lg bg-amber-100 text-amber-700">
                <Activity className="w-4 h-4" />
              </span>
            </div>
            <div className="text-2xl font-black text-amber-700">Tăng &gt; 2,400×</div>
            <p className="text-xs text-slate-600 mt-1">
              p99 vọt từ <span className="font-semibold text-slate-800">0.091 ms</span> lên <span className="font-semibold text-amber-700">220.57 ms</span> do lệch thứ tự byte Little-Endian.
            </p>
          </div>

          {/* Card 3 */}
          <div className="p-4 rounded-xl bg-blue-50/70 border border-blue-200 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold text-blue-900 uppercase tracking-wide">PostgreSQL I/O Đọc</span>
              <span className="p-1.5 rounded-lg bg-blue-100 text-blue-700">
                <Database className="w-4 h-4" />
              </span>
            </div>
            <div className="text-2xl font-black text-blue-800">Tăng vọt 27.7×</div>
            <p className="text-xs text-slate-600 mt-1">
              Từ <span className="font-semibold text-slate-800">3 blocks</span> lên <span className="font-semibold text-blue-800">83 blocks</span>; CBO ép chuyển từ Index Scan sang Bitmap Scan.
            </p>
          </div>

          {/* Card 4 */}
          <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold text-emerald-900 uppercase tracking-wide">Định Lý Pollaczek</span>
              <span className="p-1.5 rounded-lg bg-emerald-100 text-emerald-700">
                <Cpu className="w-4 h-4" />
              </span>
            </div>
            <div className="text-2xl font-black text-emerald-700">r ≥ 0.95</div>
            <p className="text-xs text-slate-600 mt-1">
              Xác nhận toán học: Độ trễ đuôi bị chi phối áp đảo bởi phương sai thời gian phục vụ <span className="font-semibold font-mono text-emerald-800">σ²</span>.
            </p>
          </div>
        </div>
      </div>
    </header>
  );
};
