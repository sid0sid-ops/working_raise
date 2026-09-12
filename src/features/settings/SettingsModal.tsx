import React, { useRef } from 'react';
import { useModeStore } from '../../stores/modeStore';
import { useSettingsJunction } from './junction/settingsJunction';
import { ThemeTab } from './tabs/ThemeTab';
import { LibraryTab } from './tabs/LibraryTab';
import { DataControlTab } from './tabs/DataControlTab';
import { GatewayTab } from './tabs/GatewayTab';
import { HelpTab } from './tabs/HelpTab';
import { AboutTab } from './tabs/AboutTab';
import { VoiceTab } from './tabs/VoiceTab';
import { GridGradientTuner } from '../../components/ui/GridGradientTuner';
import { ChatSession } from '../../types';

export interface SettingsModalProps {
  // Theme props
  theme: 'light' | 'dark' | 'system';
  setTheme: (theme: 'light' | 'dark' | 'system') => void;

  // Library props
  onSelectLibraryDocument?: (doc: any) => void;
  onDeleteSourceDoc?: (id: string, name: string) => void;

  // Data control props
  sessions: ChatSession[];
  onSessionsChange: (sessions: ChatSession[]) => void;
  onDeleteAllChats: () => void;

  // Voice props
  selectedVoiceName: string;
  setSelectedVoiceName: (name: string) => void;
  availableVoices: SpeechSynthesisVoice[];
  isPlayingSample: boolean;
  onPlaySample: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  theme,
  setTheme,
  onSelectLibraryDocument,
  onDeleteSourceDoc,
  sessions,
  onSessionsChange,
  onDeleteAllChats,
  selectedVoiceName,
  setSelectedVoiceName,
  availableVoices,
  isPlayingSample,
  onPlaySample,
}) => {
  const {
    isOpen,
    activeTab,
    mobileView,
    isTunerMode,
    showOutsideClickTip,
    close,
    setTab,
    setMobileView,
    setTunerMode,
    setShowOutsideClickTip,
  } = useSettingsJunction();

  const { appMode } = useModeStore();
  const outsideClicksCountRef = useRef(0);

  if (!isOpen) return null;

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target !== e.currentTarget) return;
    if (isTunerMode) {
      outsideClicksCountRef.current += 1;
      if (outsideClicksCountRef.current >= 2) {
        close();
        outsideClicksCountRef.current = 0;
      } else {
        setShowOutsideClickTip(true);
        setTimeout(() => setShowOutsideClickTip(false), 2500);
      }
    } else {
      close();
    }
  };

  const handleBackdropDoubleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget && isTunerMode) {
      close();
      outsideClicksCountRef.current = 0;
    }
  };

  return (
    <>
      {/* Gentle notification pill when 1st outside click occurs in Tuner mode */}
      {showOutsideClickTip && isTunerMode && (
        <div className="fixed top-6 left-1/2 -translate-x-1/2 z-[120] pointer-events-none animate-in fade-in zoom-in-95 duration-150 select-none">
          <div className="px-3.5 py-1.5 rounded-full bg-slate-900/95 dark:bg-slate-100/95 text-white dark:text-slate-900 text-xs font-medium shadow-xl backdrop-blur-md flex items-center gap-2 border border-white/10 dark:border-black/10">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse shrink-0" />
            <span>Click outside once more to close</span>
          </div>
        </div>
      )}

      <div
        id="settingsModalBackdrop"
        className={`fixed inset-0 z-[110] flex ${
          isTunerMode
            ? 'items-end justify-end p-[clamp(0.5rem,2vw,1.25rem)] bg-transparent pointer-events-auto'
            : 'items-center justify-center p-[clamp(0.5rem,2vw,1rem)] bg-black/60 backdrop-blur-sm'
        } animate-in fade-in duration-150`}
        onClick={handleBackdropClick}
        onDoubleClick={handleBackdropDoubleClick}
      >
      {isTunerMode ? (
        <div
          id="settingsModalDialog"
          role="dialog"
          aria-modal="true"
          aria-label="Grid and Light Tuner"
          onClick={(e) => e.stopPropagation()}
          className="w-[min(94vw,26rem)] max-h-[85dvh] bg-white/98 dark:bg-[#181b26]/98 text-slate-900 dark:text-slate-100 border border-slate-300 dark:border-white/15 rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-150 select-none backdrop-blur-md"
        >
          <GridGradientTuner
            embedded={true}
            defaultTab="grid"
            onSaveAndClose={() => close()}
            onBackToSettings={() => setTunerMode(false)}
            onClose={() => close()}
          />
        </div>
      ) : (
        <div
          id="settingsModalDialog"
          role="dialog"
          aria-modal="true"
          aria-label="Settings"
          onClick={(e) => e.stopPropagation()}
          className="w-[min(94vw,48rem)] max-w-3xl h-[590px] max-h-[88vh] bg-white dark:bg-[#181b26] text-slate-900 dark:text-slate-100 border border-slate-300 dark:border-white/15 rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-150 select-none"
        >
          {/* Modal Header */}
          <div className="p-[clamp(0.625rem,2vw,1rem)] border-b border-slate-200 dark:border-white/10 flex items-center justify-between bg-slate-50/80 dark:bg-white/[0.02] shrink-0">
            <div className="flex items-center gap-2.5 min-w-0">
              {/* Mobile Back Button: Only shown on mobile when inside a setting detail view */}
              {mobileView === 'detail' && (
                <button
                  type="button"
                  onClick={() => setMobileView('menu')}
                  className="md:hidden p-1.5 -ml-1 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/60 dark:hover:bg-white/10 rounded-xl transition-colors cursor-pointer flex items-center gap-1 text-xs font-semibold shrink-0"
                  aria-label="Back to settings menu"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                  </svg>
                  <span>Back</span>
                </button>
              )}

              <div className="w-8 h-8 rounded-xl bg-indigo-50 dark:bg-indigo-500/15 flex items-center justify-center text-indigo-600 dark:text-[#a8c7fa] shrink-0">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="3" />
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06-.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                </svg>
              </div>

              <div className="min-w-0">
                {mobileView === 'detail' ? (
                  <>
                    <div className="md:hidden">
                      <h2 className="text-sm sm:text-base font-semibold text-slate-900 dark:text-white truncate">
                        {activeTab === 'theme' && 'Theme'}
                        {activeTab === 'library' && 'Library'}
                        {activeTab === 'data-control' && 'Data Controls'}
                        {activeTab === 'gateway' && 'Gateway'}
                        {activeTab === 'voice' && 'Read Aloud Voice'}
                        {activeTab === 'help' && 'Help'}
                        {activeTab === 'about' && 'About'}
                      </h2>
                      <p className="hidden sm:block text-[11px] text-slate-500 dark:text-slate-400 truncate">
                        {activeTab === 'theme' && 'Appearance & visual styles'}
                        {activeTab === 'library' && 'Knowledge documents & datasets'}
                        {activeTab === 'data-control' && 'Privacy, archives & export'}
                        {activeTab === 'gateway' && 'Backend connection & routing'}
                        {activeTab === 'voice' && 'Speech synthesis & voices'}
                        {activeTab === 'help' && 'Shortcuts & documentation'}
                        {activeTab === 'about' && 'Architecture & pipeline modes'}
                      </p>
                    </div>
                    <div className="hidden md:block">
                      <h2 className="text-sm sm:text-base font-semibold text-slate-900 dark:text-white">Settings</h2>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400">Appearance, gateway &amp; system configuration</p>
                    </div>
                  </>
                ) : (
                  <div>
                    <h2 className="text-sm sm:text-base font-semibold text-slate-900 dark:text-white">Settings</h2>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400">Appearance, gateway &amp; system configuration</p>
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={close}
                className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-200/60 dark:hover:bg-white/10 rounded-md transition-colors cursor-pointer"
                title="Close"
                aria-label="Close settings"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Modal Body: Mobile Single-Pane / Desktop Two-Pane Split Layout */}
          <div className="flex flex-col md:flex-row flex-1 min-h-0 overflow-hidden">
            {/* Left Column (Navigation List):
                On Mobile: shown ONLY when mobileView === 'menu'
                On Desktop: ALWAYS shown as sidebar (md:block) */}
            <div
              className={`w-full md:w-52 shrink-0 p-2.5 md:p-2.5 border-b md:border-b-0 md:border-r border-slate-200/80 dark:border-white/10 bg-slate-50/70 dark:bg-white/[0.02] overflow-y-auto space-y-1.5 md:space-y-1 ${
                mobileView === 'menu' ? 'block' : 'hidden md:block'
              }`}
              style={{ scrollbarWidth: 'thin' }}
            >
              {/* Tab 1: Theme */}
              <button
                type="button"
                onClick={() => setTab('theme')}
                className={`w-full flex items-center justify-between p-3 md:px-3.5 md:py-2.5 rounded-xl text-xs sm:text-sm font-medium transition-all cursor-pointer ${
                  activeTab === 'theme'
                    ? 'bg-white dark:bg-[#282a2c] text-indigo-600 dark:text-[#a8c7fa] shadow-xs border border-slate-200/80 dark:border-transparent font-semibold'
                    : 'text-slate-700 dark:text-[#c4c7c5] hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/50 dark:hover:bg-white/5'
                }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-7 h-7 rounded-lg bg-indigo-50 dark:bg-indigo-500/15 flex items-center justify-center text-indigo-600 dark:text-[#a8c7fa] shrink-0">
                    <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="4" />
                      <path strokeLinecap="round" d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
                    </svg>
                  </div>
                  <div className="text-left min-w-0">
                    <div className="font-semibold text-slate-900 dark:text-white text-xs sm:text-sm">Theme</div>
                  </div>
                </div>
                <svg className="w-4 h-4 text-slate-400 md:hidden shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </button>

              {/* Tab: Library */}
              <button
                type="button"
                onClick={() => setTab('library')}
                className={`w-full flex items-center justify-between p-3 md:px-3.5 md:py-2.5 rounded-xl text-xs sm:text-sm font-medium transition-all cursor-pointer ${
                  activeTab === 'library'
                    ? 'bg-white dark:bg-[#282a2c] text-indigo-600 dark:text-[#a8c7fa] shadow-xs border border-slate-200/80 dark:border-transparent font-semibold'
                    : 'text-slate-700 dark:text-[#c4c7c5] hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/50 dark:hover:bg-white/5'
                }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-7 h-7 rounded-lg bg-emerald-50 dark:bg-emerald-500/15 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shrink-0">
                    <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                    </svg>
                  </div>
                  <div className="text-left min-w-0">
                    <div className="font-semibold text-slate-900 dark:text-white text-xs sm:text-sm">Library</div>
                  </div>
                </div>
                <svg className="w-4 h-4 text-slate-400 md:hidden shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </button>

              {/* Tab: Data Controls */}
              <button
                type="button"
                onClick={() => setTab('data-control')}
                className={`w-full flex items-center justify-between p-3 md:px-3.5 md:py-2.5 rounded-xl text-xs sm:text-sm font-medium transition-all cursor-pointer ${
                  activeTab === 'data-control'
                    ? 'bg-white dark:bg-[#282a2c] text-indigo-600 dark:text-[#a8c7fa] shadow-xs border border-slate-200/80 dark:border-transparent font-semibold'
                    : 'text-slate-700 dark:text-[#c4c7c5] hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/50 dark:hover:bg-white/5'
                }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-7 h-7 rounded-lg bg-amber-50 dark:bg-amber-500/15 flex items-center justify-center text-amber-600 dark:text-amber-400 shrink-0">
                    <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                    </svg>
                  </div>
                  <div className="text-left min-w-0">
                    <div className="font-semibold text-slate-900 dark:text-white text-xs sm:text-sm">Data Controls</div>
                  </div>
                </div>
                <svg className="w-4 h-4 text-slate-400 md:hidden shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </button>

              {/* Tab: Gateway */}
              <button
                type="button"
                onClick={() => setTab('gateway')}
                className={`w-full flex items-center justify-between p-3 md:px-3.5 md:py-2.5 rounded-xl text-xs sm:text-sm font-medium transition-all cursor-pointer ${
                  activeTab === 'gateway'
                    ? 'bg-white dark:bg-[#282a2c] text-indigo-600 dark:text-[#a8c7fa] shadow-xs border border-slate-200/80 dark:border-transparent font-semibold'
                    : 'text-slate-700 dark:text-[#c4c7c5] hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/50 dark:hover:bg-white/5'
                }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-7 h-7 rounded-lg bg-sky-50 dark:bg-sky-500/15 flex items-center justify-center text-sky-600 dark:text-sky-400 shrink-0">
                    <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
                    </svg>
                  </div>
                  <div className="text-left min-w-0">
                    <div className="font-semibold text-slate-900 dark:text-white text-xs sm:text-sm">Gateway</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 ${
                      appMode === 'connected'
                        ? 'bg-emerald-500 ring-2 ring-emerald-500/20'
                        : appMode === 'degraded'
                        ? 'bg-amber-500 ring-2 ring-amber-500/20'
                        : appMode === 'mock'
                        ? 'bg-indigo-500 ring-2 ring-indigo-500/20'
                        : 'bg-rose-500 ring-2 ring-rose-500/20'
                    }`}
                  />
                  <svg className="w-4 h-4 text-slate-400 md:hidden shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </button>

              {/* Tab: Read Aloud Voice */}
              <button
                type="button"
                onClick={() => setTab('voice')}
                className={`w-full flex items-center justify-between p-3 md:px-3.5 md:py-2.5 rounded-xl text-xs sm:text-sm font-medium transition-all cursor-pointer ${
                  activeTab === 'voice'
                    ? 'bg-white dark:bg-[#282a2c] text-indigo-600 dark:text-[#a8c7fa] shadow-xs border border-slate-200/80 dark:border-transparent font-semibold'
                    : 'text-slate-700 dark:text-[#c4c7c5] hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/50 dark:hover:bg-white/5'
                }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-7 h-7 rounded-lg bg-purple-50 dark:bg-purple-500/15 flex items-center justify-center text-purple-600 dark:text-purple-400 shrink-0">
                    <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M11 5L6 9H2v6h4l5 4V5z" />
                    </svg>
                  </div>
                  <div className="text-left min-w-0">
                    <div className="font-semibold text-slate-900 dark:text-white text-xs sm:text-sm">Read Aloud Voice</div>
                  </div>
                </div>
                <svg className="w-4 h-4 text-slate-400 md:hidden shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </button>

              {/* Tab: Help */}
              <button
                type="button"
                onClick={() => setTab('help')}
                className={`w-full flex items-center justify-between p-3 md:px-3.5 md:py-2.5 rounded-xl text-xs sm:text-sm font-medium transition-all cursor-pointer ${
                  activeTab === 'help'
                    ? 'bg-white dark:bg-[#282a2c] text-indigo-600 dark:text-[#a8c7fa] shadow-xs border border-slate-200/80 dark:border-transparent font-semibold'
                    : 'text-slate-700 dark:text-[#c4c7c5] hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/50 dark:hover:bg-white/5'
                }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-7 h-7 rounded-lg bg-slate-100 dark:bg-white/10 flex items-center justify-center text-slate-600 dark:text-slate-300 shrink-0">
                    <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="10" />
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3m.08 4h.01" />
                    </svg>
                  </div>
                  <div className="text-left min-w-0">
                    <div className="font-semibold text-slate-900 dark:text-white text-xs sm:text-sm">Help</div>
                  </div>
                </div>
                <svg className="w-4 h-4 text-slate-400 md:hidden shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </button>

              {/* Tab: About */}
              <button
                type="button"
                data-testid="settings-nav-about-btn"
                onClick={() => setTab('about')}
                className={`w-full flex items-center justify-between p-3 md:px-3.5 md:py-2.5 rounded-xl text-xs sm:text-sm font-medium transition-all cursor-pointer ${
                  activeTab === 'about'
                    ? 'bg-white dark:bg-[#282a2c] text-indigo-600 dark:text-[#a8c7fa] shadow-xs border border-slate-200/80 dark:border-transparent font-semibold'
                    : 'text-slate-700 dark:text-[#c4c7c5] hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/50 dark:hover:bg-white/5'
                }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-7 h-7 rounded-lg bg-teal-50 dark:bg-teal-500/15 flex items-center justify-center text-teal-600 dark:text-teal-400 shrink-0">
                    <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                  </div>
                  <div className="text-left min-w-0">
                    <div className="font-semibold text-slate-900 dark:text-white text-xs sm:text-sm">About</div>
                  </div>
                </div>
                <svg className="w-4 h-4 text-slate-400 md:hidden shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>

            {/* Right Column (Tab Content Area):
                On Mobile: shown ONLY when mobileView === 'detail'
                On Desktop: ALWAYS shown (md:block) */}
            <div
              className={`flex-1 p-4 sm:p-6 overflow-y-auto min-h-0 bg-white dark:bg-[#1e1f20] ${
                mobileView === 'detail' ? 'block' : 'hidden md:block'
              }`}
              style={{ scrollbarWidth: 'thin' }}
            >
              {/* TAB 1: THEME */}
              {activeTab === 'theme' && (
                <ThemeTab
                  theme={theme}
                  setTheme={setTheme}
                  onOpenTuner={() => setTunerMode(true)}
                />
              )}

              {/* TAB 2: LIBRARY */}
              {activeTab === 'library' && (
                <LibraryTab
                  onSelectDocument={onSelectLibraryDocument}
                  onDocumentDeleted={onDeleteSourceDoc}
                  onCloseSettings={close}
                />
              )}

              {/* TAB 3: DATA CONTROLS */}
              {activeTab === 'data-control' && (
                <DataControlTab
                  sessions={sessions}
                  onSessionsChange={onSessionsChange}
                  onDeleteAllChats={onDeleteAllChats}
                  onCloseSettings={close}
                />
              )}

              {/* TAB 4: GATEWAY */}
              {activeTab === 'gateway' && (
                <GatewayTab onCloseSettings={close} />
              )}

              {/* TAB 5: VOICE */}
              {activeTab === 'voice' && (
                <VoiceTab
                  selectedVoiceName={selectedVoiceName}
                  setSelectedVoiceName={setSelectedVoiceName}
                  availableVoices={availableVoices}
                  isPlayingSample={isPlayingSample}
                  onPlaySample={onPlaySample}
                />
              )}

              {/* TAB 6: HELP */}
              {activeTab === 'help' && (
                <HelpTab onNavigateToAbout={() => setTab('about')} />
              )}

              {/* TAB 7: ABOUT */}
              {activeTab === 'about' && (
                <AboutTab />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
    </>
  );
};
