import React from 'react';
import { settingsJunction } from '../../settings/junction';

export interface UserProfileMenuProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenUsage: () => void;
  onLogout: () => void;
  onOpenSettings?: () => void;
}

export const UserProfileMenu: React.FC<UserProfileMenuProps> = ({
  isOpen,
  onClose,
  onOpenUsage,
  onLogout,
  onOpenSettings,
}) => {
  if (!isOpen) return null;

  const handleOpenSettings = () => {
    onClose();
    if (onOpenSettings) {
      onOpenSettings();
    } else {
      settingsJunction.open();
    }
  };

  const handleUsageClick = () => {
    onClose();
    onOpenUsage();
  };

  const handleLogoutClick = () => {
    onClose();
    onLogout();
  };

  return (
    <div
      id="userProfilePopover"
      role="menu"
      data-testid="user-profile-popover"
      aria-label="User Options"
      className="absolute bottom-full left-2 sm:left-3 mb-2 w-48 bg-white dark:bg-[#181b26] border border-slate-300 dark:border-white/10 rounded-2xl shadow-2xl z-50 p-1.5 animate-in fade-in zoom-in-95 duration-150 select-none text-slate-900 dark:text-slate-100"
    >
      {/* Tab 1: Settings (shows exact setting logo SVG as requested) */}
      <button
        type="button"
        id="railSettingsBtn"
        data-testid="rail-settings-btn"
        role="menuitem"
        aria-label="Settings"
        onClick={handleOpenSettings}
        className="w-full text-left px-2.5 py-2 rounded-xl hover:bg-slate-100 dark:hover:bg-white/10 text-slate-800 dark:text-slate-200 text-xs font-medium flex items-center justify-between transition-colors cursor-pointer group"
      >
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-slate-100 dark:bg-white/10 flex items-center justify-center text-slate-600 dark:text-slate-300 group-hover:bg-indigo-50 group-hover:text-indigo-600 dark:group-hover:bg-indigo-500/20 dark:group-hover:text-[#a8c7fa] shrink-0">
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="1.8"
              viewBox="0 0 24 24"
            >
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          </div>
          <span className="font-semibold text-slate-800 dark:text-slate-200">Settings</span>
        </div>
        <kbd className="text-[10px] font-mono text-slate-400 dark:text-slate-500">Cmd+/</kbd>
      </button>

      {/* Tab 2: Usage */}
      <button
        type="button"
        id="userMenuUsageBtn"
        data-testid="user-menu-usage-btn"
        role="menuitem"
        aria-label="Usage"
        onClick={handleUsageClick}
        className="w-full text-left px-2.5 py-2 rounded-xl hover:bg-slate-100 dark:hover:bg-white/10 text-slate-800 dark:text-slate-200 text-xs font-medium flex items-center justify-between transition-colors cursor-pointer group"
      >
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-slate-100 dark:bg-white/10 flex items-center justify-center text-slate-600 dark:text-slate-300 group-hover:bg-indigo-50 group-hover:text-indigo-600 dark:group-hover:bg-indigo-500/20 dark:group-hover:text-[#a8c7fa] shrink-0">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
              <path d="M18 20V10M12 20V4M6 20v-6" />
            </svg>
          </div>
          <span className="font-semibold text-slate-800 dark:text-slate-200">Usage</span>
        </div>
      </button>

      {/* Tab 3: Logout */}
      <button
        type="button"
        id="userMenuLogoutBtn"
        data-testid="user-menu-logout-btn"
        role="menuitem"
        aria-label="Logout"
        onClick={handleLogoutClick}
        className="w-full text-left px-2.5 py-2 rounded-xl hover:bg-rose-50 dark:hover:bg-rose-500/10 text-rose-600 dark:text-rose-400 text-xs font-medium flex items-center justify-between transition-colors cursor-pointer group"
      >
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-rose-50 dark:bg-rose-500/15 flex items-center justify-center text-rose-600 dark:text-rose-400 group-hover:bg-rose-100 dark:group-hover:bg-rose-500/25 shrink-0">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
          </div>
          <span className="font-semibold">Logout</span>
        </div>
      </button>
    </div>
  );
};
