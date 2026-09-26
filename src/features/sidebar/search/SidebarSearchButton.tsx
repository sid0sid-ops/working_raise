import type React from 'react';
import { SpecialTooltip } from '../../../components/ui/SpecialTooltip';

export interface SidebarSearchButtonProps {
  isDrawerOpen: boolean;
  onClick: () => void;
}

export const SidebarSearchButton: React.FC<SidebarSearchButtonProps> = ({
  isDrawerOpen,
  onClick,
}) => {
  return (
    <div className="flex items-center h-10 shrink-0">
      <button
        type="button"
        onClick={onClick}
        className="w-full flex items-center group cursor-pointer text-left transition-all active:scale-[0.98]"
        aria-label="Search chats"
      >
        <SpecialTooltip
          label="Search chats"
          position="right"
          disabled={isDrawerOpen}
          className="w-14 sm:w-16 flex items-center justify-center shrink-0"
        >
          <div className="w-10 h-10 rounded-xl flex items-center justify-center text-slate-600 group-hover:text-slate-900 group-hover:bg-slate-100 dark:text-slate-400 dark:group-hover:text-white dark:group-hover:bg-white/10 transition-colors">
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
        </SpecialTooltip>
        <div
          className={`flex-1 flex items-center pl-1 pr-3 overflow-hidden transition-opacity duration-200 ${
            isDrawerOpen ? 'opacity-100' : 'opacity-0 pointer-events-none w-0'
          }`}
        >
          <span className="text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-300 group-hover:text-slate-950 dark:group-hover:text-white whitespace-nowrap">
            Search chats
          </span>
        </div>
      </button>
    </div>
  );
};
