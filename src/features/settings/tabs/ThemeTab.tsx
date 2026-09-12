import React from 'react';

export interface ThemeTabProps {
  theme: 'light' | 'dark' | 'system';
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  onOpenTuner: () => void;
}

export const ThemeTab: React.FC<ThemeTabProps> = ({
  theme,
  setTheme,
  onOpenTuner,
}) => {
  return (
    <div className="space-y-6 animate-in fade-in duration-200" data-testid="settings-theme-tab">
      <div>
        <h3 className="text-base font-semibold text-slate-900 dark:text-white">Theme</h3>
        <p className="text-xs text-slate-500 dark:text-[#a8a8a8] mt-1">
          Select how Raise RAG appears on your device. Choose Dark, Light, or synchronize with your operating system.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
        {/* Dark Card */}
        <button
          type="button"
          onClick={() => setTheme('dark')}
          className={`group flex flex-col p-3 sm:p-4 rounded-xl sm:rounded-2xl border text-left transition-all cursor-pointer ${
            theme === 'dark'
              ? 'border-indigo-600 dark:border-[#a8c7fa] bg-indigo-50/40 dark:bg-[#282a2c] ring-2 ring-indigo-500/20'
              : 'border-slate-200 dark:border-[#37393b] hover:border-slate-300 dark:hover:border-slate-600 bg-slate-50/60 dark:bg-white/[0.02]'
          }`}
        >
          <div className="w-full h-20 rounded-xl bg-[#0e1017] border border-slate-800 p-2.5 hidden sm:flex flex-col justify-between mb-3 shadow-inner">
            <div className="flex items-center justify-between">
              <div className="w-10 h-2 bg-slate-700 rounded" />
              <div className="w-2.5 h-2.5 rounded-full bg-indigo-400" />
            </div>
            <div className="space-y-1">
              <div className="w-16 h-2 bg-slate-800 rounded" />
              <div className="w-24 h-2 bg-slate-800 rounded" />
            </div>
          </div>
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-indigo-500 dark:text-indigo-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              </svg>
              <span className="text-sm font-semibold text-slate-900 dark:text-white">Dark</span>
            </div>
            {theme === 'dark' && (
              <div className="w-4 h-4 rounded-full bg-indigo-600 dark:bg-[#a8c7fa] text-white dark:text-slate-900 flex items-center justify-center">
                <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
            )}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-[#a8a8a8] mt-1">Deep palette optimal for low light</p>
        </button>

        {/* Light Card */}
        <button
          type="button"
          onClick={() => setTheme('light')}
          className={`group flex flex-col p-3 sm:p-4 rounded-xl sm:rounded-2xl border text-left transition-all cursor-pointer ${
            theme === 'light'
              ? 'border-indigo-600 dark:border-[#a8c7fa] bg-indigo-50/40 dark:bg-[#282a2c] ring-2 ring-indigo-500/20'
              : 'border-slate-200 dark:border-[#37393b] hover:border-slate-300 dark:hover:border-slate-600 bg-slate-50/60 dark:bg-white/[0.02]'
          }`}
        >
          <div className="w-full h-20 rounded-xl bg-white border border-slate-200 p-2.5 hidden sm:flex flex-col justify-between mb-3 shadow-inner">
            <div className="flex items-center justify-between">
              <div className="w-10 h-2 bg-slate-200 rounded" />
              <div className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
            </div>
            <div className="space-y-1">
              <div className="w-16 h-2 bg-slate-100 rounded" />
              <div className="w-24 h-2 bg-slate-100 rounded" />
            </div>
          </div>
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="5" />
                <line x1="12" y1="1" x2="12" y2="3" />
                <line x1="12" y1="12" x2="12" y2="23" />
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                <line x1="1" y1="12" x2="3" y2="12" />
                <line x1="21" y1="12" x2="23" y2="12" />
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
              </svg>
              <span className="text-sm font-semibold text-slate-900 dark:text-white">Light</span>
            </div>
            {theme === 'light' && (
              <div className="w-4 h-4 rounded-full bg-indigo-600 dark:bg-[#a8c7fa] text-white dark:text-slate-900 flex items-center justify-center">
                <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
            )}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-[#a8a8a8] mt-1">Crisp high-contrast daylight theme</p>
        </button>

        {/* System Card */}
        <button
          type="button"
          onClick={() => setTheme('system')}
          className={`group flex flex-col p-3 sm:p-4 rounded-xl sm:rounded-2xl border text-left transition-all cursor-pointer ${
            theme === 'system'
              ? 'border-indigo-600 dark:border-[#a8c7fa] bg-indigo-50/40 dark:bg-[#282a2c] ring-2 ring-indigo-500/20'
              : 'border-slate-200 dark:border-[#37393b] hover:border-slate-300 dark:hover:border-slate-600 bg-slate-50/60 dark:bg-white/[0.02]'
          }`}
        >
          <div className="w-full h-20 rounded-xl bg-gradient-to-r from-white to-[#0e1017] border border-slate-300 dark:border-slate-700 p-2.5 hidden sm:flex flex-col justify-between mb-3 shadow-inner">
            <div className="flex items-center justify-between">
              <div className="w-10 h-2 bg-slate-300 dark:bg-slate-600 rounded" />
              <div className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
            </div>
            <div className="space-y-1">
              <div className="w-16 h-2 bg-slate-200 dark:bg-slate-700 rounded" />
              <div className="w-24 h-2 bg-slate-200 dark:bg-slate-700 rounded" />
            </div>
          </div>
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-slate-500 dark:text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <rect height="14" rx="2" width="20" x="2" y="3" />
                <line x1="8" y1="21" x2="16" y2="21" />
                <line x1="12" y1="17" x2="12" y2="21" />
              </svg>
              <span className="text-sm font-semibold text-slate-900 dark:text-white">System</span>
            </div>
            {theme === 'system' && (
              <div className="w-4 h-4 rounded-full bg-indigo-600 dark:bg-[#a8c7fa] text-white dark:text-slate-900 flex items-center justify-center">
                <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
            )}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-[#a8a8a8] mt-1">Matches system device settings</p>
        </button>
      </div>

      {/* Visual Customization: Grid Gradient & Box Light Tuner Button (Hidden on Mobile) */}
      <div className="pt-4 border-t border-slate-200/80 dark:border-white/10 space-y-3 hidden md:block">
        <div>
          <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
            Grid &amp; Light Tuner
          </h4>
          <p className="text-xs text-slate-500 dark:text-[#a8a8a8] mt-0.5">
            Fine-tune the dotted background pattern and the luminous ambient light behind the prompt box with live full-screen preview.
          </p>
        </div>

        <button
          type="button"
          onClick={onOpenTuner}
          className="w-full p-3.5 rounded-xl border border-slate-200/90 dark:border-white/10 bg-slate-50 dark:bg-white/[0.04] hover:bg-slate-100 dark:hover:bg-white/[0.08] hover:border-indigo-400 dark:hover:border-indigo-500/50 flex items-center justify-between text-left transition-all group cursor-pointer shadow-xs active:scale-[0.99]"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-50 dark:bg-indigo-500/15 text-indigo-600 dark:text-[#a8c7fa] flex items-center justify-center group-hover:scale-105 transition-transform shrink-0">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
              </svg>
            </div>
            <div>
              <div className="text-xs sm:text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-1.5">
                <span>Grid &amp; Light Tuner</span>
                <span className="px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-indigo-100 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-300">
                  Live Preview
                </span>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-[#a8a8a8] mt-0.5">
                Move to lower right corner with unblurred background to see changes live
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1 text-xs font-semibold text-indigo-600 dark:text-[#a8c7fa] group-hover:translate-x-0.5 transition-transform shrink-0">
            <span>Open Tuner</span>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </button>
      </div>
    </div>
  );
};
