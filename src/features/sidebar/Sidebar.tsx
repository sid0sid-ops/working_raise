import type React from 'react';
import { useEffect, useRef } from 'react';
import type { ChatSession } from '../../types';
import { ChatSessionList, NewChatButton } from './chat';
import { SidebarSearchButton } from './search';
import { SidebarSettingsTrigger, UserProfileMenu } from './settings';

export interface SidebarProps {
  isDrawerOpen: boolean;
  onToggleDrawer: () => void;
  onNewChat: () => void;
  onOpenSearch: () => void;
  onOpenSettings?: () => void;
  onOpenUsage: () => void;
  onLogout: () => void;

  // Session state
  sessions: ChatSession[];
  currentSessionId: string | null;
  pinnedSessionIds: string[];
  activeSessionMenuId: string | null;
  renamingSessionId: string | null;
  newSessionTitle: string;
  setNewSessionTitle: (title: string) => void;
  onSelectSession: (session: ChatSession) => void;
  onTogglePinSession: (id: string) => void;
  setActiveSessionMenuId: (id: string | null) => void;
  setRenamingSessionId: (id: string | null) => void;
  handleSaveRename: (id: string) => void;
  handleDeleteSession: (id: string) => void;

  // User & Gateway
  gatewayUsername: string;
  isOnline: boolean;
  isTunnelConfigured?: boolean;
  isUserMenuOpen: boolean;
  setIsUserMenuOpen: (open: boolean | ((prev: boolean) => boolean)) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isDrawerOpen,
  onToggleDrawer,
  onNewChat,
  onOpenSearch,
  onOpenSettings,
  onOpenUsage,
  onLogout,
  sessions,
  currentSessionId,
  pinnedSessionIds,
  activeSessionMenuId,
  renamingSessionId,
  newSessionTitle,
  setNewSessionTitle,
  onSelectSession,
  onTogglePinSession,
  setActiveSessionMenuId,
  setRenamingSessionId,
  handleSaveRename,
  handleDeleteSession,
  gatewayUsername,
  isOnline,
  isTunnelConfigured = false,
  isUserMenuOpen,
  setIsUserMenuOpen,
}) => {
  const userMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setIsUserMenuOpen(false);
      }
    };
    if (isUserMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isUserMenuOpen, setIsUserMenuOpen]);

  return (
    <aside
      id="pipelineDrawer"
      className={`fixed inset-y-0 left-0 flex flex-col transition-all duration-300 ease-in-out ${
        isDrawerOpen
          ? 'w-[min(80vw,18rem)] z-50 shadow-2xl bg-white/98 dark:bg-[#12141d]/98 border-r border-slate-200 dark:border-white/10 backdrop-blur-2xl translate-x-0'
          : 'hidden sm:flex w-0 sm:w-16 z-30 bg-transparent border-r-0 shadow-none'
      }`}
      data-purpose="pipeline-sidebar-drawer"
    >
      <div className="flex flex-col pb-3.5 h-full space-y-3 select-none">
        {/* Row 1: Expand/Collapse Arrow Button */}
        <div className="h-14 sm:h-16 flex items-center shrink-0">
          <div className="w-14 sm:w-16 flex items-center justify-center shrink-0">
            <button
              id="sidebarToggleBtn"
              type="button"
              aria-label={isDrawerOpen ? 'Collapse menu' : 'Expand menu'}
              onClick={onToggleDrawer}
              className="w-10 h-10 rounded-xl flex items-center justify-center text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-white dark:hover:bg-white/10 transition-colors cursor-pointer active:scale-95"
            >
              <svg
                className={`w-5 h-5 transition-transform duration-200 ${isDrawerOpen ? 'rotate-180' : 'rotate-0'}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Row 2: Chat feature - New Chat button */}
        <NewChatButton isDrawerOpen={isDrawerOpen} onClick={onNewChat} />

        {/* Row 3: Search feature - Search button */}
        <SidebarSearchButton isDrawerOpen={isDrawerOpen} onClick={onOpenSearch} />

        {/* Middle Section: Chat sessions feature */}
        <div
          className={`flex-1 flex flex-col min-h-0 overflow-hidden transition-opacity duration-200 ${
            isDrawerOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
          }`}
        >
          {/* Recents Section Header */}
          <div className="px-3 pt-1 pb-1.5 flex items-center justify-between shrink-0">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
              Recents
            </span>
            <span className="text-[10px] text-slate-400 dark:text-slate-500 font-medium">
              ({sessions.length})
            </span>
          </div>

          {/* List of Chat Sessions */}
          <ChatSessionList
            displayedSessions={sessions}
            currentSessionId={currentSessionId}
            pinnedSessionIds={pinnedSessionIds}
            activeSessionMenuId={activeSessionMenuId}
            renamingSessionId={renamingSessionId}
            newSessionTitle={newSessionTitle}
            setNewSessionTitle={setNewSessionTitle}
            onSelectSession={onSelectSession}
            onTogglePinSession={onTogglePinSession}
            setActiveSessionMenuId={setActiveSessionMenuId}
            setRenamingSessionId={setRenamingSessionId}
            handleSaveRename={handleSaveRename}
            handleDeleteSession={handleDeleteSession}
          />
        </div>

        {/* Bottom Row: Settings feature - User / Gateway Status Button & Popover */}
        <div
          className="pt-2 border-t border-slate-200/80 dark:border-white/[0.06] shrink-0 relative"
          ref={userMenuRef}
        >
          {isTunnelConfigured && (
            <UserProfileMenu
              isOpen={isUserMenuOpen}
              onClose={() => setIsUserMenuOpen(false)}
              onOpenUsage={onOpenUsage}
              onLogout={onLogout}
              onOpenSettings={onOpenSettings}
            />
          )}

          <SidebarSettingsTrigger
            gatewayUsername={gatewayUsername}
            isOnline={isOnline}
            isTunnelConfigured={isTunnelConfigured}
            isDrawerOpen={isDrawerOpen}
            isUserMenuOpen={isUserMenuOpen}
            onToggleUserMenu={() => setIsUserMenuOpen((prev) => !prev)}
            onOpenSettings={onOpenSettings}
          />
        </div>
      </div>
    </aside>
  );
};
