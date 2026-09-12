import React, { useState, useEffect } from 'react';
import { Citation } from '../../types';
import { sourceService } from '../../services/SourceService';
import { useModeStore } from '../../stores/modeStore';
import { FileText, ExternalLink, Hash, AlertTriangle, ArrowLeft, ArrowRight, Bookmark } from 'lucide-react';
import { formatScore } from '../../utils/formatters';

export interface InlinePdfViewerProps {
  citation: Citation;
}

export const InlinePdfViewer: React.FC<InlinePdfViewerProps> = ({ citation }) => {
  const { appMode } = useModeStore();
  const [loadError, setLoadError] = React.useState(false);
  const [activePage, setActivePage] = useState<number>(citation.primary_page || 1);

  useEffect(() => {
    setActivePage(citation.primary_page || 1);
    setLoadError(false);
  }, [citation.primary_page, citation.pdf_filename]);

  const pdfUrl = sourceService.getPdfUrl(citation.pdf_filename, activePage);

  return (
    <div className="flex flex-col h-full bg-slate-50 dark:bg-slate-950 rounded-2xl border border-slate-200 dark:border-white/10 overflow-hidden shadow-sm">
      {/* Viewer Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 bg-slate-100 dark:bg-[#1e212d] border-b border-slate-200 dark:border-white/10 text-xs shrink-0">
        <div className="flex items-center gap-2 text-slate-800 dark:text-slate-200 font-semibold truncate min-w-0 max-w-sm">
          <FileText className="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0" />
          <span className="truncate" title={citation.pdf_filename}>{citation.pdf_filename}</span>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          {/* Interactive Page Navigation Controls */}
          <div className="flex items-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-xl overflow-hidden shadow-2xs">
            <button
              type="button"
              onClick={() => setActivePage((p) => Math.max(1, p - 1))}
              disabled={activePage <= 1}
              className="px-2 py-1 text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white disabled:opacity-30 disabled:cursor-not-allowed hover:bg-slate-100 dark:hover:bg-white/10 transition-colors flex items-center justify-center cursor-pointer"
              title="Previous Page"
              aria-label="Previous Page"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
            </button>
            <span
              data-testid="active-page-badge"
              className="px-3 py-1 text-xs font-mono font-bold text-indigo-600 dark:text-[#a8c7fa] border-x border-slate-200 dark:border-white/10 flex items-center gap-1 select-none"
            >
              <Hash className="w-3 h-3 text-slate-400" />
              Page {activePage}
            </span>
            <button
              type="button"
              onClick={() => setActivePage((p) => p + 1)}
              className="px-2 py-1 text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/10 transition-colors flex items-center justify-center cursor-pointer"
              title="Next Page"
              aria-label="Next Page"
            >
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {activePage !== citation.primary_page && (
            <button
              type="button"
              onClick={() => setActivePage(citation.primary_page)}
              className="px-2.5 py-1 text-[11px] font-semibold text-indigo-600 dark:text-[#a8c7fa] bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800/80 rounded-xl hover:bg-indigo-100 dark:hover:bg-indigo-900 transition-colors cursor-pointer flex items-center gap-1 shadow-2xs"
              title={`Return to cited page ${citation.primary_page}`}
            >
              <Bookmark className="w-3 h-3" />
              <span>Cited Page ({citation.primary_page})</span>
            </button>
          )}

          <a
            href={pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200 transition-colors px-2.5 py-1 rounded-xl hover:bg-slate-200/60 dark:hover:bg-white/5"
          >
            <span>Open in Tab</span>
            <ExternalLink className="w-3 h-3 ml-0.5" />
          </a>
        </div>
      </div>

      {/* Main Content Pane */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
        {/* Left Side: Layout Extracted Evidence Passage */}
        <div className="w-full md:w-80 bg-white dark:bg-slate-900/80 p-4 border-r border-slate-200 dark:border-white/10 flex flex-col gap-3.5 overflow-y-auto">
          <div>
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 dark:text-slate-400">
              Extracted Heading
            </span>
            <p className="text-xs font-bold text-slate-900 dark:text-slate-100 mt-0.5">
              {citation.heading || 'Academic Report Section'}
            </p>
          </div>

          <div>
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 dark:text-slate-400">
                Target Evidence Passage
              </span>
              <button
                type="button"
                onClick={() => setActivePage(citation.primary_page)}
                className="text-[10px] font-mono font-semibold text-indigo-600 dark:text-[#a8c7fa] hover:underline cursor-pointer"
              >
                Page {citation.primary_page}
              </button>
            </div>
            <div className="mt-1 p-3 bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-white/10 rounded-xl font-serif text-xs leading-relaxed text-slate-800 dark:text-slate-200">
              "{citation.plain_text}"
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-200 dark:border-white/10 text-[11px]">
            <div>
              <span className="text-slate-500 dark:text-slate-400 block text-[10px] uppercase font-medium">Chunk ID</span>
              <span className="font-mono text-slate-700 dark:text-slate-300 text-[10px] truncate block" title={citation.chunk_id}>
                {citation.chunk_id}
              </span>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400 block text-[10px] uppercase font-medium">Relevance</span>
              <span className="font-mono text-emerald-600 dark:text-emerald-400 font-bold">
                {formatScore(citation.similarity)}
              </span>
            </div>
          </div>

          <div className="mt-auto pt-3 border-t border-slate-200 dark:border-white/10 text-[11px] text-slate-500 dark:text-slate-400">
            <p className="flex items-center gap-1 text-[11px] text-indigo-600 dark:text-[#a8c7fa] font-medium">
              <span>Deep-linked to physical page {activePage}</span>
            </p>
          </div>
        </div>

        {/* Right Side: Embedded PDF Preview / Mock Canvas */}
        <div className="flex-1 bg-slate-100 dark:bg-slate-950 flex items-center justify-center p-3 relative overflow-hidden">
          {appMode === 'mock' ? (
            <div className="max-w-md p-6 bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-2xl text-center shadow-lg">
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 dark:bg-indigo-950/80 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center mx-auto mb-3 text-indigo-600 dark:text-indigo-400 shadow-2xs">
                <FileText className="w-6 h-6" />
              </div>
              <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                PDF Document Verification
              </h4>
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 mb-4 leading-relaxed">
                Viewing page{' '}
                <strong className="text-indigo-600 dark:text-[#a8c7fa] font-mono font-bold">
                  {activePage}
                </strong>{' '}
                of <strong className="text-slate-900 dark:text-slate-100">{citation.pdf_filename}</strong>.
              </p>
              <div className="text-[11px] font-mono bg-slate-50 dark:bg-slate-950 p-2.5 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-400 text-left">
                Route: GET /api/pdf/{encodeURIComponent(citation.pdf_filename)}#page={activePage}
              </div>
            </div>
          ) : loadError ? (
            <div className="max-w-md p-6 bg-white dark:bg-slate-900 border border-rose-200 dark:border-rose-900/50 rounded-2xl text-center shadow-lg">
              <div className="w-12 h-12 rounded-2xl bg-rose-50 dark:bg-rose-950/80 border border-rose-200 dark:border-rose-800 flex items-center justify-center mx-auto mb-3 text-rose-600 dark:text-rose-400">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-200">
                Unable to Display Document
              </h4>
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 mb-4 leading-relaxed">
                The document preview could not be loaded directly. You can retry or open the source in a new tab.
              </p>
              <div className="flex justify-center gap-2">
                <button
                  onClick={() => setLoadError(false)}
                  className="px-3 py-1.5 text-xs font-medium bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 rounded-xl transition-colors cursor-pointer"
                >
                  Retry Loading
                </button>
                <a
                  href={pdfUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1.5 text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl transition-colors inline-flex items-center gap-1 cursor-pointer"
                >
                  Open in New Tab <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          ) : (
            <iframe
              src={pdfUrl}
              title={`PDF viewer: ${citation.pdf_filename} page ${activePage}`}
              onError={() => setLoadError(true)}
              className="w-full h-full min-h-[520px] rounded-xl border border-slate-200 dark:border-slate-800 bg-white shadow-2xs"
            />
          )}
        </div>
      </div>
    </div>
  );
};

