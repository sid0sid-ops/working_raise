import type React from 'react';
import { FastExpertToggle } from './FastExpertToggle';

export interface AddSourceButtonProps {
  isOpen: boolean;
  onToggle: () => void;
  onClose: () => void;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  onFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onOpenLibraryPicker: () => void;
  parseMode: 'fast' | 'expert';
  onSelectMode: (mode: 'fast' | 'expert') => void;
  conversationLength?: number;
  className?: string;
}

export const AddSourceButton: React.FC<AddSourceButtonProps> = ({
  isOpen,
  onToggle,
  onClose,
  fileInputRef,
  onFileUpload,
  onOpenLibraryPicker,
  parseMode,
  onSelectMode,
  conversationLength = 0,
  className = '',
}) => {
  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.txt,.docx,.md,.csv"
        onChange={onFileUpload}
        className="hidden"
      />
      <div
        className={`relative shrink-0 select-none z-30 ${className}`}
        data-add-source-container="input"
      >
        <button
          type="button"
          onMouseDown={(e) => e.preventDefault()}
          onClick={onToggle}
          title="Add context, sources, or switch mode (Browse PC, Library, Mode)"
          aria-label="Add context or source"
          aria-expanded={isOpen}
          className={`${
            conversationLength === 0 ? 'w-7.5 h-7.5 sm:w-8 sm:h-8' : 'w-7 h-7 sm:w-7 sm:h-7'
          } rounded-full sm:rounded-lg flex items-center justify-center transition-all active:scale-95 cursor-pointer shrink-0 select-none outline-none focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50 ${
            isOpen
              ? 'bg-indigo-600 hover:bg-indigo-700 text-white border border-indigo-600 dark:bg-indigo-600 dark:hover:bg-indigo-700 dark:text-white dark:border-indigo-600 shadow-md ring-2 ring-indigo-500/30'
              : 'bg-slate-100 hover:bg-slate-200 text-slate-700 hover:text-slate-900 border border-slate-200/90 dark:bg-white/10 dark:hover:bg-white/15 dark:text-slate-300 dark:hover:text-white dark:border-white/10 shadow-xs hover:border-indigo-400/50 dark:hover:border-indigo-400/50'
          }`}
        >
          {/* Mobile (< sm): WhatsApp pin / paperclip icon */}
          <svg
            className={`sm:hidden w-4 h-4 transition-transform duration-200 ${
              isOpen ? 'rotate-45 text-white' : 'rotate-0'
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2.1"
              d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
            />
          </svg>

          {/* Desktop (>= sm): Plus (+) icon */}
          <svg
            className={`hidden sm:block w-3.5 h-3.5 transition-transform duration-200 ${
              isOpen ? 'rotate-45 text-white' : 'rotate-0'
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              d="M12 4v16m8-8H4"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2.2"
            />
          </svg>
        </button>

        {isOpen && (
          <>
            {/* Mobile WhatsApp-style backdrop overlay */}
            <div
              className="fixed inset-0 bg-black/45 backdrop-blur-xs z-[65] sm:hidden animate-in fade-in duration-200"
              onClick={onClose}
              aria-hidden="true"
            />

            {/* WhatsApp-Style Action Sheet on Mobile, anchored upwards above the prompt box on Desktop */}
            <div
              className="fixed sm:absolute bottom-0 sm:bottom-full sm:top-auto left-0 right-0 sm:right-auto sm:left-0 sm:mb-2.5 sm:mt-0 w-full sm:w-72 bg-white dark:bg-[#1e1f20] border-t sm:border border-slate-200/90 dark:border-white/10 rounded-t-3xl sm:rounded-2xl shadow-2xl z-[70] p-4 sm:p-2 animate-in slide-in-from-bottom-8 sm:slide-in-from-bottom-2 fade-in duration-200 select-none max-h-[85vh] overflow-y-auto pb-[max(1rem,env(safe-area-inset-bottom))] sm:pb-2"
              role="menu"
            >
              {/* Mobile pull / drag handle indicator */}
              <div className="w-10 h-1 rounded-full bg-slate-300 dark:bg-white/20 mx-auto mb-3.5 sm:hidden" />

              {/* Fast / Expert Mode Selector inside Pin Sheet on Mobile */}
              <FastExpertToggle
                parseMode={parseMode}
                onSelectMode={onSelectMode}
                variant="mobile"
              />

              {/* Add Context & Sources Section */}
              <div className="space-y-1 sm:space-y-0.5">
                <div className="px-1 py-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 sm:hidden">
                  Add Context & Sources
                </div>
                <button
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => {
                    onClose();
                    fileInputRef.current?.click();
                  }}
                  className="w-full text-left px-3.5 py-3 sm:px-3 sm:py-2 rounded-2xl sm:rounded-xl hover:bg-slate-100 dark:hover:bg-white/10 text-slate-800 dark:text-slate-200 text-xs font-medium flex items-center gap-3.5 sm:gap-2.5 transition-colors cursor-pointer group bg-slate-50/70 dark:bg-white/[0.03] sm:bg-transparent"
                >
                  <div className="w-10 h-10 sm:w-7 sm:h-7 rounded-xl sm:rounded-lg bg-indigo-500 text-white sm:bg-slate-100 sm:text-slate-600 sm:dark:bg-white/10 sm:dark:text-slate-300 flex items-center justify-center shrink-0 shadow-xs group-hover:bg-indigo-600 sm:group-hover:bg-indigo-50 sm:group-hover:text-indigo-600 transition-colors">
                    <svg
                      className="w-5 h-5 sm:w-4 sm:h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
                      />
                    </svg>
                  </div>
                  <div className="min-w-0">
                    <div className="font-semibold text-slate-900 dark:text-slate-100 text-[13px] sm:text-xs">
                      Browse from PC
                    </div>
                    <div className="text-[11px] sm:text-[10px] text-slate-500 dark:text-slate-400 truncate">
                      Upload fresh PDF/DOCX to parse
                    </div>
                  </div>
                </button>

                <button
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => {
                    onClose();
                    onOpenLibraryPicker();
                  }}
                  className="w-full text-left px-3.5 py-3 sm:px-3 sm:py-2 rounded-2xl sm:rounded-xl hover:bg-slate-100 dark:hover:bg-white/10 text-slate-800 dark:text-slate-200 text-xs font-medium flex items-center gap-3.5 sm:gap-2.5 transition-colors cursor-pointer group bg-slate-50/70 dark:bg-white/[0.03] sm:bg-transparent mt-1 sm:mt-0.5"
                >
                  <div className="w-10 h-10 sm:w-7 sm:h-7 rounded-xl sm:rounded-lg bg-emerald-500 text-white sm:bg-indigo-50 sm:text-indigo-600 sm:dark:bg-indigo-500/15 sm:dark:text-[#a8c7fa] flex items-center justify-center shrink-0 shadow-xs group-hover:bg-emerald-600 sm:group-hover:bg-indigo-100 transition-colors">
                    <svg
                      className="w-5 h-5 sm:w-4 sm:h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                      />
                    </svg>
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5 font-semibold text-emerald-600 dark:text-emerald-400 sm:text-indigo-600 sm:dark:text-[#a8c7fa] text-[13px] sm:text-xs">
                      <span>Attach from Library</span>
                      <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 font-mono">
                        Instant
                      </span>
                    </div>
                    <div className="text-[11px] sm:text-[10px] text-slate-500 dark:text-slate-400 truncate">
                      Pre-indexed GraphRAG docs
                    </div>
                  </div>
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
};
