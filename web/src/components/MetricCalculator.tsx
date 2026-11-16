import React, { useState } from 'react';
import { Sliders, ArrowRight, TrendingUp, TrendingDown, Clock, Activity, Zap } from 'lucide-react';
import { postgresBenchmarkData, rocksdbBenchmarkData } from '../data/benchmarkData';

export const MetricCalculator: React.FC = () => {
  const [engine, setEngine] = useState<'postgres' | 'rocksdb'>('postgres');
  const [workload, setWorkload] = useState<string>('Workload_C');
  const [threads, setThreads] = useState<number>(32);

  // Retrieve optimal and inverted rows
  const dataset = engine === 'postgres' ? postgresBenchmarkData : rocksdbBenchmarkData;
  const optVariantName = engine === 'postgres' ? 'I_OPT' : 'k_opt';
  const invVariantName = engine === 'postgres' ? 'I_INV_LOW_SEL' : 'k_inv';

  const optRow = dataset.find(
    (r) => r.workload === workload && r.variant === optVariantName && r.threads === threads
  );
  const invRow = dataset.find(
    (r) => r.workload === workload && r.variant === invVariantName && r.threads === threads
  );

  const tputRatio = optRow && invRow && invRow.total_throughput_ops > 0
    ? (optRow.total_throughput_ops / invRow.total_throughput_ops).toFixed(1)
    : '0';

  const p99Surge = optRow && invRow && optRow.p99_ms > 0
    ? (invRow.p99_ms / optRow.p99_ms).toFixed(1)
    : '0';

  const varSurge = optRow && invRow && optRow.variance_ms2 > 0
    ? (invRow.variance_ms2 / optRow.variance_ms2).toFixed(1)
    : 'N/A';

  return (
    <section id="calculator" className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-blue-700">
            <Sliders className="w-4 h-4" />
            Công cụ Tương tác Thử nghiệm
          </div>
          <h2 className="text-xl font-bold text-slate-900 mt-1">
            Metric Comparison Playground (So sánh Trực tiếp Cấu hình)
          </h2>
          <p className="text-xs text-slate-500">
            Chọn hệ thống lưu trữ, phân loại tải và bậc đồng thời để quan sát tỷ lệ sụp đổ hiệu năng tức thời.
          </p>
        </div>

        {/* Engine Switcher */}
        <div className="flex p-1 bg-slate-100 rounded-xl border border-slate-200">
          <button
            onClick={() => setEngine('postgres')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              engine === 'postgres'
                ? 'bg-blue-700 text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            PostgreSQL 17 (B-Tree)
          </button>
          <button
            onClick={() => setEngine('rocksdb')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              engine === 'rocksdb'
                ? 'bg-blue-700 text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            RocksDB 9.10 (LSM-Tree)
          </button>
        </div>
      </div>

      {/* Control Filters */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 my-5 p-4 bg-slate-50 rounded-xl border border-slate-200/70">
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Loại Phụ Tải YCSB (Workload):
          </label>
          <div className="grid grid-cols-3 gap-2">
            {[
              { id: 'Workload_C', label: 'Workload C', desc: '100% Read' },
              { id: 'Workload_B', label: 'Workload B', desc: '95%R / 5%W' },
              { id: 'Workload_A', label: 'Workload A', desc: '50%R / 50%W' },
            ].map((w) => (
              <button
                key={w.id}
                onClick={() => setWorkload(w.id)}
                className={`p-2 rounded-lg text-left border transition-all ${
                  workload === w.id
                    ? 'bg-white border-blue-500 ring-2 ring-blue-500/10 shadow-sm'
                    : 'bg-white/60 border-slate-200 hover:bg-white text-slate-600'
                }`}
              >
                <div className={`text-xs font-bold ${workload === w.id ? 'text-blue-900' : 'text-slate-800'}`}>
                  {w.label}
                </div>
                <div className="text-[10px] text-slate-400">{w.desc}</div>
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Mức Độ Đồng Thời (Concurrency Threads):
          </label>
          <div className="flex gap-2">
            {[1, 4, 8, 16, 32].map((t) => (
              <button
                key={t}
                onClick={() => setThreads(t)}
                className={`flex-1 py-2 px-3 rounded-lg text-xs font-bold border transition-all ${
                  threads === t
                    ? 'bg-blue-700 border-blue-700 text-white shadow-sm'
                    : 'bg-white border-slate-200 hover:bg-slate-100 text-slate-700'
                }`}
              >
                {t} Th
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Comparison Results */}
      {optRow && invRow ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Optimal Card */}
            <div className="p-4 rounded-xl border border-emerald-200 bg-emerald-50/50">
              <div className="flex items-center justify-between pb-3 border-b border-emerald-200">
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-800">
                    Cấu hình Tối ưu
                  </span>
                  <div className="text-base font-extrabold text-emerald-950 font-mono">
                    {engine === 'postgres' ? 'I_opt (tenant, status, time)' : 'K_opt [tenant:4B][status:1B]...'}
                  </div>
                </div>
                <span className="px-2.5 py-1 text-xs font-bold rounded-md bg-emerald-600 text-white">
                  OPTIMAL
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3">
                <div>
                  <div className="text-[11px] text-slate-500">Thông lượng</div>
                  <div className="text-base font-bold text-slate-900">
                    {optRow.total_throughput_ops.toLocaleString()} <span className="text-[10px] text-slate-400 font-normal">ops/s</span>
                  </div>
                </div>
                <div>
                  <div className="text-[11px] text-slate-500">Độ trễ p50</div>
                  <div className="text-base font-bold text-slate-900">
                    {optRow.p50_ms} <span className="text-[10px] text-slate-400 font-normal">ms</span>
                  </div>
                </div>
                <div>
                  <div className="text-[11px] text-slate-500">Độ trễ p99</div>
                  <div className="text-base font-bold text-emerald-700">
                    {optRow.p99_ms} <span className="text-[10px] text-slate-400 font-normal">ms</span>
                  </div>
                </div>
                <div>
                  <div className="text-[11px] text-slate-500">Phương sai σ²</div>
                  <div className="text-base font-bold text-slate-800 font-mono">
                    {optRow.variance_ms2}
                  </div>
                </div>
              </div>
            </div>

            {/* Inverted Card */}
            <div className="p-4 rounded-xl border border-red-200 bg-red-50/50">
              <div className="flex items-center justify-between pb-3 border-b border-red-200">
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-red-800">
                    Cấu hình Nghịch đảo
                  </span>
                  <div className="text-base font-extrabold text-red-950 font-mono">
                    {engine === 'postgres' ? 'I_inv (status, time, tenant)' : 'K_inv [status:1B][time:8B]...'}
                  </div>
                </div>
                <span className="px-2.5 py-1 text-xs font-bold rounded-md bg-red-600 text-white">
                  VIOLATED
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3">
                <div>
                  <div className="text-[11px] text-slate-500">Thông lượng</div>
                  <div className="text-base font-bold text-red-700">
                    {invRow.total_throughput_ops.toLocaleString()} <span className="text-[10px] text-slate-400 font-normal">ops/s</span>
                  </div>
                </div>
                <div>
                  <div className="text-[11px] text-slate-500">Độ trễ p50</div>
                  <div className="text-base font-bold text-slate-900">
                    {invRow.p50_ms} <span className="text-[10px] text-slate-400 font-normal">ms</span>
                  </div>
                </div>
                <div>
                  <div className="text-[11px] text-slate-500">Độ trễ p99</div>
                  <div className="text-base font-bold text-red-700">
                    {invRow.p99_ms} <span className="text-[10px] text-slate-400 font-normal">ms</span>
                  </div>
                </div>
                <div>
                  <div className="text-[11px] text-slate-500">Phương sai σ²</div>
                  <div className="text-base font-bold text-red-800 font-mono">
                    {invRow.variance_ms2}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Divergence Summary Bar */}
          <div className="p-4 bg-slate-900 text-white rounded-xl flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-600">
                <Zap className="w-5 h-5 text-yellow-300" />
              </div>
              <div>
                <div className="text-xs text-slate-400">Kết quả Đánh giá Định lượng</div>
                <div className="text-sm font-bold text-slate-100">
                  {engine === 'postgres' ? 'PostgreSQL 17 B-Tree CBO' : 'RocksDB 9.10 LSM-Tree Key-Value'}
                  {' '}({threads} luồng, {workload.replace('_', ' ')})
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-6">
              <div className="flex items-center gap-2">
                <TrendingDown className="w-5 h-5 text-red-400" />
                <div>
                  <div className="text-[10px] text-slate-400 uppercase font-bold">Thông lượng sụt giảm</div>
                  <div className="text-base font-black text-red-400">{tputRatio}×</div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-amber-400" />
                <div>
                  <div className="text-[10px] text-slate-400 uppercase font-bold">Độ trễ p99 bùng nổ</div>
                  <div className="text-base font-black text-amber-400">{p99Surge}×</div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-purple-400" />
                <div>
                  <div className="text-[10px] text-slate-400 uppercase font-bold">Phương sai σ² tăng</div>
                  <div className="text-base font-black text-purple-400">{varSurge}×</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center py-6 text-sm text-slate-400">
          Đang nạp dữ liệu kịch bản đo kiểm...
        </div>
      )}
    </section>
  );
};
