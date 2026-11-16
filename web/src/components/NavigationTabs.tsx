import React from 'react';
import { LayoutGrid, Database, Binary, Activity, BookOpenCheck } from 'lucide-react';

export type TabKey = 'overview' | 'postgres' | 'rocksdb' | 'theory' | 'rulebook';

interface NavigationTabsProps {
  activeTab: TabKey;
  onSelectTab: (tab: TabKey) => void;
}

export const NavigationTabs: React.FC<NavigationTabsProps> = ({ activeTab, onSelectTab }) => {
  const tabs = [
    {
      key: 'overview' as TabKey,
      label: '1. Tổng quan & Thiết lập',
      sublabel: 'Hardware, Docker, Schemas',
      icon: LayoutGrid,
    },
    {
      key: 'postgres' as TabKey,
      label: '2. B-Tree (PostgreSQL)',
      sublabel: 'CBO, Lossy Bitmap, 30 Runs',
      icon: Database,
    },
    {
      key: 'rocksdb' as TabKey,
      label: '3. LSM-Tree (RocksDB)',
      sublabel: 'Endianness, Bloom Filter, 30 Runs',
      icon: Binary,
    },
    {
      key: 'theory' as TabKey,
      label: '4. Lý thuyết & Tail latency',
      sublabel: 'Pollaczek-Khinchine, CDF, Spikes',
      icon: Activity,
    },
    {
      key: 'rulebook' as TabKey,
      label: '5. Đối sánh & Quy ước',
      sublabel: 'AI Advisor Slam, 8 Rules',
      icon: BookOpenCheck,
    },
  ];

  return (
    <div className="bg-slate-100 border-b border-slate-200 sticky top-[138px] lg:top-[124px] z-30 shadow-sm backdrop-blur-md bg-slate-100/95">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <nav className="flex space-x-1 sm:space-x-2 overflow-x-auto py-2.5 no-scrollbar" aria-label="Tabs">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => onSelectTab(tab.key)}
                className={`flex items-center gap-2.5 px-4 py-2.5 rounded-xl font-medium text-xs sm:text-sm whitespace-nowrap transition-all duration-200 ${isActive
                    ? 'bg-white text-blue-900 shadow-sm border border-slate-200/80 font-bold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
                  }`}
              >
                <Icon
                  className={`w-4 h-4 ${isActive ? 'text-blue-700' : 'text-slate-400'
                    }`}
                />
                <div className="text-left">
                  <div>{tab.label}</div>
                  <div className={`text-[10px] hidden sm:block ${isActive ? 'text-blue-600 font-normal' : 'text-slate-400 font-normal'}`}>
                    {tab.sublabel}
                  </div>
                </div>
              </button>
            );
          })}
        </nav>
      </div>
    </div>
  );
};

