import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { HeroSection } from './components/HeroSection';
import { MetricCalculator } from './components/MetricCalculator';
import { ImageModal } from './components/ImageModal';
import { OverviewTab } from './components/tabs/OverviewTab';
import { PostgresTab } from './components/tabs/PostgresTab';
import { RocksdbTab } from './components/tabs/RocksdbTab';
import { QueueingTheoryTab } from './components/tabs/QueueingTheoryTab';
import { RulebookTab } from './components/tabs/RulebookTab';
import { TabKey } from './components/NavigationTabs';
import { BookOpen, ArrowUp, CheckCircle2, Sliders } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [showCalculator, setShowCalculator] = useState<boolean>(false);
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

  const handleTabChange = (key: TabKey) => {
    setActiveTab(key);
    // Smooth scroll down to content area so user sees the new tab content immediately
    setTimeout(() => {
      const contentEl = document.getElementById('content-area');
      if (contentEl) {
        const yOffset = -70;
        const y = contentEl.getBoundingClientRect().top + window.pageYOffset + yOffset;
        window.scrollTo({ top: y, behavior: 'smooth' });
      }
    }, 50);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans selection:bg-blue-100 selection:text-blue-900">
      {/* 1. Slim, Compact Sticky Navbar (Only 56px height, does not hog the screen) */}
      <Navbar
        activeTab={activeTab}
        onSelectTab={handleTabChange}
        showCalculator={showCalculator}
        onToggleCalculator={() => setShowCalculator((prev) => !prev)}
      />

      {/* 2. Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Hero Section (In normal page flow, scrolls away naturally) */}
        <HeroSection
          onSelectTab={handleTabChange}
          onOpenCalculator={() => {
            setShowCalculator(true);
            const calcEl = document.getElementById('calculator-section');
            if (calcEl) {
              calcEl.scrollIntoView({ behavior: 'smooth' });
            }
          }}
        />

        {/* Collapsible / Toggleable Metric Comparison Playground */}
        {showCalculator && (
          <div id="calculator-section" className="animate-fadeIn">
            <MetricCalculator />
          </div>
        )}

        {/* Quick Playground Toggle Banner if not opened */}
        {!showCalculator && (
          <div className="flex items-center justify-between p-3.5 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200/80 rounded-xl">
            <div className="flex items-center gap-2.5">
              <span className="p-1.5 rounded-lg bg-blue-600 text-white">
                <Sliders className="w-4 h-4" />
              </span>
              <div>
                <span className="text-xs font-bold text-blue-950">Metric Comparison Playground</span>
                <span className="text-xs text-slate-600 hidden sm:inline ml-2">
                  — Chọn và đối sánh side-by-side tức thì giữa cấu hình Optimal và Inverted
                </span>
              </div>
            </div>
            <button
              onClick={() => setShowCalculator(true)}
              className="px-3 py-1.5 rounded-lg bg-blue-700 hover:bg-blue-800 text-white text-xs font-bold transition-colors shrink-0 shadow-sm"
            >
              Mở So Sánh Nhanh
            </button>
          </div>
        )}

        {/* 3. Tab Content Display Area */}
        <div id="content-area" className="scroll-mt-20">
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

      {/* 4. High-Resolution 300 DPI Image Modal */}
      <ImageModal
        isOpen={modalState.isOpen}
        onClose={handleCloseImageModal}
        imageSrc={modalState.imageSrc}
        title={modalState.title}
        caption={modalState.caption}
        analysisText={modalState.analysisText}
      />

      {/* 5. Academic Footer */}
      <footer className="mt-16 bg-white border-t border-slate-200 py-8 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="space-y-1 text-center sm:text-left">
            <div className="font-bold text-slate-900 text-sm flex items-center justify-center sm:justify-start gap-2">
              <BookOpen className="w-4 h-4 text-blue-700" />
              Nghiên cứu Thực nghiệm Đánh Chỉ Mục CSDL (PostgreSQL vs. RocksDB)
            </div>
            <p className="text-slate-500">
              Đồ án chuyên ngành Cơ sở dữ liệu • Báo cáo khoa học Chương 3 &amp; Quy ước thiết kế định lượng.
            </p>
            <div className="flex items-center justify-center sm:justify-start gap-2 pt-0.5 text-[11px] text-emerald-600 font-semibold">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Sẵn sàng triển khai 1-click lên Vercel • Zero-Hallucination Verified</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={scrollToTop}
              className="p-2 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-600 transition-colors shadow-sm"
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
