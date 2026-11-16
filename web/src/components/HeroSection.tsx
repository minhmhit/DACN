import React from 'react';
import { Database, Cpu, Activity, ShieldAlert, Sparkles, BookOpen, Layers } from 'lucide-react';
import { TabKey } from './NavigationTabs';

interface HeroSectionProps {
  onSelectTab: (tab: TabKey) => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({ onSelectTab }) => {
  const jumpToTab = (tab: TabKey) => {
    onSelectTab(tab);
    const contentEl = document.getElementById('content-area');
    if (contentEl) {
      const yOffset = -70;
      const y = contentEl.getBoundingClientRect().top + window.pageYOffset + yOffset;
      window.scrollTo({ top: y, behavior: 'smooth' });
    }
  };

  const scrollToCalculator = () => {
    const calcEl = document.getElementById('calculator');
    if (calcEl) {
      const yOffset = -70;
      const y = calcEl.getBoundingClientRect().top + window.pageYOffset + yOffset;
      window.scrollTo({ top: y, behavior: 'smooth' });
    }
  };

  return (
    <section className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-sm space-y-6">
      {/* Top Academic Tag */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-4">
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
            ĐỒ ÁN CHUYÊN NGÀNH CƠ SỞ DỮ LIỆU • BÁO CÁO KHOA HỌC CHƯƠNG 3
          </span>
        </div>
        <div className="text-xs font-mono text-slate-500">
          PostgreSQL 17 (B-Tree) vs. RocksDB 9.10 (LSM-Tree)
        </div>
      </div>

      {/* Main Title & Action Buttons */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div className="space-y-2.5 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-800 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-blue-600" />
            Empirical Study &amp; Microarchitectural Decision Rulebook
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight leading-snug">
            Nghiên cứu &amp; Thực nghiệm Ảnh hưởng của Đánh Chỉ mục đến Hiệu năng Truy vấn
          </h1>
          <p className="text-sm text-slate-600 font-sans leading-relaxed">
            Giải mã cơ chế vi kiến trúc dẫn đến sự bùng nổ độ trễ đuôi (<span className="font-semibold text-slate-900">p99 / p99.9</span>)
            và kiểm chứng thực nghiệm bằng <span className="font-semibold text-blue-700">Định lý hàng đợi Pollaczek-Khinchine</span>.
          </p>
        </div>

        {/* Quick Nav Shortcut Buttons */}
        <div className="flex flex-wrap lg:flex-col gap-2 shrink-0">
          <button
            onClick={() => jumpToTab('rulebook')}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-700 hover:bg-blue-800 text-white text-xs font-bold shadow-sm transition-all hover:shadow hover:-translate-y-0.5"
          >
            <BookOpen className="w-4 h-4" />
            Tra cứu 8 Quy ước Thiết kế
          </button>
          <button
            onClick={scrollToCalculator}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold border border-slate-300 transition-colors"
          >
            <Layers className="w-4 h-4 text-slate-600" />
            Đến Playground So sánh
          </button>
        </div>
      </div>

      {/* 4 Highlight Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2 border-t border-slate-100">
        {/* Card 1 */}
        <div
          onClick={() => jumpToTab('rocksdb')}
          className="p-4 rounded-xl bg-red-50/70 border border-red-200 hover:shadow-md hover:bg-red-50 cursor-pointer transition-all"
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-bold text-red-900 uppercase tracking-wide">RocksDB Thông Lượng</span>
            <span className="p-1 rounded bg-red-100 text-red-700">
              <ShieldAlert className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="text-2xl font-black text-red-700">Sụp đổ 355×</div>
          <p className="text-xs text-slate-600 mt-1">
            Từ <span className="font-semibold text-slate-900">255,264 ops/s</span> xuống <span className="font-semibold text-red-700">589 ops/s</span> do vô hiệu hóa Prefix Bloom Filter.
          </p>
        </div>

        {/* Card 2 */}
        <div
          onClick={() => jumpToTab('rocksdb')}
          className="p-4 rounded-xl bg-amber-50/70 border border-amber-200 hover:shadow-md hover:bg-amber-50 cursor-pointer transition-all"
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-bold text-amber-900 uppercase tracking-wide">Độ Trễ Đuôi p99</span>
            <span className="p-1 rounded bg-amber-100 text-amber-700">
              <Activity className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="text-2xl font-black text-amber-700">Tăng &gt; 2,400×</div>
          <p className="text-xs text-slate-600 mt-1">
            p99 vọt từ <span className="font-semibold text-slate-900">0.091 ms</span> lên <span className="font-semibold text-amber-700">220.57 ms</span> do lệch thứ tự byte Little-Endian.
          </p>
        </div>

        {/* Card 3 */}
        <div
          onClick={() => jumpToTab('postgres')}
          className="p-4 rounded-xl bg-blue-50/70 border border-blue-200 hover:shadow-md hover:bg-blue-50 cursor-pointer transition-all"
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-bold text-blue-900 uppercase tracking-wide">PostgreSQL I/O Đọc</span>
            <span className="p-1 rounded bg-blue-100 text-blue-700">
              <Database className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="text-2xl font-black text-blue-800">Tăng vọt 27.7×</div>
          <p className="text-xs text-slate-600 mt-1">
            Từ <span className="font-semibold text-slate-900">3 blocks</span> lên <span className="font-semibold text-blue-800">83 blocks</span>; CBO ép chuyển từ Index Scan sang Bitmap Scan.
          </p>
        </div>

        {/* Card 4 */}
        <div
          onClick={() => jumpToTab('theory')}
          className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 hover:shadow-md hover:bg-emerald-50 cursor-pointer transition-all"
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-bold text-emerald-900 uppercase tracking-wide">Định Lý Pollaczek</span>
            <span className="p-1 rounded bg-emerald-100 text-emerald-700">
              <Cpu className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="text-2xl font-black text-emerald-700">r ≥ 0.95</div>
          <p className="text-xs text-slate-600 mt-1">
            Xác nhận toán học: Độ trễ đuôi bị chi phối áp đảo bởi phương sai thời gian phục vụ <span className="font-semibold font-mono text-emerald-800">σ²</span>.
          </p>
        </div>
      </div>
    </section>
  );
};
