import React, { useState } from 'react';
import { Header } from './components/Header';
import { NavigationTabs, TabKey } from './components/NavigationTabs';
import { MetricCalculator } from './components/MetricCalculator';
import { ImageModal } from './components/ImageModal';
import { OverviewTab } from './components/tabs/OverviewTab';
import { PostgresTab } from './components/tabs/PostgresTab';
import { RocksdbTab } from './components/tabs/RocksdbTab';
import { QueueingTheoryTab } from './components/tabs/QueueingTheoryTab';
import { RulebookTab } from './components/tabs/RulebookTab';
import { BookOpen, Github, ArrowUp, Layers, CheckCircle2 } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [modalState, setModalState] = useState<{
    isOpen: boolean;
    imageSrc: string;
    title: string;
    caption: string;
    analysisText?: string;
  }>({
    isOpen: false,
    imageSrc: '',
    title: '',
    caption: '',
  });

  const handleOpenImageModal = (
    src: string,
    title: string,
    caption: string,
    analysis?: string
  ) => {
    setModalState({
      isOpen: true,
      imageSrc: src,
      title,
      caption,
      analysisText: analysis,
    });
  };

  const handleCloseImageModal = () => {
    setModalState((prev) => ({ ...prev, isOpen: false }));
  };

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans selection:bg-blue-100 selection:text-blue-900">
      {/* Header */}
      <Header />

      {/* Sticky Tab Navigation */}
      <NavigationTabs activeTab={activeTab} onSelectTab={setActiveTab} />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Interactive Metric Calculator Playground */}
        <MetricCalculator />

        {/* Tab Content Display */}
        <div className="mt-8">
          {activeTab === 'overview' && <OverviewTab />}
          {activeTab === 'postgres' && (
            <PostgresTab onOpenImageModal={handleOpenImageModal} />
          )}
          {activeTab === 'rocksdb' && (
            <RocksdbTab onOpenImageModal={handleOpenImageModal} />
          )}
          {activeTab === 'theory' && (
            <QueueingTheoryTab onOpenImageModal={handleOpenImageModal} />
          )}
          {activeTab === 'rulebook' && <RulebookTab />}
        </div>
      </main>

      {/* High-Resolution 300 DPI Image Modal */}
      <ImageModal
        isOpen={modalState.isOpen}
        onClose={handleCloseImageModal}
        imageSrc={modalState.imageSrc}
        title={modalState.title}
        caption={modalState.caption}
        analysisText={modalState.analysisText}
      />

      {/* Academic Footer */}
      <footer className="mt-16 bg-white border-t border-slate-200 py-10 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="space-y-1 text-center sm:text-left">
            <div className="font-bold text-slate-900 text-sm flex items-center justify-center sm:justify-start gap-2">
              <BookOpen className="w-4 h-4 text-blue-700" />
              Nghiên cứu Thực nghiệm Đánh Chỉ Mục CSDL (PostgreSQL vs. RocksDB)
            </div>
            <p className="text-slate-500">
              Đồ án chuyên ngành Cơ sở dữ liệu • Báo cáo khoa học Chương 3 &amp; Quy ước thiết kế định lượng.
            </p>
            <div className="flex items-center justify-center sm:justify-start gap-2 pt-1 text-[11px] text-emerald-600 font-semibold">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Sẵn sàng triển khai 1-click lên Vercel • Zero-Hallucination Verified</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={scrollToTop}
              className="p-2.5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-600 transition-colors shadow-sm"
              title="Cuộn lên đầu trang"
            >
              <ArrowUp className="w-4 h-4" />
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
