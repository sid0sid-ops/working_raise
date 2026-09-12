import React from 'react';
import { ChatSession } from '../../../types';
import { formatSessionDate } from '../../../utils/uuid';

export interface ChatSessionItemProps {
  session: ChatSession;
  isSelected: boolean;
  isMenuOpen: boolean;
  isRenaming: boolean;
  isPinned: boolean;
  newSessionTitle: string;
  setNewSessionTitle: (title: string) => void;
  onSelect: (session: ChatSession) => void;
  onTogglePin: (id: string) => void;
  onToggleMenu: (id: string) => void;
  onStartRename: (session: ChatSession) => void;
  onSaveRename: (id: string) => void;
  onCancelRename: () => void;
  onDeleteSession: (id: string) => void;
}

export const ChatSessionItem: React.FC<ChatSessionItemProps> = ({
  session,
  isSelected,
  isMenuOpen,
  isRenaming,
  isPinned,
  newSessionTitle,
  setNewSessionTitle,
  onSelect,
  onTogglePin,
  onToggleMenu,
  onStartRename,
  onSaveRename,
  onCancelRename,
  onDeleteSession,
}) => {

  return (
    <div
      onClick={() => onSelect(session)}
      className={`group relative px-3 py-2 rounded-xl transition-all cursor-pointer flex items-center justify-between gap-2 border ${
        isSelected
          ? 'bg-slate-200/90 border-slate-300/90 text-slate-950 font-semibold shadow-xs dark:bg-white/10 dark:border-white/15 dark:text-white'
          : 'bg-transparent hover:bg-slate-100/90 border-transparent dark:hover:bg-white/[0.06] text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
      }`}
    >
      <div className="flex-1 min-w-0 pr-1">
        <div className="flex items-center gap-2">
          {isPinned && (
            <svg className="w-3.5 h-3.5 text-indigo-600 dark:text-[#a8c7fa] shrink-0" fill="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M16 12V4H8v8l-2 3v1h12v-1l-2-3z" />
            </svg>
          )}

          {isRenaming ? (
            <input
              type="text"
              autoFocus
              value={newSessionTitle}
              onChange={(e) => setNewSessionTitle(e.target.value)}
              onClick={(e) => e.stopPropagation()}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  onSaveRename(session.id);
                } else if (e.key === 'Escape') {
                  onCancelRename();
                }
              }}
              onBlur={() => onSaveRename(session.id)}
              className="w-full text-xs font-medium px-1.5 py-0.5 rounded bg-white dark:bg-slate-900 border border-indigo-500 text-slate-900 dark:text-slate-100 focus:outline-none shadow-xs"
            />
          ) : (
            <div className="min-w-0 flex-1">
              <p
                className={`text-xs truncate ${
                  isSelected ? 'font-semibold text-slate-950 dark:text-white' : 'font-normal'
                }`}
                title={session.title}
              >
                {session.title}
              </p>
              <div className="flex items-center gap-1.5 text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">
                <span>{session.timestamp || formatSessionDate(session.updated_at || session.created_at)}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right side actions: Pin button + Three-dots menu button */}
      <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
        {/* Pin button */}
        <button
          type="button"
          onClick={() => onTogglePin(session.id)}
          title={isPinned ? 'Unpin' : 'Pin'}
          aria-label={isPinned ? 'Unpin' : 'Pin'}
          className={`p-1.5 rounded-md transition-all cursor-pointer ${
            isPinned
              ? 'opacity-100 text-indigo-600 dark:text-[#a8c7fa] bg-indigo-50 dark:bg-indigo-500/15'
              : 'text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 dark:hover:text-slate-200 dark:hover:bg-white/10 opacity-0 group-hover:opacity-100'
          }`}
        >
          <svg
            className="w-3.5 h-3.5"
            fill={isPinned ? 'currentColor' : 'none'}
            stroke="currentColor"
            strokeWidth="2"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M16 12V4H8v8l-2 3v1h12v-1l-2-3z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 16v5" />
          </svg>
        </button>

        {/* Three-dots menu button */}
        <div className="relative">
          <button
            type="button"
            onClick={() => onToggleMenu(session.id)}
            className={`p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 dark:hover:text-slate-200 dark:hover:bg-white/10 rounded-md transition-all cursor-pointer ${
              isMenuOpen
                ? 'opacity-100 bg-slate-200/60 dark:bg-white/10 text-slate-700 dark:text-slate-200'
                : 'opacity-70 hover:opacity-100 sm:opacity-0 sm:group-hover:opacity-100'
            }`}
            aria-label="Chat options"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <circle cx="12" cy="5" r="1.75" />
              <circle cx="12" cy="12" r="1.75" />
              <circle cx="12" cy="19" r="1.75" />
            </svg>
          </button>

          {/* Dropdown Action Box */}
          {isMenuOpen && (
            <div className="absolute right-0 top-full mt-1 w-36 bg-white dark:bg-[#181b26] border border-slate-200 dark:border-white/10 rounded-xl shadow-xl py-1 z-50 animate-in fade-in zoom-in-95 duration-100 backdrop-blur-xl">
              <button
                type="button"
                onClick={() => onStartRename(session)}
                className="w-full text-left px-3 py-1.5 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 flex items-center gap-2 transition-colors cursor-pointer"
              >
                <svg className="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                <span>Rename</span>
              </button>

              <button
                type="button"
                onClick={() => onDeleteSession(session.id)}
                className="w-full text-left px-3 py-1.5 text-xs text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-500/10 flex items-center gap-2 transition-colors cursor-pointer"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                <span>Delete</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
