import React from 'react';
import { ChatSession } from '../../../types';
import { ChatSessionItem } from './ChatSessionItem';

export interface ChatSessionListProps {
  displayedSessions: ChatSession[];
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
}

export const ChatSessionList: React.FC<ChatSessionListProps> = ({
  displayedSessions,
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
}) => {
  return (
    <div
      className="flex-1 overflow-y-auto px-2 space-y-0.5"
      style={{ scrollbarWidth: 'thin' }}
    >
      {displayedSessions.map((s) => (
        <ChatSessionItem
          key={s.id}
          session={s}
          isSelected={s.id === currentSessionId}
          isMenuOpen={activeSessionMenuId === s.id}
          isRenaming={renamingSessionId === s.id}
          isPinned={pinnedSessionIds.includes(s.id)}
          newSessionTitle={newSessionTitle}
          setNewSessionTitle={setNewSessionTitle}
          onSelect={onSelectSession}
          onTogglePin={onTogglePinSession}
          onToggleMenu={(id) => setActiveSessionMenuId(activeSessionMenuId === id ? null : id)}
          onStartRename={(sess) => {
            setRenamingSessionId(sess.id);
            setNewSessionTitle(sess.title);
            setActiveSessionMenuId(null);
          }}
          onSaveRename={handleSaveRename}
          onCancelRename={() => setRenamingSessionId(null)}
          onDeleteSession={handleDeleteSession}
        />
      ))}

      {displayedSessions.length === 0 && (
        <div className="text-center py-6 text-xs text-slate-400 dark:text-slate-500">
          No chats yet.
        </div>
      )}
    </div>
  );
};
