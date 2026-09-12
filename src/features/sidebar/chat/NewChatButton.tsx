import React from 'react';
import { SpecialTooltip } from '../../../components/ui/SpecialTooltip';

export interface NewChatButtonProps {
  isDrawerOpen: boolean;
  onClick: () => void;
}

export const NewChatButton: React.FC<NewChatButtonProps> = ({
  isDrawerOpen,
  onClick,
}) => {
  return (
    <div className="flex items-center h-10 shrink-0">
      <button
        type="button"
        onClick={onClick}
        className="w-full flex items-center group cursor-pointer text-left transition-all active:scale-[0.98]"
        aria-label="New chat"
      >
        <SpecialTooltip
          label="New chat"
          position="right"
          disabled={isDrawerOpen}
          className="w-14 sm:w-16 flex items-center justify-center shrink-0"
        >
          <div className="w-10 h-10 rounded-xl bg-slate-900 group-hover:bg-slate-800 text-white dark:bg-white/10 dark:group-hover:bg-white/15 dark:text-slate-100 flex items-center justify-center transition-colors shadow-xs">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path d="M12 4v16m8-8H4" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
            </svg>
          </div>
        </SpecialTooltip>
        <div
          className={`flex-1 flex items-center pl-1 pr-3 overflow-hidden transition-opacity duration-200 ${
            isDrawerOpen ? 'opacity-100' : 'opacity-0 pointer-events-none w-0'
          }`}
        >
          <span className="text-xs sm:text-sm font-semibold text-slate-800 dark:text-slate-200 group-hover:text-slate-950 dark:group-hover:text-white whitespace-nowrap">
            New chat
          </span>
        </div>
      </button>
    </div>
  );
};
