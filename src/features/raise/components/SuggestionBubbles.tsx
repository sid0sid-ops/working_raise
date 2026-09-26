import React from 'react';

export interface SuggestionBubblesProps {
  /** List of contextual follow-up query suggestions */
  suggestions: string[];
  /** Callback fired when a user clicks a suggestion */
  onSelect: (query: string) => void;
  /** Whether interactions should be disabled (e.g. while generating) */
  disabled?: boolean;
  /** Optional custom styling classes */
  className?: string;
}

/**
 * Modular SuggestionBubbles Component (ChatGPT & NotebookLM style)
 * Renders high-probability follow-up suggestions in a clean vertical stack
 * directly in the conversation stream below the assistant's response.
 */
export const SuggestionBubbles: React.FC<SuggestionBubblesProps> = React.memo(
  ({ suggestions, onSelect, disabled = false, className = '' }) => {
    if (!suggestions || suggestions.length === 0) {
      return null;
    }

    return (
      <div
        data-purpose="suggestion-bubbles"
        className={`mt-3.5 mb-1 flex flex-col gap-1.5 w-full max-w-2xl animate-in fade-in slide-in-from-bottom-1 duration-200 ${className}`}
        role="region"
        aria-label="Suggested follow-up questions"
      >
        {suggestions.map((bubbleText, bIdx) => (
          <button
            key={`${bIdx}-${bubbleText.slice(0, 20)}`}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(bubbleText)}
            className="w-full text-left px-3.5 py-2.5 rounded-xl text-xs font-medium bg-white/90 dark:bg-[#1a1d29]/90 hover:bg-indigo-50/90 dark:hover:bg-indigo-950/60 border border-slate-200/90 dark:border-white/10 hover:border-indigo-300 dark:hover:border-indigo-600/80 text-slate-700 dark:text-slate-200 shadow-2xs hover:shadow-xs transition-all flex items-center justify-between gap-3 cursor-pointer group disabled:opacity-50 disabled:pointer-events-none active:scale-[0.99]"
          >
            <span className="flex items-center gap-2.5 min-w-0 flex-1">
              <span
                className="text-indigo-500 dark:text-indigo-400 text-[11px] group-hover:scale-110 transition-transform shrink-0"
                aria-hidden="true"
              >
                ✨
              </span>
              <span className="truncate">{bubbleText}</span>
            </span>
            <span
              className="text-slate-400 group-hover:text-indigo-500 dark:group-hover:text-indigo-400 font-bold transition-transform group-hover:translate-x-0.5 shrink-0 text-xs"
              aria-hidden="true"
            >
              →
            </span>
          </button>
        ))}
      </div>
    );
  }
);

SuggestionBubbles.displayName = 'SuggestionBubbles';
