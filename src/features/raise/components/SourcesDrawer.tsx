import type React from 'react';
import { CircularUploadProgress } from '../../../components/ui/CircularUploadProgress';
import { useModeStore } from '../../../stores/modeStore';
import type { SourceDocument } from '../../../types';
import { formatBytes } from '../../../utils/formatters';

export interface SourcesDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  sourceDocs: SourceDocument[];
  activeSourcesCount: number;
  sourceFilter: string;
  setSourceFilter: (filter: string) => void;
  addSourceMenuOpen: 'drawer' | 'input' | null;
  setAddSourceMenuOpen: React.Dispatch<React.SetStateAction<'drawer' | 'input' | null>>;
  onBrowseFileClick: () => void;
  onOpenLibraryPicker: () => void;
  isDocReady: (doc: SourceDocument) => boolean;
  onToggleSourceDoc: (id: string) => void;
  onDeleteSourceDoc: (id: string, name: string) => void;
  onViewPdf?: (filename: string, pageNumber?: number) => void;
}

export const SourcesDrawer: React.FC<SourcesDrawerProps> = ({
  isOpen,
  onClose,
  sourceDocs,
  activeSourcesCount,
  sourceFilter,
  setSourceFilter,
  addSourceMenuOpen,
  setAddSourceMenuOpen,
  onBrowseFileClick,
  onOpenLibraryPicker,
  isDocReady,
  onToggleSourceDoc,
  onDeleteSourceDoc,
  onViewPdf,
}) => {
  const { appMode } = useModeStore();
  const isOnline = appMode === 'connected';

  if (!isOpen) return null;

  const filteredDocs = sourceDocs.filter((d) =>
    d.name.toLowerCase().includes(sourceFilter.toLowerCase())
  );

  return (
    <div
      id="sourcesModalBackdrop"
      className="fixed inset-0 z-[110] flex items-center justify-center p-[clamp(0.5rem,2.5vw,1.25rem)] bg-black/60 backdrop-blur-sm animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        id="sourcesModalDialog"
        role="dialog"
        aria-modal="true"
        aria-label="Source Documents Drawer"
        onClick={(e) => e.stopPropagation()}
        className="w-[min(96vw,44rem)] max-w-2xl h-auto max-h-[min(88dvh,560px)] min-h-0 bg-white dark:bg-[#181b26] text-slate-900 dark:text-slate-100 border border-slate-300/90 dark:border-white/15 rounded-2xl sm:rounded-3xl shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-150 select-none transition-all duration-200"
      >
        {/* Modal Header - Styled to match SettingsModal */}
        <div className="p-[clamp(0.625rem,2vw,1rem)] border-b border-slate-200/90 dark:border-white/10 flex flex-col bg-slate-50/80 dark:bg-white/[0.02] shrink-0">
          {/* Mobile pull / drag handle indicator */}
          <div className="w-10 h-1 rounded-full bg-slate-300 dark:bg-white/20 mx-auto -mt-0.5 mb-2.5 sm:hidden" />

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-indigo-50 dark:bg-indigo-500/15 flex items-center justify-center text-indigo-600 dark:text-[#a8c7fa] shrink-0 shadow-2xs">
                <svg
                  className="w-4 h-4 sm:w-4.5 sm:h-4.5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"
                  />
                </svg>
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h2 className="text-sm sm:text-base font-semibold text-slate-900 dark:text-white truncate">
                    Drawer
                  </h2>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-semibold shrink-0 ${
                      isOnline
                        ? 'bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-500/20 dark:text-indigo-300 dark:border-indigo-400/30'
                        : 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30'
                    }`}
                  >
                    {isOnline ? `${activeSourcesCount} active` : 'Offline'}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                  Source data documents for retrieval augmented generation
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono bg-slate-200/80 dark:bg-white/10 text-slate-500 dark:text-slate-400 rounded-md border border-slate-300 dark:border-white/10">
                Esc
              </kbd>
              <button
                id="closeSourcesBtn"
                type="button"
                onClick={onClose}
                className="p-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-200/60 dark:hover:bg-white/10 rounded-xl transition-colors cursor-pointer shrink-0"
                title="Close (Esc)"
                aria-label="Close drawer popup"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Filter & Actions Bar */}
        <div className="p-2.5 sm:px-4 sm:py-3 border-b border-slate-200/80 dark:border-white/10 bg-slate-50/50 dark:bg-white/[0.01] flex items-center gap-2 sm:gap-2.5 shrink-0">
          <div className="relative flex-1 min-w-0">
            <input
              type="text"
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              placeholder="Filter sources by title..."
              className="w-full bg-white dark:bg-white/[0.05] border border-slate-200/90 dark:border-white/10 rounded-xl pl-8 pr-7 py-1.5 text-xs text-slate-900 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/25 focus:border-indigo-500 transition-all shadow-2xs"
            />
            <svg
              className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500 absolute left-2.5 top-2.5 pointer-events-none"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
              />
            </svg>
            {sourceFilter && (
              <button
                type="button"
                onClick={() => setSourceFilter('')}
                className="absolute right-2 top-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-0.5 rounded cursor-pointer"
                title="Clear filter"
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            )}
          </div>

          <div className="relative shrink-0" data-add-source-container="drawer">
            {/* Add Sources button: writes 'Add Sources' on desktop, compact 'Add' on smaller screens */}
            <button
              type="button"
              id="drawerAddSourcesBtn"
              onClick={() => setAddSourceMenuOpen((prev) => (prev === 'drawer' ? null : 'drawer'))}
              title="Add sources to chat"
              aria-label="Add sources"
              className="py-1.5 px-2.5 sm:px-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold flex items-center gap-1 sm:gap-1.5 transition-all cursor-pointer shadow-xs active:scale-95 shrink-0"
            >
              <svg
                className="w-3.5 h-3.5 shrink-0"
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
              {/* Responsive label: compact 'Add' on mobile, full 'Add Sources' on larger screens */}
              <span className="hidden sm:inline">Add Sources</span>
              <span className="sm:hidden font-medium">Add</span>
              <svg
                className={`w-3 h-3 shrink-0 transition-transform duration-150 ${addSourceMenuOpen === 'drawer' ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  d="M19 9l-7 7-7-7"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                />
              </svg>
            </button>

            {addSourceMenuOpen === 'drawer' && (
              <>
                {/* Backdrop to dismiss menu */}
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setAddSourceMenuOpen(null)}
                  aria-hidden="true"
                />

                <div className="absolute right-0 top-full mt-1.5 w-64 bg-white dark:bg-[#1e1f20] border border-slate-200/90 dark:border-white/10 rounded-2xl shadow-2xl z-50 p-1.5 animate-in fade-in zoom-in-95 duration-150">
                  <button
                    type="button"
                    onClick={() => {
                      setAddSourceMenuOpen(null);
                      onBrowseFileClick();
                    }}
                    className="w-full text-left px-3 py-2 rounded-xl hover:bg-slate-100 dark:hover:bg-white/10 text-slate-800 dark:text-slate-200 text-xs font-medium flex items-center gap-2.5 transition-colors cursor-pointer group"
                  >
                    <div className="w-7 h-7 rounded-lg bg-slate-100 dark:bg-white/10 flex items-center justify-center text-slate-600 dark:text-slate-300 group-hover:bg-indigo-50 group-hover:text-indigo-600 dark:group-hover:bg-indigo-500/20 dark:group-hover:text-[#a8c7fa] shrink-0">
                      <svg
                        className="w-4 h-4"
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
                      <div className="font-semibold text-slate-900 dark:text-white">
                        Browse from PC
                      </div>
                      <div className="text-[10px] text-slate-400 dark:text-slate-500 truncate">
                        Upload fresh PDF/DOCX to parse
                      </div>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setAddSourceMenuOpen(null);
                      onOpenLibraryPicker();
                    }}
                    className="w-full text-left px-3 py-2 rounded-xl hover:bg-slate-100 dark:hover:bg-white/10 text-slate-800 dark:text-slate-200 text-xs font-medium flex items-center gap-2.5 transition-colors cursor-pointer group mt-0.5"
                  >
                    <div className="w-7 h-7 rounded-lg bg-indigo-50 dark:bg-indigo-500/15 flex items-center justify-center text-indigo-600 dark:text-[#a8c7fa] group-hover:bg-indigo-100 dark:group-hover:bg-indigo-500/25 shrink-0">
                      <svg
                        className="w-4 h-4"
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
                      <div className="flex items-center gap-1.5 font-semibold text-indigo-600 dark:text-[#a8c7fa]">
                        <span>Attach from Library</span>
                        <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 font-mono">
                          Instant
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-400 dark:text-slate-500 truncate">
                        Pre-indexed GraphRAG docs
                      </div>
                    </div>
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Source items list */}
        <div
          className="flex-1 overflow-y-auto p-2.5 sm:p-4 space-y-2"
          style={{ scrollbarWidth: 'thin' }}
        >
          <div className="px-1 text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider flex items-center justify-between">
            <span>Documents in Chat</span>
            <span>{isOnline ? sourceDocs.length : 0} total</span>
          </div>

          {!isOnline && (
            <div className="flex items-center gap-2.5 p-3 rounded-xl bg-amber-500/10 border border-amber-500/25 text-amber-700 dark:text-amber-300 text-xs">
              <div className="w-2 h-2 rounded-full bg-amber-400 shrink-0 animate-pulse" />
              <span>
                Gateway Disconnected: Unable to reach backend document store. Connect your gateway
                in Control Center to sync documents.
              </span>
            </div>
          )}

          {filteredDocs.map((doc) => {
            const ready = isDocReady(doc);
            const isProcessing = !ready;
            const progress = doc.uploadProgress ?? (isProcessing ? 45 : 100);

            return (
              <div
                key={doc.id}
                onClick={() => !isProcessing && onToggleSourceDoc(doc.id)}
                className={`p-2.5 sm:p-3 rounded-xl border transition-all flex items-center justify-between gap-2.5 sm:gap-3 select-none ${
                  isProcessing
                    ? 'filter blur-[1.5px] opacity-70 bg-slate-50/50 dark:bg-white/[0.01] border-slate-200/60 dark:border-white/5 cursor-wait'
                    : doc.selected
                      ? 'bg-indigo-50/70 border-indigo-200 dark:bg-indigo-500/10 dark:border-indigo-500/30 shadow-2xs cursor-pointer'
                      : 'bg-slate-50/50 hover:bg-slate-100 border-slate-200/60 dark:bg-white/[0.02] dark:hover:bg-white/[0.05] dark:border-white/[0.06] opacity-75 hover:opacity-100 cursor-pointer'
                }`}
              >
                <div className="flex items-center gap-2.5 sm:gap-3 flex-1 min-w-0">
                  {isProcessing ? (
                    <div className="shrink-0 w-4 h-4 flex items-center justify-center">
                      <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping" />
                    </div>
                  ) : (
                    <input
                      type="checkbox"
                      checked={doc.selected}
                      onChange={(e) => {
                        e.stopPropagation();
                        onToggleSourceDoc(doc.id);
                      }}
                      className="rounded border-slate-300 dark:border-white/20 bg-white dark:bg-white/10 text-indigo-600 focus:ring-0 cursor-pointer shrink-0"
                    />
                  )}

                  {/* File icon */}
                  <div className="relative shrink-0">
                    <div
                      className={`w-7 h-7 sm:w-8 sm:h-8 rounded-lg flex items-center justify-center shrink-0 ${
                        doc.color === 'rose'
                          ? 'bg-rose-50 text-rose-600 dark:bg-rose-500/15 dark:text-rose-400'
                          : doc.color === 'emerald'
                            ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-400'
                            : doc.color === 'amber'
                              ? 'bg-amber-50 text-amber-600 dark:bg-amber-500/15 dark:text-amber-400'
                              : 'bg-indigo-50 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-400'
                      }`}
                    >
                      <svg
                        className="w-3.5 h-3.5 sm:w-4 sm:h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="1.75"
                          d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                        />
                      </svg>
                    </div>
                  </div>

                  <div className="space-y-0.5 flex-1 min-w-0">
                    <p className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">
                      {doc.name}
                    </p>
                    <div className="text-[10px] text-slate-500 dark:text-slate-400 flex items-center gap-1.5 truncate">
                      <span>
                        {doc.size === '0.0 MB' || doc.size === '0.0MB' || doc.size === '0 MB'
                          ? doc.bytes
                            ? formatBytes(doc.bytes)
                            : '< 1 MB'
                          : doc.size}
                      </span>
                      <span>•</span>
                      {isProcessing ? (
                        <span className="text-amber-600 dark:text-amber-400 font-medium animate-pulse truncate">
                          Uploading & parsing in GraphRAG... ({Math.round(progress)}%)
                        </span>
                      ) : (
                        <>
                          <span>{doc.pages} pp.</span>
                          {doc.selected && (
                            <span className="ml-1 text-indigo-600 dark:text-[#a8c7fa] font-semibold">
                              Active Context
                            </span>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Right: Progress indicator or delete button */}
                <div className="flex items-center shrink-0">
                  {isProcessing ? (
                    <div className="flex items-center gap-1.5 text-[11px] font-mono text-indigo-600 dark:text-[#a8c7fa]">
                      <CircularUploadProgress
                        progress={progress}
                        size={22}
                        strokeWidth={2}
                        showPercentText={true}
                      />
                    </div>
                  ) : (
                    <div className="flex items-center gap-1">
                      {onViewPdf && ready && doc.name.toLowerCase().endsWith('.pdf') && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onViewPdf(doc.name, 1);
                          }}
                          className="px-2 py-1 text-[11px] font-medium text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300 bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-500/15 dark:hover:bg-indigo-500/25 rounded-lg border border-indigo-200/80 dark:border-indigo-500/30 transition-all cursor-pointer flex items-center gap-1 shrink-0"
                          title={`View ${doc.name} in PDF Viewer`}
                          aria-label={`View ${doc.name} in PDF Viewer`}
                        >
                          <svg
                            className="w-3.5 h-3.5"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth="2"
                              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                            />
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth="2"
                              d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                            />
                          </svg>
                          <span className="hidden sm:inline">View PDF</span>
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteSourceDoc(doc.id, doc.name);
                        }}
                        className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:text-rose-400 dark:hover:bg-rose-500/10 rounded-lg transition-all cursor-pointer opacity-75 hover:opacity-100"
                        title="Delete source"
                        aria-label={`Delete source ${doc.name}`}
                      >
                        <svg
                          className="w-3.5 h-3.5"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth="2"
                            d="M6 18L18 6M6 6l12 12"
                          />
                        </svg>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {filteredDocs.length === 0 && (
            <div className="text-center py-5 sm:py-7 px-4 rounded-2xl border border-dashed border-slate-200 dark:border-white/10 bg-slate-50/50 dark:bg-white/[0.01]">
              <div className="w-9 h-9 sm:w-11 sm:h-11 mx-auto mb-2.5 rounded-2xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400">
                <svg
                  className="w-5 h-5 sm:w-6 sm:h-6"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="1.5"
                    d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                  />
                </svg>
              </div>
              <p className="text-xs sm:text-sm font-semibold text-slate-900 dark:text-white">
                {!isOnline
                  ? 'Gateway Disconnected'
                  : sourceFilter
                    ? 'No matching sources found'
                    : 'No sources attached yet'}
              </p>
              <p className="text-[11px] sm:text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm mx-auto">
                {!isOnline
                  ? 'Connect to your pipeline gateway in Control Center or Settings to view indexed documents.'
                  : sourceFilter
                    ? `No sources match "${sourceFilter}". Try a different keyword.`
                    : 'Click the Add button above to attach documents to this conversation.'}
              </p>
            </div>
          )}
        </div>

        {/* Footer with Selection Summary & Close - Styled like Settings Modal */}
        <div className="p-2.5 sm:px-4 sm:py-3 border-t border-slate-200 dark:border-white/10 bg-slate-50/80 dark:bg-white/[0.02] flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-500' : 'bg-slate-400'}`}
            />
            <span className="text-[11.5px] font-medium text-slate-600 dark:text-slate-300">
              {isOnline
                ? `${activeSourcesCount} of ${sourceDocs.length} sources enabled`
                : 'Gateway offline • 0 active documents'}
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-slate-900 text-white hover:bg-slate-800 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100 transition-all shadow-xs active:scale-95 cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
