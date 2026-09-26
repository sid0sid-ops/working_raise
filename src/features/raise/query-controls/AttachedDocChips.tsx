import type React from 'react';
import { CircularUploadProgress } from '../../../components/ui/CircularUploadProgress';
import type { SourceDocument } from '../../../types';

export interface AttachedDocChipsProps {
  selectedDocs: SourceDocument[];
  isDocReady: (doc: SourceDocument) => boolean;
  onRemoveDoc: (id: string) => void;
  onOpenDrawer?: () => void;
  conversationLength?: number;
  variant?: 'desktop' | 'mobile';
  className?: string;
}

export const AttachedDocChips: React.FC<AttachedDocChipsProps> = ({
  selectedDocs,
  isDocReady,
  onRemoveDoc,
  onOpenDrawer,
  conversationLength = 0,
  variant = 'desktop',
  className = '',
}) => {
  if (variant === 'mobile') {
    if (selectedDocs.length === 0) return null;
    return (
      <div
        className={`flex sm:hidden items-center gap-1.5 mb-1.5 px-2.5 py-1 bg-white/95 dark:bg-[#1e1f20]/95 border border-slate-200/90 dark:border-white/10 rounded-full shadow-xs overflow-x-auto scrollbar-none animate-in fade-in slide-in-from-bottom-1 select-none ${className}`}
        data-purpose="mobile-attached-sources"
      >
        <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider pl-0.5 shrink-0">
          Sources ({selectedDocs.length}):
        </span>
        {selectedDocs.map((file) => {
          const ready = isDocReady(file);
          const isProcessing = !ready;
          const progress = file.uploadProgress ?? (isProcessing ? 45 : 100);

          return (
            <div
              key={`mob-${file.id}`}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 dark:bg-white/10 border border-slate-200 dark:border-white/10 shrink-0 text-[11px]"
            >
              <span className="truncate max-w-[100px] font-medium text-slate-700 dark:text-slate-200">
                {file.name}
              </span>
              {isProcessing ? (
                <div className="w-3 h-3">
                  <CircularUploadProgress progress={progress} size={12} strokeWidth={2} />
                </div>
              ) : (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemoveDoc(file.id);
                  }}
                  aria-label={`Remove mobile ${file.name}`}
                  className="text-slate-400 hover:text-slate-700 dark:hover:text-white rounded-full p-0.5 cursor-pointer"
                >
                  <svg
                    className="w-2.5 h-2.5"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  // Desktop horizontal scrolling chips
  return (
    <div
      className={`hidden sm:flex items-center space-x-1.5 sm:space-x-2 overflow-x-auto scrollbar-none py-0.5 select-none shrink ${className}`}
    >
      {selectedDocs.length === 0 && (
        <span className="text-[11px] text-slate-400 dark:text-slate-500 font-normal sm:hidden select-none truncate">
          Attach sources
        </span>
      )}

      {selectedDocs.map((file) => {
        const ready = isDocReady(file);
        const isProcessing = !ready;
        const progress = file.uploadProgress ?? (isProcessing ? 45 : 100);

        return (
          <div key={file.id} className="relative group cursor-pointer shrink-0 select-none">
            <button
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => onOpenDrawer?.()}
              aria-label={file.name}
              className={`${
                conversationLength === 0 ? 'w-7.5 h-7.5 sm:w-9 sm:h-9' : 'w-6 h-6 sm:w-7 sm:h-7'
              } rounded-lg bg-slate-100 hover:bg-slate-200 border border-slate-300/80 dark:bg-white/[0.06] dark:hover:bg-white/10 dark:border-white/10 hover:border-indigo-400/40 flex items-center justify-center transition-all shadow-xs active:scale-95 cursor-pointer relative overflow-hidden select-none outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50 ${
                isProcessing
                  ? 'filter blur-[1.5px] opacity-70 cursor-wait'
                  : 'filter-none opacity-100'
              }`}
              title={
                isProcessing
                  ? `Uploading & parsing in GraphRAG... (${Math.round(progress)}%)`
                  : `Source: ${file.name} (click to view in drawer)`
              }
            >
              <svg
                className={`w-3 h-3 sm:w-3.5 sm:h-3.5 ${
                  file.color === 'rose'
                    ? 'text-rose-600 dark:text-rose-400'
                    : file.color === 'emerald'
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : file.color === 'amber'
                        ? 'text-amber-600 dark:text-amber-400'
                        : 'text-indigo-600 dark:text-indigo-400'
                }`}
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
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="1.75"
                  d="M13 3v5a1 1 0 001 1h5"
                />
              </svg>
            </button>

            {/* While uploading and parsing: circular moving animation, no x button */}
            {isProcessing ? (
              <div
                className="absolute inset-0 flex items-center justify-center pointer-events-none z-10"
                title={`Uploading & parsing in GraphRAG... (${Math.round(progress)}%)`}
              >
                <CircularUploadProgress
                  progress={progress}
                  size={conversationLength === 0 ? 26 : 22}
                  strokeWidth={2}
                />
              </div>
            ) : (
              /* Once parsed and full circle: unblurred and show x sign to deselect/remove */
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onRemoveDoc(file.id);
                }}
                aria-label={`Remove ${file.name}`}
                className="absolute -top-1.5 -right-1.5 w-3.5 h-3.5 sm:w-4 sm:h-4 rounded-full bg-white dark:bg-[#12141d] border border-slate-300 dark:border-white/20 text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-20 shadow-xs cursor-pointer"
                title="Deselect source"
              >
                <svg
                  className="w-2 h-2 sm:w-2.5 sm:h-2.5"
                  fill="none"
                  stroke="currentColor"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2.5"
                  viewBox="0 0 24 24"
                >
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            )}

            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-50 pointer-events-none">
              <div className="bg-slate-900 text-white dark:bg-[#12141d] dark:border dark:border-white/10 dark:text-slate-200 text-[11px] font-medium py-1 px-2 rounded-md shadow-xl whitespace-nowrap">
                {isProcessing ? `Uploading: ${file.name} (${Math.round(progress)}%)` : file.name}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
