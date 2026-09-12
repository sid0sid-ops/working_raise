import React from 'react';
import { SpecialTooltip } from '../../components/ui/SpecialTooltip';

export interface HeaderProps {
  activeSourcesCount: number;
  onOpenSources: () => void;
  onOpenMobileMenu: () => void;
  isDrawerOpen?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  activeSourcesCount,
  onOpenSources,
  onOpenMobileMenu,
  isDrawerOpen = false,
}) => {
  return (
    <header
      id="mainTopHeader"
      className="fixed top-0 left-0 sm:left-16 right-0 z-[55] bg-transparent border-b-0 px-0 sm:px-4 h-14 sm:h-16 flex items-center justify-between pointer-events-none select-none"
      data-purpose="main-navigation"
    >
      {/* Brand & Mobile Hamburger Menu */}
      <div className="flex items-center h-full pointer-events-auto">
        <div className="w-14 h-14 flex items-center justify-center shrink-0 sm:hidden">
          {!isDrawerOpen && (
            <button
              type="button"
              id="mobileMenuToggleBtn"
              onClick={onOpenMobileMenu}
              aria-label="Open navigation menu"
              className="w-10 h-10 rounded-xl flex items-center justify-center text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-white dark:hover:bg-white/10 transition-colors cursor-pointer active:scale-95"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          )}
        </div>
        <span className="text-[clamp(1.125rem,2.5vw,1.375rem)] font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-1 whitespace-nowrap">
          Raise
        </span>
      </div>

      {/* Right Utility Icons: Sources Drawer Trigger */}
      <div
        className={`relative flex items-center gap-2 pr-3 sm:pr-0 transition-opacity duration-200 ${
          isDrawerOpen ? 'opacity-0 pointer-events-none' : 'pointer-events-auto'
        }`}
        id="settingsContainer"
      >
        <SpecialTooltip label="Drawer" position="bottom">
          <button
            id="navSourcesBtn"
            onClick={onOpenSources}
            aria-label="Drawer"
            className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-white dark:hover:bg-white/5 rounded-lg active:scale-95 transition-all flex items-center justify-center cursor-pointer relative"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="1.75"
              viewBox="0 0 24 24"
            >
              <path d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
            </svg>
            <span className="absolute -top-1 -right-1 px-1.5 py-0.2 rounded-full text-[10px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-500/20 dark:text-indigo-300 dark:border-indigo-400/30">
              {activeSourcesCount}
            </span>
          </button>
        </SpecialTooltip>
      </div>
    </header>
  );
};
