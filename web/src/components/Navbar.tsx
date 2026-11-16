import React from 'react';
import { Database, LayoutGrid, Binary, Activity, BookOpenCheck, ArrowUp } from 'lucide-react';
import { TabKey } from './NavigationTabs';

interface NavbarProps {
  activeTab: TabKey;
  onSelectTab: (tab: TabKey) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onSelectTab,
}) => {
  const tabs = [
    { key: 'overview' as TabKey, label: '1. Tổng quan', fullLabel: '1. Tổng quan & Thiết lập', icon: LayoutGrid },
    { key: 'postgres' as TabKey, label: '2. PostgreSQL', fullLabel: '2. B-Tree (PostgreSQL)', icon: Database },
    { key: 'rocksdb' as TabKey, label: '3. RocksDB', fullLabel: '3. LSM-Tree (RocksDB)', icon: Binary },
    { key: 'theory' as TabKey, label: '4. Lý thuyết', fullLabel: '4. Lý thuyết & Tail latency', icon: Activity },
    { key: 'rulebook' as TabKey, label: '5. Quy ước', fullLabel: '5. Đối sánh & Quy ước', icon: BookOpenCheck },
  ];

  const handleTabClick = (key: TabKey) => {
    onSelectTab(key);
    // Smooth scroll to content area so user sees the change immediately
    const contentEl = document.getElementById('content-area');
    if (contentEl) {
      const yOffset = -70; // Offset for sticky navbar
      const y = contentEl.getBoundingClientRect().top + window.pageYOffset + yOffset;
      window.scrollTo({ top: y, behavior: 'smooth' });
    }
  };

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14 gap-2">
          {/* Left: Compact Project Logo & Title */}
          <div
            onClick={() => {
              onSelectTab('overview');
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
            className="flex items-center gap-2 cursor-pointer shrink-0"
          >
            <span className="p-1.5 rounded-lg bg-blue-700 text-white shadow-sm">
              <Database className="w-4 h-4" />
            </span>
            <div className="hidden sm:block">
              <div className="text-xs font-black text-slate-900 tracking-tight leading-none">
                DB INDEXING LAB
              </div>
              <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                PostgreSQL vs. RocksDB
              </div>
            </div>
          </div>

          {/* Center: The 5 Navigation Tabs (No overflow-x, clean flex alignment) */}
          <nav className="flex items-center gap-1 sm:gap-1.5 justify-center flex-1 max-w-3xl">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  onClick={() => handleTabClick(tab.key)}
                  className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all duration-150 ${isActive
                      ? 'bg-blue-700 text-white shadow-sm ring-1 ring-blue-700 font-bold'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                    }`}
                  title={tab.fullLabel}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span className="hidden lg:inline">{tab.fullLabel}</span>
                  <span className="lg:hidden">{tab.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Right: Quick Scroll to Top */}
          <div className="flex items-center gap-1.5 shrink-0">
            <button
              onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
              title="Cuộn lên đầu trang"
            >
              <ArrowUp className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
