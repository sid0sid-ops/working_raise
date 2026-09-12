import React from 'react';
import { helpContent } from './helpContent';

export interface HelpTabProps {
  onNavigateToAbout?: () => void;
}

export const HelpTab: React.FC<HelpTabProps> = ({ onNavigateToAbout }) => {
  const { header, shortcuts, capabilities, architecture, platform } = helpContent;

  return (
    <div className="space-y-6 animate-in fade-in duration-200" data-testid="settings-help-tab">
      {/* Header */}
      <div>
        <h3 className="text-base font-semibold text-slate-900 dark:text-white">{header.title}</h3>
        <p className="text-xs text-slate-500 dark:text-[#a8a8a8] mt-1">
          {header.description}
        </p>
      </div>

      {/* Keyboard shortcuts */}
      <div className="space-y-2.5">
        <h4 className="text-xs font-semibold text-slate-800 dark:text-slate-200 uppercase tracking-wider">
          {shortcuts.sectionTitle}
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {shortcuts.items.map((item, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 dark:bg-[#282a2c] border border-slate-200/80 dark:border-[#37393b]"
            >
              <span className="text-xs text-slate-700 dark:text-slate-300">{item.label}</span>
              {item.separator ? (
                <div className="flex items-center gap-1">
                  {item.keys.map((k, kIdx) => (
                    <React.Fragment key={kIdx}>
                      <kbd className="px-1.5 py-1 text-[10px] font-mono bg-white dark:bg-[#18191a] text-slate-800 dark:text-slate-200 rounded border border-slate-200 dark:border-white/10 shadow-2xs">
                        {k}
                      </kbd>
                      {kIdx < item.keys.length - 1 && (
                        <span className="text-[10px] text-slate-400">{item.separator}</span>
                      )}
                    </React.Fragment>
                  ))}
                </div>
              ) : (
                <kbd className="px-2 py-1 text-[10px] font-mono bg-white dark:bg-[#18191a] text-slate-800 dark:text-slate-200 rounded border border-slate-200 dark:border-white/10 shadow-2xs">
                  {item.keys.join(' ')}
                </kbd>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Key capabilities guide */}
      <div className="space-y-2.5">
        <h4 className="text-xs font-semibold text-slate-800 dark:text-slate-200 uppercase tracking-wider">
          {capabilities.sectionTitle}
        </h4>
        <div className="space-y-2 text-xs">
          {capabilities.items.map((cap, idx) => (
            <div
              key={idx}
              className="p-3 rounded-xl bg-slate-50 dark:bg-[#282a2c] border border-slate-200/80 dark:border-[#37393b]"
            >
              <div className="font-semibold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                {cap.title}
              </div>
              <p className="text-slate-500 dark:text-[#a8a8a8] text-[11px] leading-relaxed">
                {cap.description}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Pipeline Architecture Routing */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold text-slate-800 dark:text-slate-200 uppercase tracking-wider">
            {architecture.sectionTitle}
          </h4>
          {onNavigateToAbout && (
            <button
              type="button"
              onClick={onNavigateToAbout}
              className="text-[11px] font-medium text-indigo-600 dark:text-[#a8c7fa] hover:underline cursor-pointer flex items-center gap-1"
            >
              <span>{architecture.linkText}</span>
              <span>&rarr;</span>
            </button>
          )}
        </div>

        {/* ASCII tree view */}
        <div className="hidden sm:block p-3.5 rounded-2xl bg-slate-950 text-slate-200 border border-slate-800 font-mono text-[10.5px] leading-tight overflow-x-auto shadow-inner select-all">
          <pre className="text-emerald-400 font-mono select-all">
            {architecture.asciiDiagram}
          </pre>
        </div>
      </div>

      {/* About Raise RAG Platform banner */}
      <div className="p-3.5 rounded-2xl bg-indigo-50/50 dark:bg-[#1a1b1c] border border-indigo-100 dark:border-white/[0.08] flex items-center justify-between">
        <div>
          <div className="text-xs font-semibold text-slate-900 dark:text-white">{platform.title}</div>
          <div className="text-[11px] text-slate-500 dark:text-[#a8a8a8]">
            {platform.description}
          </div>
        </div>
        <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-medium bg-indigo-100 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-300">
          {platform.version}
        </span>
      </div>
    </div>
  );
};

export default HelpTab;
