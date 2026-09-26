import type React from 'react';

export interface FastExpertToggleProps {
  parseMode: 'fast' | 'expert';
  onSelectMode: (mode: 'fast' | 'expert') => void;
  isOnline?: boolean;
  variant?: 'desktop' | 'mobile';
  className?: string;
}

export const FastExpertToggle: React.FC<FastExpertToggleProps> = ({
  parseMode,
  onSelectMode,
  isOnline = false,
  variant = 'desktop',
  className = '',
}) => {
  if (variant === 'mobile') {
    return (
      <div className={`mb-4 sm:hidden ${className}`}>
        <div className="px-1 mb-2">
          <span className="text-[11px] font-semibold tracking-wider text-slate-400 dark:text-slate-500 uppercase">
            Research Engine Mode
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2 bg-slate-100 dark:bg-white/[0.06] p-1 rounded-2xl border border-slate-200/80 dark:border-white/10">
          <button
            type="button"
            onClick={() => onSelectMode('fast')}
            className={`flex items-center justify-center gap-2 py-2 px-3 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
              parseMode === 'fast'
                ? 'bg-white dark:bg-white/20 text-slate-900 dark:text-white shadow-xs ring-1 ring-black/5 dark:ring-white/10'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
            }`}
          >
            <svg
              className="w-3.5 h-3.5 text-indigo-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2.25"
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
            <span>Fast Mode</span>
          </button>
          <button
            type="button"
            onClick={() => onSelectMode('expert')}
            className={`flex items-center justify-center gap-2 py-2 px-3 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
              parseMode === 'expert'
                ? 'bg-white dark:bg-white/20 text-indigo-600 dark:text-white shadow-xs ring-1 ring-black/5 dark:ring-white/10'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
            }`}
          >
            <svg
              className="w-3.5 h-3.5 text-purple-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2.25"
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
            <span>Expert Mode</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`hidden sm:flex items-center bg-slate-100 dark:bg-white/[0.06] p-0.5 rounded-lg border border-slate-200/80 dark:border-white/[0.08] text-[clamp(10px,2.2vw,11px)] font-medium select-none ${className}`}
    >
      <button
        type="button"
        onClick={() => onSelectMode('fast')}
        className={`px-[clamp(0.375rem,1.5vw,0.5rem)] py-0.5 rounded-md transition-all cursor-pointer ${
          parseMode === 'fast'
            ? 'bg-white dark:bg-white/20 text-slate-900 dark:text-white font-semibold shadow-2xs'
            : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
        }`}
      >
        Fast
      </button>
      <button
        type="button"
        onClick={() => onSelectMode('expert')}
        className={`px-[clamp(0.375rem,1.5vw,0.5rem)] py-0.5 rounded-md transition-all cursor-pointer relative overflow-hidden ${
          parseMode === 'expert'
            ? 'bg-white dark:bg-white/20 text-slate-900 dark:text-white font-semibold shadow-2xs'
            : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
        }`}
      >
        {/* Expert mode gentle moving glow ray using light toner primary core color */}
        {parseMode === 'expert' && isOnline && (
          <span
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 overflow-hidden rounded-md z-0"
          >
            <span
              className="absolute inset-y-0 w-full -left-full animate-tunnel-ray pointer-events-none"
              style={{
                background:
                  'linear-gradient(90deg, transparent 0%, var(--box-light-primary, #6366f1) 50%, transparent 100%)',
                filter: 'blur(1.5px)',
                opacity: 0.35,
              }}
            />
          </span>
        )}
        <span className="relative z-10">Expert</span>
      </button>
    </div>
  );
};
