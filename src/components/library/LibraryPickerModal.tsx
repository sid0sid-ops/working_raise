import React, { useState, useEffect, useMemo } from 'react';
import { LibraryItem, documentItemToLibraryItem } from '../settings/SettingsLibraryTab';
import { sourceService } from '../../services/SourceService';
import { CircularUploadProgress } from '../ui/CircularUploadProgress';

export interface LibraryPickerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectDocument: (doc: LibraryItem) => void;
  attachedDocNames: string[];
  onOpenUploadFromPC: () => void;
  onViewPdf?: (filename: string, pageNumber?: number) => void;
}

export const LibraryPickerModal: React.FC<LibraryPickerModalProps> = ({
  isOpen,
  onClose,
  onSelectDocument,
  attachedDocNames,
  onOpenUploadFromPC,
  onViewPdf,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<'all' | 'pdf' | 'csv' | 'docx' | 'other'>('all');
  const [apiReadyFilenames, setApiReadyFilenames] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Load library items from backend state only
  const [items, setItems] = useState<LibraryItem[]>([]);

  // Query backend for authoritative documents and ready list
  useEffect(() => {
    if (!isOpen) return;
    let active = true;
    setIsLoading(true);
    sourceService
      .getDocuments()
      .then((resp) => {
        if (!active) return;
        if (resp.data && Array.isArray(resp.data.documents)) {
          const backendDocs = resp.data.documents.map(documentItemToLibraryItem);
          setItems(backendDocs);
          const readySet = new Set(
            resp.data.documents
              .filter((d) => d.status === 'ready' || d.status === 'indexed')
              .map((d) => (d.filename || d.name || '').toLowerCase())
              .filter(Boolean)
          );
          setApiReadyFilenames(readySet);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [isOpen]);

  // Handle ESC key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const isItemIndexed = (item: LibraryItem): boolean => {
    if (item.status === 'processing') return false;
    if (item.uploadProgress !== undefined && item.uploadProgress < 100) return false;
    if (apiReadyFilenames.size > 0 && apiReadyFilenames.has(item.name.toLowerCase())) {
      return true;
    }
    return item.status === 'indexed' || item.status === 'ready';
  };

  const attachedSet = useMemo(() => {
    return new Set(attachedDocNames.map((n) => n.toLowerCase().trim()));
  }, [attachedDocNames]);

  const filteredItems = useMemo(() => {
    let result = [...items];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter((item) => item.name.toLowerCase().includes(q));
    }

    if (typeFilter !== 'all') {
      result = result.filter((item) => {
        if (typeFilter === 'other') {
          return !['pdf', 'csv', 'docx'].includes(item.type);
        }
        return item.type === typeFilter;
      });
    }

    return result;
  }, [items, searchQuery, typeFilter]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[120] flex items-center justify-center p-[clamp(0.5rem,2vw,1.25rem)] bg-black/60 backdrop-blur-sm animate-in fade-in duration-150 select-none"
      onClick={onClose}
    >
      <div
        className="w-[min(94vw,38rem)] max-h-[88dvh] bg-white dark:bg-[#1e1f20] text-slate-900 dark:text-slate-100 border border-slate-300 dark:border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="library-picker-title"
      >
        {/* Header */}
        <div className="px-[clamp(0.875rem,2vw,1.25rem)] py-[clamp(0.75rem,1.8vw,1rem)] border-b border-slate-200 dark:border-white/10 flex items-center justify-between bg-slate-50/80 dark:bg-white/[0.02]">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-xl bg-indigo-50 dark:bg-indigo-500/15 border border-indigo-200/60 dark:border-indigo-500/30 flex items-center justify-center text-indigo-600 dark:text-[#a8c7fa] shrink-0">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <div className="min-w-0">
              <h3 id="library-picker-title" className="text-sm font-semibold text-slate-900 dark:text-white truncate">
                Select from Knowledge Base Library
              </h3>
              <p className="text-[11px] text-slate-500 dark:text-[#a8a8a8] truncate">
                Pre-parsed &amp; embedded in GraphRAG — instant retrieval with 0 indexing wait
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-white hover:bg-slate-200/50 dark:hover:bg-white/10 transition-colors cursor-pointer"
            aria-label="Close"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Search & Filter Bar */}
        <div className="p-4 border-b border-slate-200/80 dark:border-white/5 space-y-2.5 bg-slate-50/40 dark:bg-white/[0.01]">
          <div className="relative">
            <svg
              className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <circle cx="11" cy="11" r="8" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-4.35-4.35" />
            </svg>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search library documents..."
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl bg-white dark:bg-[#18191a] border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          {/* Type Filter Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5">
            {(['all', 'pdf', 'csv', 'docx', 'other'] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTypeFilter(t)}
                className={`px-2.5 py-0.5 rounded-full text-[11px] font-medium transition-colors whitespace-nowrap cursor-pointer ${
                  typeFilter === t
                    ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900'
                    : 'bg-slate-100 dark:bg-white/5 text-slate-600 dark:text-[#c4c7c5] hover:bg-slate-200/70 dark:hover:bg-white/10'
                }`}
              >
                {t === 'all' ? 'All' : t.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {/* Documents List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2.5 max-h-[50vh]" style={{ scrollbarWidth: 'thin' }}>
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-12 px-4 text-xs text-slate-400 dark:text-slate-500 gap-2.5">
              <div className="w-6 h-6 rounded-full border-2 border-slate-300 dark:border-slate-600 border-t-indigo-600 animate-spin" />
              <span className="font-medium">Checking Knowledge Base Library...</span>
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 px-4 text-center">
              <div className="w-12 h-12 rounded-2xl bg-slate-100 dark:bg-white/5 border border-slate-200/80 dark:border-white/10 flex items-center justify-center text-slate-400 dark:text-slate-500 mb-3">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <p className="text-xs font-semibold text-slate-800 dark:text-slate-200 mb-1">
                {searchQuery ? 'No matching documents found' : 'Your Library is currently empty'}
              </p>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 max-w-xs mb-4">
                {searchQuery
                  ? `No indexed documents matched "${searchQuery}". Try a different keyword or reset filters.`
                  : 'No documents have been indexed into the GraphRAG knowledge base yet. Upload files from your PC to get started.'}
              </p>
              {!searchQuery && (
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onOpenUploadFromPC();
                  }}
                  className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium transition-all active:scale-95 cursor-pointer shadow-xs flex items-center gap-1.5"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                  </svg>
                  <span>Upload Document from PC</span>
                </button>
              )}
            </div>
          ) : (
            filteredItems.map((item) => {
              const indexed = isItemIndexed(item);
              const isAttached = attachedSet.has(item.name.toLowerCase());
              const progress = item.uploadProgress ?? 45;

              const badgeBg =
                item.color === 'rose'
                  ? 'bg-rose-50 text-rose-600 dark:bg-rose-500/15 dark:text-rose-400 border-rose-200/60 dark:border-rose-500/20'
                  : item.color === 'emerald'
                  ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-400 border-emerald-200/60 dark:border-emerald-500/20'
                  : item.color === 'amber'
                  ? 'bg-amber-50 text-amber-600 dark:bg-amber-500/15 dark:text-amber-400 border-amber-200/60 dark:border-amber-500/20'
                  : 'bg-indigo-50 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-400 border-indigo-200/60 dark:border-indigo-500/20';

              return (
                <div
                  key={item.id}
                  className={`relative p-3 rounded-xl border transition-all flex items-center justify-between gap-3 ${
                    !indexed
                      ? 'filter blur-[1.5px] opacity-60 bg-slate-50/50 dark:bg-white/[0.01] border-slate-200/60 dark:border-white/5 cursor-not-allowed select-none'
                      : isAttached
                      ? 'bg-indigo-50/40 dark:bg-indigo-500/10 border-indigo-300/80 dark:border-indigo-500/30'
                      : 'bg-slate-50/70 dark:bg-white/[0.03] border-slate-200/80 dark:border-white/10 hover:border-indigo-300 dark:hover:border-indigo-500/40 hover:bg-white dark:hover:bg-[#252834]'
                  }`}
                  title={!indexed ? `Document is still parsing in GraphRAG... (${Math.round(progress)}%)` : item.name}
                >
                  {/* Left: Icon & Info */}
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="relative shrink-0">
                      <div className={`p-2 rounded-xl border ${badgeBg}`}>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                        </svg>
                      </div>
                    </div>

                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="text-xs font-semibold text-slate-900 dark:text-white truncate">
                          {item.name}
                        </h4>
                        {!indexed && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 shrink-0 flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
                            <span>Parsing...</span>
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-[11px] text-slate-500 dark:text-[#a8a8a8] mt-0.5">
                        <span className="font-mono">{item.size}</span>
                        <span>•</span>
                        {item.pages && (
                          <>
                            <span>•</span>
                            <span>{item.pages} pp.</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Right: Exactly ONE Circular Progress Spinner */}
                  <div className="shrink-0">
                    {!indexed ? (
                      <div
                        className="flex items-center gap-1 text-[11px] font-mono text-indigo-600 dark:text-[#a8c7fa] px-2 py-1"
                        title={`Parsing progress: ${Math.round(progress)}%`}
                      >
                        <CircularUploadProgress progress={progress} size={24} strokeWidth={2.5} showPercentText={true} />
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5">
                        {onViewPdf && item.type === 'pdf' && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              onViewPdf(item.name, 1);
                            }}
                            className="px-2.5 py-1.5 rounded-xl text-xs font-medium text-slate-700 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-[#a8c7fa] hover:bg-slate-100 dark:hover:bg-white/10 transition-colors flex items-center gap-1 cursor-pointer"
                            title={`Preview ${item.name} in PDF Viewer`}
                          >
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                            </svg>
                            <span className="hidden sm:inline">Preview</span>
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => onSelectDocument(item)}
                          className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer ${
                            isAttached
                              ? 'bg-emerald-600 text-white shadow-xs'
                              : 'bg-indigo-600 hover:bg-indigo-700 active:scale-95 text-white shadow-xs'
                          }`}
                        >
                          {isAttached ? (
                            <>
                              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                                <polyline points="20 6 9 17 4 12" />
                              </svg>
                              <span>Attached</span>
                            </>
                          ) : (
                            <>
                              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                              </svg>
                              <span>Attach</span>
                            </>
                          )}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3.5 border-t border-slate-200 dark:border-white/10 bg-slate-50/80 dark:bg-white/[0.02] flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => {
              onClose();
              onOpenUploadFromPC();
            }}
            className="text-xs text-indigo-600 dark:text-[#a8c7fa] hover:underline font-medium flex items-center gap-1.5 cursor-pointer"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            <span>Need a new file? Browse from PC</span>
          </button>

          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100 text-xs font-medium transition-all active:scale-95 cursor-pointer shadow-xs"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
