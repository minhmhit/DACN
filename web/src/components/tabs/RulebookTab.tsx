import React, { useState } from 'react';
import { BookOpenCheck, ShieldAlert, Award, ChevronDown, ChevronUp, Copy, Check, CheckSquare, Sparkles, Terminal } from 'lucide-react';
import { comparisonDimensions, rulebookItems, productionChecklist } from '../../data/benchmarkData';

export const RulebookTab: React.FC = () => {
  const [openRuleId, setOpenRuleId] = useState<number | null>(1);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const toggleRule = (id: number) => {
    setOpenRuleId(openRuleId === id ? null : id);
  };

  const copyCode = (id: number, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="space-y-8 animate-fadeIn" id="rulebook">
      {/* 3.6.1 Đối Sánh Quốc Tế (Slamming Matrix) */}
      <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center gap-2.5 text-xs font-bold uppercase tracking-wider text-blue-700 mb-2">
          <Award className="w-4 h-4" />
          Mục 3.6.1 Đồ Án
        </div>
        <h2 className="text-xl font-bold text-slate-900">
          Đối Sánh Quốc Tế: Khoảng Trống Vi Kiến Trúc của Các Hệ Thống AI / DRL Index Advisor
        </h2>
        <p className="text-sm text-slate-600 mt-1 leading-relaxed">
          Nghiên cứu chỉ ra ranh giới đứt gãy sâu sắc giữa mô hình lý thuyết của các công cụ khuyến nghị chỉ mục tự động truyền thống 
          (<span className="font-semibold text-slate-800">AutoAdmin 1997, DB2 Advisor</span>) cũng như các thuật toán Học tăng cường sâu hiện đại 
          (<span className="font-semibold text-slate-800">SWIRL, AutoIndexer</span>) so với các ràng buộc vật lý trong môi trường triển khai thực tế.
        </p>

        {/* The Two Critical Blind Spots */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-5">
          <div className="p-4 rounded-xl border border-amber-200 bg-amber-50/50 space-y-1.5">
            <div className="flex items-center gap-2 font-bold text-xs text-amber-900 uppercase tracking-wide">
              <ShieldAlert className="w-4 h-4 text-amber-600" />
              Điểm Mù 1: Bất Lực Trước Giới Hạn Bộ Nhớ work_mem Động
            </div>
            <p className="text-xs text-slate-700 leading-relaxed">
              Các mô hình AI/DRL chỉ đánh giá chi phí dựa trên CBO tĩnh. Dưới tải đồng thời cao cạn kiệt <code className="text-amber-900 font-bold">work_mem</code>, 
              kế hoạch Bitmap Scan âm thầm suy thoái thành <span className="font-semibold text-slate-900">Lossy Bitmap Heap Scan</span> (quét lại 340k dòng). 
              Các công cụ AI hoàn toàn mù tịt vì trong mô hình tĩnh của chúng, Bitmap Scan vẫn được gán chi phí thấp hơn Seq Scan.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-red-200 bg-red-50/50 space-y-1.5">
            <div className="flex items-center gap-2 font-bold text-xs text-red-900 uppercase tracking-wide">
              <ShieldAlert className="w-4 h-4 text-red-600" />
              Điểm Mù 2: Mù Tịt Về Vi Kiến Trúc Nhị Phân &amp; Bloom Filter
            </div>
            <p className="text-xs text-slate-700 leading-relaxed">
              Các công cụ AI chỉ xử lý ở tầng trừu tượng SQL/Quan hệ, hoàn toàn không có khái niệm về quy cách đóng gói nhị phân (Endianness), 
              thứ tự so sánh từ điển cấp byte bằng <code className="text-red-900 font-bold">memcmp()</code>, hay điều kiện căn chỉnh 4-byte tiếp đầu ngữ 
              của <span className="font-semibold text-slate-900">Prefix Bloom Filter</span>, khiến RocksDB sụp đổ 355 lần.
            </p>
          </div>
        </div>

        {/* Table 3.4: 5-Dimension International Comparison Matrix */}
        <div className="mt-6">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3 flex items-center gap-2">
            <Award className="w-4 h-4 text-blue-600" />
            Bảng 3.4: Ma Trận Đối Sánh Vi Kiến Trúc Giữa Đề Tài &amp; Các Công Trình Quốc Tế
          </h3>
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-100 text-slate-700 border-b border-slate-200 font-bold">
                  <th className="py-3 px-4 w-1/5">Tiêu chí vi kiến trúc</th>
                  <th className="py-3 px-4 w-1/4 text-slate-600">AutoAdmin / DB2 Advisor (Truyền thống)</th>
                  <th className="py-3 px-4 w-1/4 text-slate-600">SWIRL / AutoIndexer (AI/DRL Hiện đại)</th>
                  <th className="py-3 px-4 w-3/10 bg-blue-50 text-blue-900">Đề tài nghiên cứu (Physical Rulebook)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-600 font-sans">
                {comparisonDimensions.map((row, idx) => (
                  <tr key={idx} className={idx % 2 === 1 ? 'bg-slate-50/40' : 'bg-white'}>
                    <td className="py-2.5 px-4 font-bold text-slate-900">{row.dimension}</td>
                    <td className="py-2.5 px-4 text-slate-500">{row.traditional}</td>
                    <td className="py-2.5 px-4 text-slate-500">{row.aiDrl}</td>
                    <td className="py-2.5 px-4 font-bold text-blue-900 bg-blue-50/30">{row.ourRulebook}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* 3.6.2 Tập Luật Thiết Kế Định Lượng (Quantitative Rulebook) */}
      <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center gap-2.5 text-xs font-bold uppercase tracking-wider text-blue-700 mb-2">
          <BookOpenCheck className="w-4 h-4" />
          Mục 3.6.2 Đồ Án
        </div>
        <h2 className="text-xl font-bold text-slate-900">
          Tập Luật Thiết Kế Định Lượng (Quantitative Decision Rulebook)
        </h2>
        <p className="text-sm text-slate-600 mt-1 leading-relaxed">
          Đúc kết từ 60 kịch bản thực nghiệm độc lập và phân tích toán học lý thuyết xếp hàng, đóng vai trò như một 
          <span className="font-semibold text-slate-800"> "hàng rào vật lý cứng"</span> bảo vệ các hệ sinh thái cơ sở dữ liệu phân tán quy mô lớn.
        </p>

        {/* 8 Rules Accordion */}
        <div className="mt-6 space-y-3">
          {rulebookItems.map((rule) => {
            const isOpen = openRuleId === rule.id;
            return (
              <div
                key={rule.id}
                className={`rounded-xl border transition-all ${
                  isOpen
                    ? 'border-blue-300 ring-2 ring-blue-500/10 bg-white shadow-sm'
                    : 'border-slate-200 bg-slate-50/50 hover:bg-white'
                }`}
              >
                <button
                  onClick={() => toggleRule(rule.id)}
                  className="w-full flex items-center justify-between p-4 text-left"
                >
                  <div className="flex items-center gap-3">
                    <span className="flex items-center justify-center w-7 h-7 rounded-lg bg-blue-700 text-white font-bold text-xs shrink-0">
                      L{rule.id}
                    </span>
                    <div>
                      <div className="text-sm font-bold text-slate-900">{rule.title}</div>
                      <div className="text-xs text-slate-500 mt-0.5">{rule.target}</div>
                    </div>
                  </div>
                  <span className="p-1 text-slate-400 hover:text-slate-700">
                    {isOpen ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                  </span>
                </button>

                {isOpen && (
                  <div className="px-5 pb-5 pt-1 space-y-4 border-t border-slate-100 text-xs">
                    {/* Statement */}
                    <div>
                      <span className="font-bold text-slate-900 uppercase tracking-wide text-[10px] text-blue-700">
                        Phát Biểu Luật:
                      </span>
                      <p className="text-slate-800 mt-1 leading-relaxed font-sans text-[13px] bg-slate-50 p-3 rounded-lg border border-slate-200">
                        {rule.statement}
                      </p>
                    </div>

                    {/* Empirical Proof */}
                    <div className="p-3 bg-emerald-50/60 rounded-lg border border-emerald-200">
                      <span className="font-bold text-emerald-900 uppercase tracking-wide text-[10px] block mb-1">
                        Căn Cứ Định Lượng Thực Nghiệm (Zero-Hallucination):
                      </span>
                      <p className="text-slate-700 leading-relaxed font-sans text-xs">
                        {rule.empiricalProof}
                      </p>
                    </div>

                    {/* Risk If Violated */}
                    <div className="p-3 bg-red-50/60 rounded-lg border border-red-200">
                      <span className="font-bold text-red-900 uppercase tracking-wide text-[10px] block mb-1">
                        Hậu Quả Nghiêm Trọng Nếu Vi Phạm:
                      </span>
                      <p className="text-slate-700 leading-relaxed font-sans text-xs">
                        {rule.riskIfViolated}
                      </p>
                    </div>

                    {/* Checklist */}
                    <div>
                      <span className="font-bold text-slate-900 uppercase tracking-wide text-[10px] block mb-1.5">
                        Checklist Áp Dụng Sản Xuất:
                      </span>
                      <ul className="space-y-1.5">
                        {rule.checklist.map((item, cIdx) => (
                          <li key={cIdx} className="flex items-start gap-2 text-slate-700">
                            <CheckSquare className="w-3.5 h-3.5 text-blue-600 mt-0.5 shrink-0" />
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Code Snippet */}
                    {rule.codeSnippet && (
                      <div className="mt-3">
                        <div className="flex items-center justify-between px-3 py-1.5 bg-slate-800 text-slate-300 rounded-t-lg font-mono text-[11px]">
                          <span className="flex items-center gap-1.5">
                            <Terminal className="w-3.5 h-3.5 text-blue-400" />
                            {rule.codeSnippet.title}
                          </span>
                          <button
                            onClick={() => copyCode(rule.id, rule.codeSnippet!.code)}
                            className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-white transition-colors"
                          >
                            {copiedId === rule.id ? (
                              <>
                                <Check className="w-3 h-3 text-emerald-400" />
                                <span className="text-emerald-400">Đã sao chép</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-3 h-3" />
                                <span>Copy code</span>
                              </>
                            )}
                          </button>
                        </div>
                        <pre className="p-3 bg-slate-900 text-slate-200 font-mono text-[11px] rounded-b-lg overflow-x-auto leading-relaxed border-t border-slate-700">
                          <code>{rule.codeSnippet.code}</code>
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Production Pre-flight Checklist */}
        <div className="mt-8 pt-6 border-t border-slate-100">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3 flex items-center gap-2">
            <CheckSquare className="w-4 h-4 text-emerald-600" />
            Bảng Checklist Tra Cứu Nhanh Trước Khi Deploy Production
          </h3>
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-100 text-slate-700 border-b border-slate-200 font-bold">
                  <th className="py-2.5 px-3">Hạng mục kiểm tra</th>
                  <th className="py-2.5 px-3">Tiêu chuẩn đạt</th>
                  <th className="py-2.5 px-3 text-red-900">Rủi ro nếu không đạt</th>
                  <th className="py-2.5 px-3 text-blue-900">Hành động khắc phục</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-600 font-sans">
                {productionChecklist.map((item, idx) => (
                  <tr key={idx} className={idx % 2 === 1 ? 'bg-slate-50/40' : 'bg-white'}>
                    <td className="py-2 px-3 font-bold text-slate-900">{item.category}</td>
                    <td className="py-2 px-3 text-emerald-800 font-medium">{item.standard}</td>
                    <td className="py-2 px-3 text-red-700">{item.risk}</td>
                    <td className="py-2 px-3 text-blue-800 font-medium">{item.action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* 3.7 Tóm tắt Chương 3 */}
      <section className="bg-slate-900 text-white rounded-2xl p-6 shadow-sm border border-slate-800 space-y-4">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-blue-400">
          <Sparkles className="w-4 h-4" />
          Mục 3.7 Đồ Án
        </div>
        <h2 className="text-xl font-bold text-slate-100">
          Tóm Tắt Chương 3 &amp; Ba Đúc Kết Cốt Lõi
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
          <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700 space-y-1.5">
            <div className="text-xs font-bold text-blue-400 uppercase">1. B-Tree (PostgreSQL)</div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Vi phạm quy tắc ESR khiến CBO chuyển sang Bitmap Scan; dưới áp lực tải và cạn kiệt <code className="text-blue-300">work_mem</code>, 
              suy thoái thành <strong className="text-white">Lossy Bitmap Heap Scan</strong> quét lại 340k dòng, làm bùng nổ phương sai σ² và kéo p99 sụp đổ.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700 space-y-1.5">
            <div className="text-xs font-bold text-purple-400 uppercase">2. LSM-Tree (RocksDB)</div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Sai lệch mã hóa Endianness và bố cục khóa nhị phân khiến <code className="text-purple-300">memcmp()</code> sai thứ tự, 
              <strong className="text-white">vô hiệu hóa 100% Prefix Bloom Filter</strong>, ép duyệt đĩa đa tầng và làm sụp đổ thông lượng hơn 355 lần.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700 space-y-1.5">
            <div className="text-xs font-bold text-emerald-400 uppercase">3. Đóng Góp Khoa Học</div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Chỉ ra điểm mù chí tử của các hệ thống AI/DRL Index Advisor hiện đại và thiết lập 
              <strong className="text-white"> Tập luật thiết kế định lượng</strong> can thiệp thẳng vào vi kiến trúc vật lý, bảo vệ tuyệt đối ngưỡng SLA (p99).
            </p>
          </div>
        </div>
      </section>
    </div>
  );
};
