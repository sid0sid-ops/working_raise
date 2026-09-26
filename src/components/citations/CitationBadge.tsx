import { ExternalLink, FileText, Layers } from 'lucide-react';
import type React from 'react';
import { useEffect, useRef, useState } from 'react';
import { sourceService } from '../../services/SourceService';
import type { Citation } from '../../types';
import { extractVerifiedPageNumber } from '../../utils/citationParser';

export interface CitationBadgeProps {
  index?: number;
  indices?: number[];
  citation?: Citation;
  citations?: Citation[];
  onViewPdf?: (fileName: string, page: number) => void;
}

interface CitationItemDetail {
  index: number;
  pageNumber?: number;
  fileName: string;
  pdfUrl?: string;
  heading?: string;
  plainText?: string;
}

function resolveCitationDetail(cit?: Citation, fallbackIndex: number = 1): CitationItemDetail {
  const pageNumber = extractVerifiedPageNumber(cit);

  const rawFileName =
    cit?.pdf_filename ||
    (cit as any)?.filename ||
    (cit as any)?.file_name ||
    (cit as any)?.document_name ||
    (cit as any)?.doc_name ||
    (cit as any)?.source ||
    (cit as any)?.metadata?.pdf_filename ||
    (cit as any)?.metadata?.filename;

  const fileName =
    rawFileName && rawFileName !== 'Document' ? rawFileName : rawFileName || 'Audited Document';
  const effectivePage = pageNumber || 1;
  const pdfUrl = rawFileName ? sourceService.getPdfUrl(rawFileName, effectivePage) : undefined;

  return {
    index: cit?.citation_index ?? fallbackIndex,
    pageNumber,
    fileName,
    pdfUrl,
    heading: cit?.heading,
    plainText: cit?.plain_text,
  };
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({
  index,
  indices,
  citation,
  citations,
  onViewPdf,
}) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const leaveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

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

  // Determine list of citations to show
  const rawList: { cit?: Citation; idx: number }[] = [];
  if (citations && citations.length > 0) {
    citations.forEach((c, i) => {
      const idx = indices?.[i] ?? c.citation_index ?? (index ? index + i : i + 1);
      rawList.push({ cit: c, idx });
    });
  } else if (indices && indices.length > 0) {
    indices.forEach((idx) => {
      rawList.push({ cit: citation, idx });
    });
  } else {
    rawList.push({ cit: citation, idx: index ?? 1 });
  }

  const items: CitationItemDetail[] = rawList.map((item) =>
    resolveCitationDetail(item.cit, item.idx)
  );

  const isMultiple = items.length > 1;
  const firstItem = items[0] || {
    index: index ?? 1,
    fileName: 'Audited Document',
    pageNumber: undefined,
  };
  const buttonLabel = isMultiple
    ? `[${items.map((it) => it.index).join(', ')}]`
    : `[${firstItem.index}]`;

  const handleTogglePopover = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowTooltip((prev) => !prev);
  };

  const handleOpenDoc = (
    e: React.MouseEvent,
    pdfUrl?: string,
    fileName?: string,
    page?: number
  ) => {
    e.stopPropagation();
    if (onViewPdf && fileName) {
      onViewPdf(fileName, page || 1);
      return;
    }
    if (pdfUrl && typeof window !== 'undefined') {
      window.open(pdfUrl, '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <span className="relative inline-block mx-0.5 align-baseline">
      <button
        type="button"
        onClick={handleTogglePopover}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onFocus={handleMouseEnter}
        onBlur={handleMouseLeave}
        aria-label={
          isMultiple
            ? `Citations ${buttonLabel}`
            : `Citation [${firstItem.index}]: ${firstItem.fileName}${firstItem.pageNumber ? `, page ${firstItem.pageNumber}` : ''}`
        }
        className="inline-flex items-center justify-center px-1.5 py-0.2 text-[11px] font-mono font-semibold rounded bg-indigo-50/90 hover:bg-indigo-100 dark:bg-indigo-950/80 dark:hover:bg-indigo-900 text-indigo-700 hover:text-indigo-900 dark:text-[#a8c7fa] dark:hover:text-white border border-indigo-200/90 hover:border-indigo-400 dark:border-indigo-800/80 dark:hover:border-indigo-600 transition-all duration-150 cursor-pointer shadow-2xs hover:scale-105 active:scale-95 select-none"
        title={
          isMultiple
            ? `Multiple citations ${buttonLabel} - Click to inspect`
            : firstItem.fileName
              ? `${firstItem.fileName}${firstItem.pageNumber ? ` (Page ${firstItem.pageNumber})` : ''} - Click to inspect source`
              : `Citation [${firstItem.index}]`
        }
      >
        <span>{buttonLabel}</span>
        {firstItem.pageNumber !== undefined && firstItem.pageNumber > 0 && (
          <span className="ml-1 text-[9.5px] font-mono font-medium opacity-85">
            p.{firstItem.pageNumber}
          </span>
        )}
      </button>

      {showTooltip && (
        <div
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          className={`absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 ${
            isMultiple ? 'w-64 sm:w-72 max-h-80' : 'w-56 sm:w-64 max-h-72'
          } max-w-[calc(100vw-2rem)] p-2.5 bg-black/95 dark:bg-black/95 text-white backdrop-blur-md border border-white/15 rounded-xl shadow-2xl shadow-black/80 text-left pointer-events-auto animate-in fade-in zoom-in-95 duration-150 select-text overflow-y-auto`}
          role="tooltip"
        >
          {isMultiple && (
            <div className="flex items-center gap-1.5 pb-1.5 mb-2 border-b border-white/10 text-[11px] font-semibold text-slate-300">
              <Layers className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
              <span>Citations ({items.length})</span>
            </div>
          )}

          <div className="space-y-2.5 divide-y divide-white/10">
            {items.map((item, i) => (
              <div key={`${item.index}-${i}`} className={i > 0 ? 'pt-2' : ''}>
                {/* Header with Document Name & Single Page Badge */}
                <div className="flex items-center justify-between gap-1.5">
                  <div
                    onClick={(e) =>
                      handleOpenDoc(e, item.pdfUrl, item.fileName, item.pageNumber || 1)
                    }
                    className="flex items-center gap-1 text-[11.5px] font-semibold text-slate-100 hover:text-indigo-400 transition-colors cursor-pointer min-w-0"
                    title="Click to open PDF document"
                  >
                    <FileText className="w-3 h-3 shrink-0 text-indigo-400" />
                    <span className="truncate">{item.fileName}</span>
                  </div>
                  {item.pageNumber !== undefined && item.pageNumber > 0 ? (
                    <span className="text-[10px] font-mono font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-1.5 py-0.2 rounded shrink-0">
                      Page {item.pageNumber}
                      <span className="sr-only"> (p. {item.pageNumber})</span>
                    </span>
                  ) : (
                    <span className="text-[10px] font-mono font-medium bg-slate-800 text-slate-400 border border-slate-700/60 px-1.5 py-0.2 rounded shrink-0">
                      Doc Source
                    </span>
                  )}
                </div>

                {/* Heading */}
                {item.heading && (
                  <div className="text-[11px] font-medium text-slate-300 mt-1 line-clamp-1 flex items-center gap-1">
                    <span className="w-1 h-1 rounded-full bg-indigo-400 shrink-0" />
                    <span className="truncate">{item.heading}</span>
                  </div>
                )}

                {/* Excerpt Quote */}
                {item.plainText && (
                  <blockquote className="text-[10.5px] leading-relaxed text-slate-300 line-clamp-2 mt-1.5 italic bg-white/[0.04] p-1.5 rounded border-l-2 border-indigo-500/80">
                    "{item.plainText}"
                  </blockquote>
                )}

                {/* Footer with View PDF Link - Single page number display in header, clean action link here */}
                {item.pdfUrl && (
                  <div className="flex items-center justify-end text-[10.5px] pt-1.5 mt-1">
                    <button
                      type="button"
                      onClick={(e) =>
                        handleOpenDoc(e, item.pdfUrl, item.fileName, item.pageNumber || 1)
                      }
                      className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300 hover:underline cursor-pointer transition-colors text-[10.5px] font-medium"
                    >
                      <span>View PDF</span>
                      <ExternalLink className="w-2.5 h-2.5" />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Arrow / Caret - Black to match tooltip */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-black dark:border-t-black drop-shadow-2xs pointer-events-none" />
        </div>
      )}
    </span>
  );
};
