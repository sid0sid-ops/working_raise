import React, { useState } from 'react';
import { aboutContent } from './aboutContent';

export const AboutTab: React.FC = () => {
  const [showAsciiView, setShowAsciiView] = useState(false);
  const { header, asciiBlueprint, routerNode, modes, substrateSpecs } = aboutContent;
  const { fastMode, expertMode } = modes;

  return (
    <div className="space-y-6 animate-in fade-in duration-200" data-testid="settings-about-tab">
      {/* Header */}
      <div>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h3 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <span>{header.title}</span>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-indigo-100 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-300">
              {header.version}
            </span>
          </h3>
          <button
            type="button"
            onClick={() => setShowAsciiView(!showAsciiView)}
            className="text-[11px] font-mono text-indigo-600 dark:text-[#a8c7fa] hover:underline flex items-center gap-1 cursor-pointer"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
            <span>{showAsciiView ? header.hideAsciiText : header.showAsciiText}</span>
          </button>
        </div>
        <p className="text-xs text-slate-500 dark:text-[#a8a8a8] mt-1 leading-relaxed">
          {header.description}
        </p>
      </div>

      {/* ASCII Architecture Blueprint (Expandable) */}
      {showAsciiView && (
        <div className="p-3.5 rounded-2xl bg-slate-950 text-slate-200 border border-slate-800 font-mono text-[11px] overflow-x-auto leading-tight shadow-inner animate-in fade-in zoom-in-95 duration-150">
          <div className="text-slate-400 text-[10px] uppercase tracking-wider mb-2 font-semibold">
            {asciiBlueprint.sectionTitle}
          </div>
          <pre className="text-emerald-400 font-mono select-all">
            {asciiBlueprint.diagram}
          </pre>
        </div>
      )}

      {/* Dual Routing Architecture Cards with Visual Tree Connector */}
      <div className="space-y-4">
        {/* Top Router Node */}
        <div className="flex flex-col items-center">
          <div className="px-4 py-2 rounded-xl bg-slate-100 dark:bg-white/[0.06] border border-slate-200 dark:border-white/10 text-center shadow-xs">
            <div className="text-[10px] font-mono uppercase tracking-wider text-indigo-600 dark:text-[#a8c7fa] font-semibold">
              {routerNode.category}
            </div>
            <div className="text-xs font-semibold text-slate-900 dark:text-white mt-0.5">
              {routerNode.title}
            </div>
          </div>

          {/* SVG Tree Connector Lines */}
          <div className="w-full max-w-md h-8 hidden md:flex items-center justify-center relative my-0.5 pointer-events-none">
            {/* Center vertical down from top node */}
            <div className="absolute top-0 left-1/2 w-0.5 h-3 bg-slate-300 dark:bg-white/20 -translate-x-1/2" />
            {/* Horizontal branching bar */}
            <div className="absolute top-3 left-1/4 right-1/4 h-0.5 bg-slate-300 dark:bg-white/20" />
            {/* Left vertical drop with arrowhead */}
            <div className="absolute top-3 left-1/4 w-0.5 h-4 bg-slate-300 dark:bg-white/20" />
            <div className="absolute top-6 left-[calc(25%-3px)] border-solid border-t-slate-400 dark:border-t-white/40 border-t-4 border-x-transparent border-x-3 border-b-0" />
            {/* Right vertical drop with arrowhead */}
            <div className="absolute top-3 right-1/4 w-0.5 h-4 bg-slate-300 dark:bg-white/20" />
            <div className="absolute top-6 right-[calc(25%-3px)] border-solid border-t-slate-400 dark:border-t-white/40 border-t-4 border-x-transparent border-x-3 border-b-0" />
          </div>
        </div>

        {/* Dual Mode Cards (Side by Side) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 pt-1">
          {/* 1. FAST MODE */}
          <div
            data-testid={fastMode.testId}
            className="p-3.5 sm:p-4 rounded-2xl bg-slate-50 dark:bg-[#282a2c] border border-slate-200/90 dark:border-[#37393b] hover:border-amber-400/40 dark:hover:border-amber-400/30 transition-all space-y-2.5 sm:space-y-3 relative group"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shadow-xs" />
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white">
                  {fastMode.title}
                </h4>
              </div>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-amber-100 dark:bg-amber-500/15 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-500/20">
                {fastMode.badge}
              </span>
            </div>

            <p className="hidden sm:block text-[11px] text-slate-500 dark:text-[#a8a8a8] leading-relaxed">
              {fastMode.description}
            </p>

            <div className="space-y-1.5 sm:space-y-2 pt-0.5">
              {fastMode.features.map((feature, idx) => (
                <div key={idx} className="flex items-start gap-2 text-xs">
                  <span className="text-amber-500 font-bold">•</span>
                  <div>
                    <span className="font-semibold text-slate-800 dark:text-slate-200">{feature.title}</span>
                    <p className="hidden sm:block text-[11px] text-slate-500 dark:text-[#a8a8a8] mt-0.5">
                      {feature.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 2. EXPERT MODE */}
          <div
            data-testid={expertMode.testId}
            className="p-3.5 sm:p-4 rounded-2xl bg-slate-50 dark:bg-[#282a2c] border border-slate-200/90 dark:border-[#37393b] hover:border-emerald-400/40 dark:hover:border-emerald-400/30 transition-all space-y-2.5 sm:space-y-3 relative group"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-xs" />
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white">
                  {expertMode.title}
                </h4>
              </div>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-emerald-100 dark:bg-emerald-500/15 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-500/20">
                {expertMode.badge}
              </span>
            </div>

            <p className="hidden sm:block text-[11px] text-slate-500 dark:text-[#a8a8a8] leading-relaxed">
              {expertMode.description}
            </p>

            <div className="space-y-1.5 sm:space-y-2 pt-0.5">
              {expertMode.features.map((feature, idx) => (
                <div key={idx} className="flex items-start gap-2 text-xs">
                  <span className="text-emerald-500 font-bold">•</span>
                  <div>
                    <span className="font-semibold text-slate-800 dark:text-slate-200">{feature.title}</span>
                    <p className="hidden sm:block text-[11px] text-slate-500 dark:text-[#a8a8a8] mt-0.5">
                      {feature.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* System Specifications Card */}
      <div className="p-3.5 sm:p-4 rounded-2xl bg-slate-50 dark:bg-[#282a2c] border border-slate-200/80 dark:border-[#37393b] space-y-3">
        <h4 className="text-xs font-semibold text-slate-900 dark:text-white uppercase tracking-wider flex items-center gap-2">
          <svg className="w-4 h-4 text-indigo-600 dark:text-[#a8c7fa]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2" strokeWidth="2" />
            <line x1="8" y1="21" x2="16" y2="21" strokeWidth="2" />
            <line x1="12" y1="17" x2="12" y2="21" strokeWidth="2" />
          </svg>
          <span>{substrateSpecs.sectionTitle}</span>
        </h4>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
          {substrateSpecs.items.map((spec, idx) => (
            <div key={idx} className="p-2.5 rounded-xl bg-white dark:bg-[#1f2022] border border-slate-200/70 dark:border-white/5">
              <div className="text-[10px] text-slate-400 uppercase font-mono">{spec.label}</div>
              <div className="font-semibold text-slate-800 dark:text-slate-200 mt-0.5">{spec.value}</div>
              <div className="hidden sm:block text-[11px] text-slate-500 dark:text-slate-400">{spec.detail}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AboutTab;
