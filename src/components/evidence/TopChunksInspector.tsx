import React from 'react';
import { TopChunk } from '../../types';
import { formatScore } from '../../utils/formatters';
import { FileText, Award } from 'lucide-react';

export interface TopChunksInspectorProps {
  chunks: TopChunk[];
}

export const TopChunksInspector: React.FC<TopChunksInspectorProps> = ({ chunks }) => {
  if (!chunks || chunks.length === 0) {
    return (
      <div className="p-6 text-center text-slate-500 text-xs">
        No fused candidate passages recorded.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {chunks.map((chunk, index) => (
        <div
          key={chunk.chunk_id || index}
          className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-lg hover:border-slate-700/80 transition-colors text-xs"
        >
          <div className="flex items-center justify-between mb-2 pb-2 border-b border-slate-900">
            <div className="flex items-center gap-2 text-slate-300">
              <span className="w-5 h-5 rounded bg-slate-800 text-slate-300 flex items-center justify-center font-mono text-[10px] font-bold">
                #{index + 1}
              </span>
              <span className="font-mono text-[11px] text-slate-400 truncate max-w-[220px]">
                {chunk.chunk_id}
              </span>
            </div>

            <div className="flex items-center gap-1.5 text-emerald-400 font-mono text-xs font-semibold">
              <Award className="w-3.5 h-3.5" />
              <span>RRF / Dense: {formatScore(chunk.similarity)}</span>
            </div>
          </div>

          <p className="text-slate-300 font-serif leading-relaxed line-clamp-4">
            "{chunk.text}"
          </p>

          {chunk.metadata && Object.keys(chunk.metadata).length > 0 && (
            <div className="mt-2.5 pt-2 border-t border-slate-900 flex flex-wrap gap-2 text-[10px] text-slate-500">
              {chunk.metadata.pdf_filename && (
                <span className="flex items-center gap-1 bg-slate-900 px-2 py-0.5 rounded text-slate-400">
                  <FileText className="w-3 h-3" /> {chunk.metadata.pdf_filename}
                </span>
              )}
              {chunk.metadata.primary_page && (
                <span className="bg-slate-900 px-2 py-0.5 rounded text-slate-400">
                  Page {chunk.metadata.primary_page}
                </span>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
