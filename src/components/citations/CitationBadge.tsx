import React, { useState, useRef, useEffect } from 'react';
import { Citation } from '../../types';
import { useUiStore } from '../../stores/uiStore';
import { ExternalLink, FileText, CheckCircle2 } from 'lucide-react';
import { formatScore } from '../../utils/formatters';

export interface CitationBadgeProps {
  index: number;
  citation?: Citation;
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({ index, citation }) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const leaveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const { openModal, setSelectedCitation } = useUiStore();

  const handleMouseEnter = () => {
    if (leaveTimeoutRef.current) {
      clearTimeout(leaveTimeoutRef.current);
      leaveTimeoutRef.current = null;
    }
    setShowTooltip(true);
  };

  const handleMouseLeave = () => {
    leaveTimeoutRef.current = setTimeout(() => {
      setShowTooltip(false);
    }, 180);
  };

  useEffect(() => {
    return () => {
      if (leaveTimeoutRef.current) {
        clearTimeout(leaveTimeoutRef.current);
      }
    };
  }, []);

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (citation && citation.pdf_filename) {
      setSelectedCitation(citation);
      openModal('pdf');
    } else {
      setShowTooltip((prev) => !prev);
    }
  };

  const pageNumber = citation?.primary_page || 1;
  const fileName = citation?.pdf_filename || `Institutional Source [${index}]`;

  return (
    <span className="relative inline-block mx-0.5 align-baseline">
      <button
        type="button"
        onClick={handleClick}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onFocus={handleMouseEnter}
        onBlur={handleMouseLeave}
        aria-label={`Citation [${index}]: ${fileName}, page ${pageNumber}`}
        className="inline-flex items-center justify-center px-1.5 py-0.5 text-[11px] font-mono font-semibold rounded bg-sky-50 hover:bg-sky-100 dark:bg-sky-950/80 dark:hover:bg-sky-900 text-sky-700 hover:text-sky-900 dark:text-sky-300 dark:hover:text-sky-100 border border-sky-300 hover:border-sky-400 dark:border-sky-800 dark:hover:border-sky-600 transition-all duration-150 cursor-pointer shadow-2xs hover:shadow-xs hover:scale-105 active:scale-95 select-none"
        title={citation?.pdf_filename ? `${citation.pdf_filename} (p. ${pageNumber})` : `Citation [${index}]`}
      >
        [{index}]
      </button>

      {showTooltip && (
        <div
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 sm:w-84 max-w-[calc(100vw-2.5rem)] p-3 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border border-slate-200 dark:border-slate-700/80 rounded-xl shadow-xl text-left pointer-events-auto animate-in fade-in zoom-in-95 duration-150 text-slate-800 dark:text-slate-200 select-text"
          role="tooltip"
        >
          {/* Header */}
          <div className="flex items-center justify-between gap-2 border-b border-slate-100 dark:border-slate-800 pb-2 mb-2">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-sky-700 dark:text-sky-400 min-w-0">
              <FileText className="w-3.5 h-3.5 shrink-0 text-sky-600 dark:text-sky-400" />
              <span className="truncate" title={fileName}>
                {fileName}
              </span>
            </div>
            {citation?.primary_page !== undefined && citation?.primary_page !== null && (
              <span className="text-[10px] font-mono font-bold bg-sky-50 dark:bg-sky-950/80 text-sky-700 dark:text-sky-300 px-1.5 py-0.5 rounded border border-sky-200 dark:border-sky-800 shrink-0">
                p. {citation.primary_page}
              </span>
            )}
          </div>

          {/* Heading */}
          {citation?.heading && (
            <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 mb-1.5 line-clamp-1 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-500 shrink-0" />
              <span className="truncate">{citation.heading}</span>
            </div>
          )}

          {/* Excerpt Quote */}
          {citation?.plain_text ? (
            <blockquote className="text-[11.5px] leading-relaxed text-slate-600 dark:text-slate-300 line-clamp-3 mb-2.5 font-sans italic bg-slate-50/90 dark:bg-white/[0.03] p-2 rounded-lg border-l-2 border-sky-400/80 dark:border-sky-500">
              "{citation.plain_text}"
            </blockquote>
          ) : (
            <p className="text-[11px] text-slate-500 dark:text-slate-400 italic mb-2">
              Verified institutional source excerpt
            </p>
          )}

          {/* Footer with Grounding Score and PDF Link */}
          <div className="flex items-center justify-between text-[10.5px] text-slate-500 dark:text-slate-400 pt-1.5 border-t border-slate-100 dark:border-slate-800/80">
            {citation?.similarity !== undefined ? (
              <span className="flex items-center gap-1 font-mono text-[10.5px] text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="w-3 h-3" />
                <span>Score: {formatScore(citation.similarity)}</span>
              </span>
            ) : (
              <span className="font-mono text-[10px] text-sky-600 dark:text-sky-400 font-medium">
                Verified Evidence
              </span>
            )}

            {citation?.pdf_filename && (
              <button
                type="button"
                onClick={handleClick}
                className="flex items-center gap-1 text-sky-600 dark:text-sky-400 font-semibold hover:text-sky-800 dark:hover:text-sky-200 hover:underline cursor-pointer transition-colors text-[11px]"
              >
                <span>View PDF (p. {pageNumber})</span>
                <ExternalLink className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* Arrow / Caret */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-white dark:border-t-slate-900 drop-shadow-2xs pointer-events-none" />
        </div>
      )}
    </span>
  );
};

