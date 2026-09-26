import type React from 'react';
import { useState } from 'react';
import type { ChatSession } from '../../../types';
import { formatSessionDate } from '../../../utils/uuid';

export interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  sessions: ChatSession[];
  currentSessionId: string | null;
  pinnedSessionIds: string[];
  sourceDocs?: any[];
  activeSessionMenuId?: string | null;
  setActiveSessionMenuId?: (id: string | null) => void;
  renamingSessionId?: string | null;
  setRenamingSessionId?: (id: string | null) => void;
  newSessionTitle?: string;
  setNewSessionTitle?: (title: string) => void;
  handleSaveRename?: (id: string) => void;
  handleTogglePinSession?: (id: string) => void;
  handleDeleteSession?: (id: string) => void;
  onSelectSession: (session: ChatSession) => void;
  onNewChat?: () => void;
}

export const SearchModal: React.FC<SearchModalProps> = ({
  isOpen,
  onClose,
  sessions,
  currentSessionId,
  pinnedSessionIds,
  sourceDocs = [],
  activeSessionMenuId = null,
  setActiveSessionMenuId,
  renamingSessionId = null,
  setRenamingSessionId,
  newSessionTitle = '',
  setNewSessionTitle,
  handleSaveRename,
  handleTogglePinSession,
  handleDeleteSession,
  onSelectSession,
  onNewChat,
}) => {
  const [searchFilter, setSearchFilter] = useState('');
  const [activeSearchIndex, setActiveSearchIndex] = useState(-1);

  if (!isOpen) return null;

  const filteredSessions = sessions.filter((s) =>
    s.title.toLowerCase().includes(searchFilter.toLowerCase())
  );

  return (
    <div
      id="searchModalBackdrop"
      className="fixed inset-0 z-[110] flex items-start justify-center pt-[clamp(3.5rem,8vh,5rem)] p-[clamp(0.5rem,2vw,1rem)] bg-black/60 backdrop-blur-sm animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        id="searchModalDialog"
        role="dialog"
        aria-modal="true"
        aria-label="Search all chats"
        onClick={(e) => {
          e.stopPropagation();
          if (setActiveSessionMenuId) setActiveSessionMenuId(null);
        }}
        className="w-[min(94vw,42rem)] max-h-[85dvh] bg-white dark:bg-[#181b26] text-slate-900 dark:text-slate-100 border border-slate-300 dark:border-white/15 rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-150 select-none"
      >
        {/* Search Input Header */}
        <div className="p-[clamp(0.625rem,2vw,0.875rem)] border-b border-slate-200 dark:border-white/10 flex items-center gap-2.5 bg-slate-50/80 dark:bg-white/[0.02]">
          <svg
            className="w-4 h-4 text-slate-400 dark:text-slate-500 shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            type="text"
            autoFocus
            value={searchFilter}
            role="combobox"
            aria-label="Search all chats"
            aria-autocomplete="list"
            aria-expanded={true}
            aria-controls="search-chats-listbox"
            aria-activedescendant={
              activeSearchIndex >= 0 ? `search-chat-item-${activeSearchIndex}` : undefined
            }
            onChange={(e) => {
              setSearchFilter(e.target.value);
              setActiveSearchIndex(-1);
            }}
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown') {
                if (filteredSessions.length > 0) {
                  e.preventDefault();
                  setActiveSearchIndex((prev) =>
                    prev < filteredSessions.length - 1 ? prev + 1 : 0
                  );
                }
              } else if (e.key === 'ArrowUp') {
                if (filteredSessions.length > 0) {
                  e.preventDefault();
                  setActiveSearchIndex((prev) =>
                    prev > 0 ? prev - 1 : filteredSessions.length - 1
                  );
                }
              } else if (e.key === 'Enter') {
                if (activeSearchIndex >= 0 && activeSearchIndex < filteredSessions.length) {
                  e.preventDefault();
                  onSelectSession(filteredSessions[activeSearchIndex]);
                  onClose();
                  setActiveSearchIndex(-1);
                }
              } else if (e.key === 'Escape') {
                e.preventDefault();
                onClose();
                setActiveSearchIndex(-1);
              }
            }}
            placeholder="Search all chats..."
            className="flex-1 bg-transparent border-0 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-0 p-0"
          />
          {searchFilter && (
            <button
              type="button"
              onClick={() => {
                setSearchFilter('');
                setActiveSearchIndex(-1);
              }}
              className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-white rounded-md cursor-pointer"
              title="Clear search"
              aria-label="Clear search query"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          )}
          <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono bg-slate-200/80 dark:bg-white/10 text-slate-500 dark:text-slate-400 rounded border border-slate-300 dark:border-white/10">
            Esc
          </kbd>
          <button
            type="button"
            onClick={() => {
              onClose();
              if (setActiveSessionMenuId) setActiveSessionMenuId(null);
              setActiveSearchIndex(-1);
            }}
            className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-200/60 dark:hover:bg-white/10 rounded-md transition-colors cursor-pointer ml-1"
            aria-label="Close popup"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* List of Chats */}
        <div
          id="search-chats-listbox"
          role="listbox"
          aria-label="Chat Sessions"
          className="flex-1 overflow-y-auto p-2 pb-8 space-y-1"
          style={{ scrollbarWidth: 'thin' }}
        >
          <div className="px-2.5 py-1.5 text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider flex items-center justify-between">
            <span>All Chats</span>
            <span>{sessions.length} total</span>
          </div>
          {filteredSessions.map((s, sIdx) => {
            const isSelected = s.id === currentSessionId;
            const isHighlighted = activeSearchIndex === sIdx;
            const isPinned = pinnedSessionIds.includes(s.id);
            const isMenuOpen = activeSessionMenuId === s.id;
            const isRenaming = renamingSessionId === s.id;
            const dataCount = isSelected
              ? sourceDocs.filter((d: any) => d.selected).length
              : s.sources && s.sources.length > 0
                ? s.sources.filter((src: any) => src.selected !== false).length
                : (s.selectedSourceIds?.length ?? (s.id === 'session-xyma-faculty' ? 1 : 0));

            return (
              <div
                key={s.id}
                id={`search-chat-item-${sIdx}`}
                role="option"
                aria-selected={isHighlighted || isSelected}
                tabIndex={0}
                onClick={() => {
                  if (isRenaming) return;
                  onSelectSession(s);
                  onClose();
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    if (isRenaming) return;
                    e.preventDefault();
                    onSelectSession(s);
                    onClose();
                  }
                }}
                className={`group relative w-full text-left px-3.5 py-2.5 rounded-xl transition-all flex items-center justify-between gap-3 cursor-pointer border ${
                  isHighlighted
                    ? 'bg-indigo-50 border-indigo-300 text-indigo-950 font-semibold shadow-xs dark:bg-indigo-950/60 dark:border-indigo-700/60 dark:text-white ring-1 ring-indigo-400/40'
                    : isSelected
                      ? 'bg-slate-200/90 border-slate-300/90 text-slate-950 font-semibold shadow-xs dark:bg-white/10 dark:border-white/15 dark:text-white'
                      : 'bg-transparent hover:bg-slate-100/90 border-transparent dark:hover:bg-white/[0.06] text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0 flex-1">
                  {isPinned ? (
                    <svg
                      className="w-3.5 h-3.5 text-indigo-600 dark:text-[#a8c7fa] shrink-0"
                      fill="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M16 12V4H8v8l-2 3v1h12v-1l-2-3z"
                      />
                    </svg>
                  ) : (
                    <svg
                      className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500 shrink-0"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="1.8"
                        d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                      />
                    </svg>
                  )}
                  {isRenaming && setNewSessionTitle && handleSaveRename ? (
                    <input
                      type="text"
                      autoFocus
                      value={newSessionTitle}
                      onChange={(e) => setNewSessionTitle(e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          handleSaveRename(s.id);
                        } else if (e.key === 'Escape' && setRenamingSessionId) {
                          setRenamingSessionId(null);
                        }
                      }}
                      onBlur={() => handleSaveRename(s.id)}
                      className="w-full text-xs font-medium px-2 py-0.5 rounded bg-white dark:bg-slate-900 border border-indigo-500 text-slate-900 dark:text-slate-100 focus:outline-none shadow-xs"
                    />
                  ) : (
                    <span
                      className={`text-xs truncate ${isSelected ? 'font-semibold text-slate-950 dark:text-white' : 'font-medium'}`}
                    >
                      {s.title}
                    </span>
                  )}
                </div>

                {/* Right side: Drawer icon with count + Date + Three dots */}
                <div className="flex items-center gap-2 shrink-0">
                  <div
                    className="flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-slate-100 dark:bg-white/[0.06] border border-slate-200/80 dark:border-white/10 text-slate-600 dark:text-slate-400"
                    title={`${dataCount} source data added`}
                  >
                    <svg
                      className="w-3 h-3 text-slate-500 dark:text-slate-400 shrink-0"
                      fill="none"
                      stroke="currentColor"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="1.75"
                      viewBox="0 0 24 24"
                    >
                      <path d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                    </svg>
                    <span className="text-[10px] font-semibold tabular-nums text-slate-700 dark:text-slate-300">
                      {dataCount}
                    </span>
                  </div>

                  <span className="text-[11px] text-slate-400 dark:text-slate-500 whitespace-nowrap min-w-[65px] text-right">
                    {s.timestamp || formatSessionDate(s.updated_at || s.created_at)}
                  </span>

                  {setActiveSessionMenuId && (
                    <div className="relative" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        onClick={() => setActiveSessionMenuId(isMenuOpen ? null : s.id)}
                        className={`p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/70 dark:hover:text-slate-200 dark:hover:bg-white/10 transition-all cursor-pointer ${
                          isMenuOpen
                            ? 'opacity-100 bg-slate-200/70 dark:bg-white/10 text-slate-700 dark:text-slate-200'
                            : 'opacity-70 sm:opacity-0 sm:group-hover:opacity-100 hover:opacity-100'
                        }`}
                        aria-label="Chat options"
                      >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                          <circle cx="12" cy="5" r="1.75" />
                          <circle cx="12" cy="12" r="1.75" />
                          <circle cx="12" cy="19" r="1.75" />
                        </svg>
                      </button>

                      {isMenuOpen && (
                        <div className="absolute right-0 top-full mt-1 w-36 bg-white dark:bg-[#181b26] border border-slate-200 dark:border-white/10 rounded-xl shadow-xl py-1 z-50 animate-in fade-in zoom-in-95 duration-100 backdrop-blur-xl">
                          {handleTogglePinSession && (
                            <button
                              type="button"
                              onClick={() => {
                                handleTogglePinSession(s.id);
                                setActiveSessionMenuId(null);
                              }}
                              className="w-full text-left px-3 py-1.5 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 flex items-center gap-2 transition-colors cursor-pointer"
                            >
                              <svg
                                className="w-3.5 h-3.5 text-slate-400"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2"
                                viewBox="0 0 24 24"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  d="M16 12V4H8v8l-2 3v1h12v-1l-2-3z"
                                />
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 16v5" />
                              </svg>
                              <span>{isPinned ? 'Unpin' : 'Pin to top'}</span>
                            </button>
                          )}

                          {setRenamingSessionId && setNewSessionTitle && (
                            <button
                              type="button"
                              onClick={() => {
                                setRenamingSessionId(s.id);
                                setNewSessionTitle(s.title);
                                setActiveSessionMenuId(null);
                              }}
                              className="w-full text-left px-3 py-1.5 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 flex items-center gap-2 transition-colors cursor-pointer"
                            >
                              <svg
                                className="w-3.5 h-3.5 text-slate-400"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth="2"
                                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                                />
                              </svg>
                              <span>Rename</span>
                            </button>
                          )}

                          {handleDeleteSession && (
                            <button
                              type="button"
                              onClick={() => {
                                handleDeleteSession(s.id);
                                setActiveSessionMenuId(null);
                              }}
                              className="w-full text-left px-3 py-1.5 text-xs text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-500/10 flex items-center gap-2 transition-colors cursor-pointer"
                            >
                              <svg
                                className="w-3.5 h-3.5"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth="2"
                                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                                />
                              </svg>
                              <span>Delete</span>
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          {filteredSessions.length === 0 && (
            <div className="text-center py-8 text-xs text-slate-400 dark:text-slate-500">
              No chats found matching &ldquo;{searchFilter}&rdquo;
            </div>
          )}
        </div>

        {/* Footer with New Chat Action */}
        <div className="p-2.5 border-t border-slate-200 dark:border-white/10 bg-slate-50/70 dark:bg-white/[0.02] flex items-center justify-between">
          <button
            type="button"
            onClick={() => {
              if (onNewChat) onNewChat();
              onClose();
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-white/10 transition-all cursor-pointer"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                d="M12 4v16m8-8H4"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
              />
            </svg>
            <span>Create New Chat</span>
          </button>
          <span className="text-[11px] text-slate-400 dark:text-slate-500">
            Click any chat to open
          </span>
        </div>
      </div>
    </div>
  );
};
