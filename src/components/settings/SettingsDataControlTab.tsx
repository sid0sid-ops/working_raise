import type React from 'react';
import { useEffect, useState } from 'react';
import type { ChatSession } from '../../types';

export interface SharedLinkItem {
  id: string;
  title: string;
  url: string;
  createdAt: string;
  views: number;
}

export interface SettingsDataControlTabProps {
  sessions: ChatSession[];
  onSessionsChange: (updatedSessions: ChatSession[]) => void;
  onDeleteAllChats: () => void;
  onCloseSettings?: () => void;
}

export const SettingsDataControlTab: React.FC<SettingsDataControlTabProps> = ({
  sessions,
  onSessionsChange,
  onDeleteAllChats,
}) => {
  // Modal states for the 5 actions
  const [isSharedLinksOpen, setIsSharedLinksOpen] = useState(false);
  const [isArchiveChatsOpen, setIsArchiveChatsOpen] = useState(false);
  const [isArchiveAllOpen, setIsArchiveAllOpen] = useState(false);
  const [isDeleteAllOpen, setIsDeleteAllOpen] = useState(false);
  const [isExportOpen, setIsExportOpen] = useState(false);

  // Shared links state
  const [sharedLinks, setSharedLinks] = useState<SharedLinkItem[]>(() => {
    try {
      const saved = localStorage.getItem('raise_shared_links');
      if (saved) {
        const parsed = JSON.parse(saved) as unknown[];
        if (Array.isArray(parsed)) {
          // Cleanse legacy hardcoded mock items if any exist in localStorage
          return (parsed as SharedLinkItem[]).filter(
            (item: SharedLinkItem) =>
              item.id !== 'share-1' &&
              item.id !== 'share-2' &&
              !item.url?.includes('raise.internal')
          );
        }
      }
    } catch {}
    return [];
  });

  const saveSharedLinks = (links: SharedLinkItem[]) => {
    setSharedLinks(links);
    try {
      localStorage.setItem('raise_shared_links', JSON.stringify(links));
    } catch {}
  };

  // Archived chats state
  const [archivedSessions, setArchivedSessions] = useState<ChatSession[]>(() => {
    try {
      const saved = localStorage.getItem('raise_archived_sessions');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) return parsed as ChatSession[];
      }
    } catch {}
    return [];
  });

  const saveArchivedSessions = (archived: ChatSession[]) => {
    setArchivedSessions(archived);
    try {
      localStorage.setItem('raise_archived_sessions', JSON.stringify(archived));
    } catch {}
  };

  // Toast / feedback notifications
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [copiedLinkId, setCopiedLinkId] = useState<string | null>(null);
  const [exportFormat, setExportFormat] = useState<'json' | 'markdown'>('json');

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 2500);
  };

  // ESC key listener to close any open sub-popup
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (isDeleteAllOpen) setIsDeleteAllOpen(false);
        else if (isArchiveAllOpen) setIsArchiveAllOpen(false);
        else if (isArchiveChatsOpen) setIsArchiveChatsOpen(false);
        else if (isSharedLinksOpen) setIsSharedLinksOpen(false);
        else if (isExportOpen) setIsExportOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isDeleteAllOpen, isArchiveAllOpen, isArchiveChatsOpen, isSharedLinksOpen, isExportOpen]);

  // Handler: Copy shared link
  const handleCopyLink = (item: SharedLinkItem) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(item.url).then(() => {
        setCopiedLinkId(item.id);
        showToast('Link copied to clipboard');
        setTimeout(() => setCopiedLinkId(null), 2000);
      });
    }
  };

  // Handler: Revoke / Delete shared link
  const handleRevokeLink = (id: string) => {
    const updated = sharedLinks.filter((l) => l.id !== id);
    saveSharedLinks(updated);
    showToast('Shared link revoked');
  };

  // Handler: Restore archived session
  const handleRestoreSession = (sessionToRestore: ChatSession) => {
    const updatedArchived = archivedSessions.filter((s) => s.id !== sessionToRestore.id);
    saveArchivedSessions(updatedArchived);

    const updatedActive = [sessionToRestore, ...sessions];
    onSessionsChange(updatedActive);

    showToast(`Restored "${sessionToRestore.title}" to active chats`);
  };

  // Handler: Delete permanently from archive
  const handleDeleteArchivedPermanently = (sessionId: string) => {
    const updated = archivedSessions.filter((s) => s.id !== sessionId);
    saveArchivedSessions(updated);
    showToast('Session permanently deleted from archive');
  };

  // Handler: Archive all active chats
  const handleConfirmArchiveAll = () => {
    if (sessions.length === 0) {
      setIsArchiveAllOpen(false);
      showToast('No active chats to archive');
      return;
    }

    const updatedArchived = [...sessions, ...archivedSessions];
    saveArchivedSessions(updatedArchived);

    // Clear active sessions
    onSessionsChange([]);
    onDeleteAllChats(); // Resets active conversation
    setIsArchiveAllOpen(false);
    showToast(`Archived ${sessions.length} chat session(s)`);
  };

  // Handler: Delete all chats permanently
  const handleConfirmDeleteAll = () => {
    onDeleteAllChats();
    onSessionsChange([]);

    setIsDeleteAllOpen(false);
    showToast('All chat conversations permanently deleted');
  };

  // Handler: Export data to downloadable file
  const handlePerformExport = () => {
    const exportPayload = {
      version: '1.0.0',
      exportedAt: new Date().toISOString(),
      activeSessions: sessions,
      archivedSessions: archivedSessions,
      sharedLinks: sharedLinks,
      settings: {
        theme: localStorage.getItem('raise_theme_mode') || 'dark',
        gatewayUrl: localStorage.getItem('raise_gateway_url') || '',
        voice: localStorage.getItem('raise_preferred_voice') || '',
        gridConfig: localStorage.getItem('raise_grid_config')
          ? JSON.parse(localStorage.getItem('raise_grid_config')!)
          : null,
      },
    };

    let blob: Blob;
    let filename: string;

    if (exportFormat === 'json') {
      blob = new Blob([JSON.stringify(exportPayload, null, 2)], { type: 'application/json' });
      filename = `raise-export-${new Date().toISOString().split('T')[0]}.json`;
    } else {
      let md = `# RAISE Chat Conversations Export\nExported: ${new Date().toLocaleString()}\n\n`;
      sessions.forEach((s, idx) => {
        md += `## ${idx + 1}. ${s.title}\n*Timestamp: ${s.timestamp}*\n\n`;
        s.messages.forEach((m) => {
          md += `### ${m.role === 'user' ? 'User' : 'RAISE Assistant'}\n${m.text}\n\n`;
        });
        md += `---\n\n`;
      });
      blob = new Blob([md], { type: 'text/markdown' });
      filename = `raise-transcripts-${new Date().toISOString().split('T')[0]}.md`;
    }

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    setIsExportOpen(false);
    showToast(`Exported ${sessions.length} conversations (${exportFormat.toUpperCase()})`);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Toast Alert */}
      {toastMessage && (
        <div className="fixed top-5 left-1/2 -translate-x-1/2 z-[150] pointer-events-none animate-in fade-in zoom-in-95 duration-150">
          <div className="px-4 py-2 rounded-xl bg-white/95 dark:bg-[#181a20]/95 text-slate-900 dark:text-white text-xs font-medium shadow-2xl backdrop-blur-md flex items-center gap-2 border border-slate-200/90 dark:border-white/15">
            <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
            <span>{toastMessage}</span>
          </div>
        </div>
      )}

      {/* Header section */}
      <div>
        <h3 className="text-base font-semibold text-slate-900 dark:text-white">Data Control</h3>
        <p className="text-xs text-slate-500 dark:text-[#a8a8a8] mt-1">
          Manage your shared links, archived chats, data retention, export options, and conversation
          history.
        </p>
      </div>

      {/* 5 Data Control Options */}
      <div className="divide-y divide-slate-200/80 dark:divide-white/10 rounded-2xl border border-slate-200/80 dark:border-white/10 bg-slate-50/50 dark:bg-white/[0.02] overflow-hidden">
        {/* 1. Shared links */}
        <div className="p-3.5 sm:p-4.5 flex flex-row items-center justify-between gap-3 hover:bg-slate-50 dark:hover:bg-white/[0.03] transition-colors">
          <div className="space-y-0.5 min-w-0">
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-semibold text-slate-900 dark:text-white">Shared links</h4>
              <span className="px-2 py-0.5 text-[10px] font-medium rounded-full bg-slate-200/70 dark:bg-white/10 text-slate-600 dark:text-slate-300">
                {sharedLinks.length} active
              </span>
            </div>
            <p className="hidden sm:block text-xs text-slate-500 dark:text-[#a8a8a8]">
              Manage public links created to share specific conversation threads with collaborators.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsSharedLinksOpen(true)}
            className="px-3.5 sm:px-4 py-1.5 sm:py-2 rounded-xl text-xs font-semibold bg-white dark:bg-[#282a2c] hover:bg-slate-100 dark:hover:bg-[#34373a] text-slate-800 dark:text-slate-100 border border-slate-200/90 dark:border-white/10 transition-all shadow-2xs active:scale-98 cursor-pointer shrink-0"
          >
            Manage
          </button>
        </div>

        {/* 2. Archive chats */}
        <div className="p-3.5 sm:p-4.5 flex flex-row items-center justify-between gap-3 hover:bg-slate-50 dark:hover:bg-white/[0.03] transition-colors">
          <div className="space-y-0.5 min-w-0">
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
                Archive chats
              </h4>
              <span className="px-2 py-0.5 text-[10px] font-medium rounded-full bg-slate-200/70 dark:bg-white/10 text-slate-600 dark:text-slate-300">
                {archivedSessions.length} archived
              </span>
            </div>
            <p className="hidden sm:block text-xs text-slate-500 dark:text-[#a8a8a8]">
              View and restore conversations you have previously moved to your archive.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsArchiveChatsOpen(true)}
            className="px-3.5 sm:px-4 py-1.5 sm:py-2 rounded-xl text-xs font-semibold bg-white dark:bg-[#282a2c] hover:bg-slate-100 dark:hover:bg-[#34373a] text-slate-800 dark:text-slate-100 border border-slate-200/90 dark:border-white/10 transition-all shadow-2xs active:scale-98 cursor-pointer shrink-0"
          >
            Manage
          </button>
        </div>

        {/* 3. Archive all chats */}
        <div className="p-3.5 sm:p-4.5 flex flex-row items-center justify-between gap-3 hover:bg-slate-50 dark:hover:bg-white/[0.03] transition-colors">
          <div className="space-y-0.5 min-w-0">
            <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
              Archive all chats
            </h4>
            <p className="hidden sm:block text-xs text-slate-500 dark:text-[#a8a8a8]">
              Move all active chat conversations to your archive to clean up your recents sidebar.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsArchiveAllOpen(true)}
            className="px-3.5 sm:px-4 py-1.5 sm:py-2 rounded-xl text-xs font-semibold bg-white dark:bg-[#282a2c] hover:bg-slate-100 dark:hover:bg-[#34373a] text-slate-800 dark:text-slate-100 border border-slate-200/90 dark:border-white/10 transition-all shadow-2xs active:scale-98 cursor-pointer shrink-0"
          >
            Archive all
          </button>
        </div>

        {/* 4. Delete all chats */}
        <div className="p-3.5 sm:p-4.5 flex flex-row items-center justify-between gap-3 hover:bg-rose-50/40 dark:hover:bg-rose-500/5 transition-colors">
          <div className="space-y-0.5 min-w-0">
            <h4 className="text-sm font-semibold text-rose-600 dark:text-rose-400">
              Delete all chats
            </h4>
            <p className="hidden sm:block text-xs text-slate-500 dark:text-[#a8a8a8]">
              Permanently erase all chat conversations, prompt histories, and source attachments
              from this browser.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsDeleteAllOpen(true)}
            className="px-3.5 sm:px-4 py-1.5 sm:py-2 rounded-xl text-xs font-semibold text-rose-600 hover:text-white dark:text-rose-400 dark:hover:text-white bg-rose-50 hover:bg-rose-600 dark:bg-rose-500/10 dark:hover:bg-rose-600 border border-rose-200 dark:border-rose-500/30 transition-all shadow-2xs active:scale-98 cursor-pointer shrink-0"
          >
            Delete all
          </button>
        </div>

        {/* 5. Export data */}
        <div className="p-3.5 sm:p-4.5 flex flex-row items-center justify-between gap-3 hover:bg-slate-50 dark:hover:bg-white/[0.03] transition-colors">
          <div className="space-y-0.5 min-w-0">
            <h4 className="text-sm font-semibold text-slate-900 dark:text-white">Export data</h4>
            <p className="hidden sm:block text-xs text-slate-500 dark:text-[#a8a8a8]">
              Download an export of your chats, library document manifests, and custom configuration
              settings.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsExportOpen(true)}
            className="px-3.5 sm:px-4 py-1.5 sm:py-2 rounded-xl text-xs font-semibold bg-white dark:bg-[#282a2c] hover:bg-slate-100 dark:hover:bg-[#34373a] text-slate-800 dark:text-slate-100 border border-slate-200/90 dark:border-white/10 transition-all shadow-2xs active:scale-98 cursor-pointer shrink-0"
          >
            Export
          </button>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          POPUP 1: SHARED LINKS MANAGE POPUP
         ───────────────────────────────────────────────────────────── */}
      {isSharedLinksOpen && (
        <div
          id="sharedLinksModalBackdrop"
          className="fixed inset-0 z-[130] flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150"
          onClick={(e) => {
            if (e.target === e.currentTarget) setIsSharedLinksOpen(false);
          }}
        >
          <div
            id="sharedLinksModalDialog"
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-lg bg-white dark:bg-[#181b26] border border-slate-200 dark:border-white/15 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh] animate-in zoom-in-95 duration-150 select-none"
          >
            {/* Header */}
            <div className="p-4 border-b border-slate-200/80 dark:border-white/10 flex items-center justify-between bg-slate-50/80 dark:bg-white/[0.02]">
              <div>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                  Shared Links
                </h3>
                <p className="text-xs text-slate-500 dark:text-[#a8a8a8]">
                  Anyone with these links can view the shared conversation thread.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsSharedLinksOpen(false)}
                className="p-1 rounded-md text-slate-400 hover:text-slate-700 dark:hover:text-white cursor-pointer"
              >
                ✕
              </button>
            </div>

            {/* Content List */}
            <div className="p-4 overflow-y-auto space-y-3 flex-1">
              {sharedLinks.length === 0 ? (
                <div className="text-center py-8 text-slate-500 text-xs">
                  No active shared links found.
                </div>
              ) : (
                sharedLinks.map((item) => (
                  <div
                    key={item.id}
                    className="p-3 rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50/70 dark:bg-white/[0.03] flex items-center justify-between gap-3"
                  >
                    <div className="min-w-0 space-y-1">
                      <h5 className="text-xs font-semibold text-slate-900 dark:text-white truncate">
                        {item.title}
                      </h5>
                      <div className="flex items-center gap-2 text-[11px] text-slate-500 dark:text-[#a8a8a8]">
                        <span className="font-mono truncate">{item.url}</span>
                        <span>•</span>
                        <span>{item.views} views</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        type="button"
                        onClick={() => handleCopyLink(item)}
                        className="px-2.5 py-1 text-[11px] font-medium rounded-lg bg-white dark:bg-[#282a2c] hover:bg-slate-100 dark:hover:bg-white/10 border border-slate-200 dark:border-white/10 text-slate-700 dark:text-slate-200 transition-colors cursor-pointer"
                      >
                        {copiedLinkId === item.id ? 'Copied!' : 'Copy'}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRevokeLink(item.id)}
                        className="p-1 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-lg transition-colors cursor-pointer"
                        title="Revoke link"
                      >
                        <svg
                          className="w-4 h-4"
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
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-slate-200/80 dark:border-white/10 bg-slate-50/50 dark:bg-white/[0.01] flex justify-end">
              <button
                type="button"
                onClick={() => setIsSharedLinksOpen(false)}
                className="px-4 py-1.5 rounded-xl text-xs font-semibold bg-slate-900 text-white dark:bg-white dark:text-slate-900 cursor-pointer"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          POPUP 2: ARCHIVE CHATS MANAGE POPUP
         ───────────────────────────────────────────────────────────── */}
      {isArchiveChatsOpen && (
        <div
          id="archiveChatsModalBackdrop"
          className="fixed inset-0 z-[130] flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150"
          onClick={(e) => {
            if (e.target === e.currentTarget) setIsArchiveChatsOpen(false);
          }}
        >
          <div
            id="archiveChatsModalDialog"
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-lg bg-white dark:bg-[#181b26] border border-slate-200 dark:border-white/15 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh] animate-in zoom-in-95 duration-150 select-none"
          >
            {/* Header */}
            <div className="p-4 border-b border-slate-200/80 dark:border-white/10 flex items-center justify-between bg-slate-50/80 dark:bg-white/[0.02]">
              <div>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                  Archived Chats
                </h3>
                <p className="text-xs text-slate-500 dark:text-[#a8a8a8]">
                  View or restore conversations that were moved to your archive.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsArchiveChatsOpen(false)}
                className="p-1 rounded-md text-slate-400 hover:text-slate-700 dark:hover:text-white cursor-pointer"
              >
                ✕
              </button>
            </div>

            {/* Content List */}
            <div className="p-4 overflow-y-auto space-y-3 flex-1">
              {archivedSessions.length === 0 ? (
                <div className="text-center py-10 space-y-2">
                  <div className="w-10 h-10 mx-auto rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="1.5"
                        d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
                      />
                    </svg>
                  </div>
                  <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                    No archived chats
                  </p>
                  <p className="text-[11px] text-slate-500 max-w-xs mx-auto">
                    When you archive chats, they will safely appear here instead of cluttering your
                    sidebar.
                  </p>
                </div>
              ) : (
                archivedSessions.map((session) => (
                  <div
                    key={session.id}
                    className="p-3 rounded-xl border border-slate-200/80 dark:border-white/10 bg-slate-50/70 dark:bg-white/[0.03] flex items-center justify-between gap-3"
                  >
                    <div className="min-w-0 space-y-0.5">
                      <h5 className="text-xs font-semibold text-slate-900 dark:text-white truncate">
                        {session.title}
                      </h5>
                      <div className="flex items-center gap-2 text-[11px] text-slate-500 dark:text-[#a8a8a8]">
                        <span>{session.messages?.length || 0} messages</span>
                        <span>•</span>
                        <span>{session.timestamp}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        type="button"
                        onClick={() => handleRestoreSession(session)}
                        className="px-2.5 py-1 text-[11px] font-medium rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white transition-colors cursor-pointer"
                      >
                        Restore
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteArchivedPermanently(session.id)}
                        className="p-1 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-lg transition-colors cursor-pointer"
                        title="Delete permanently"
                      >
                        <svg
                          className="w-4 h-4"
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
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-slate-200/80 dark:border-white/10 bg-slate-50/50 dark:bg-white/[0.01] flex justify-end">
              <button
                type="button"
                onClick={() => setIsArchiveChatsOpen(false)}
                className="px-4 py-1.5 rounded-xl text-xs font-semibold bg-slate-900 text-white dark:bg-white dark:text-slate-900 cursor-pointer"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          POPUP 3: ARCHIVE ALL CHATS CONFIRMATION POPUP
         ───────────────────────────────────────────────────────────── */}
      {isArchiveAllOpen && (
        <div
          id="archiveAllModalBackdrop"
          className="fixed inset-0 z-[130] flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150"
          onClick={(e) => {
            if (e.target === e.currentTarget) setIsArchiveAllOpen(false);
          }}
        >
          <div
            id="archiveAllModalDialog"
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md bg-white dark:bg-[#181b26] border border-slate-200 dark:border-white/15 rounded-2xl shadow-2xl p-5 select-none space-y-4 animate-in zoom-in-95 duration-150"
          >
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-500/15 text-indigo-600 dark:text-[#a8c7fa] flex items-center justify-center shrink-0">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
                  />
                </svg>
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                  Archive all chats?
                </h3>
                <p className="text-xs text-slate-500 dark:text-[#a8a8a8] leading-relaxed">
                  This will move all{' '}
                  <strong className="text-slate-900 dark:text-white">{sessions.length}</strong>{' '}
                  active conversations to your archive. You can access or restore them anytime under
                  Data controls &gt; Archive chats.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200/80 dark:border-white/10">
              <button
                type="button"
                onClick={() => setIsArchiveAllOpen(false)}
                className="px-3.5 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/10 rounded-xl transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmArchiveAll}
                className="px-4 py-1.5 text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl transition-colors cursor-pointer"
              >
                Archive all chats
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          POPUP 4: DELETE ALL CHATS CONFIRMATION POPUP
          (Clicking outside the popup closes the delete all popup)
         ───────────────────────────────────────────────────────────── */}
      {isDeleteAllOpen && (
        <div
          id="deleteAllModalBackdrop"
          className="fixed inset-0 z-[130] flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150"
          onClick={(e) => {
            // User requested: "clicking outside the popup close the delete all popup"
            if (e.target === e.currentTarget) {
              setIsDeleteAllOpen(false);
            }
          }}
        >
          <div
            id="deleteAllModalDialog"
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md bg-white dark:bg-[#181b26] border border-rose-200 dark:border-rose-500/30 rounded-2xl shadow-2xl p-5 select-none space-y-4 animate-in zoom-in-95 duration-150"
          >
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-rose-100 dark:bg-rose-500/20 text-rose-600 dark:text-rose-400 flex items-center justify-center shrink-0">
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
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Delete all chats?
                </h3>
                <p className="text-xs text-slate-500 dark:text-[#a8a8a8] leading-relaxed">
                  Are you sure you want to permanently delete all{' '}
                  <strong className="text-rose-600 dark:text-rose-400">{sessions.length}</strong>{' '}
                  chat conversations? All message history, questions, and attached documents in this
                  browser will be wiped. This action cannot be undone.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200/80 dark:border-white/10">
              <button
                type="button"
                onClick={() => setIsDeleteAllOpen(false)}
                className="px-3.5 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/10 rounded-xl transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmDeleteAll}
                className="px-4 py-1.5 text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white rounded-xl transition-colors cursor-pointer shadow-xs active:scale-95"
              >
                Delete all chats
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          POPUP 5: EXPORT DATA POPUP
         ───────────────────────────────────────────────────────────── */}
      {isExportOpen && (
        <div
          id="exportModalBackdrop"
          className="fixed inset-0 z-[130] flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150"
          onClick={(e) => {
            if (e.target === e.currentTarget) setIsExportOpen(false);
          }}
        >
          <div
            id="exportModalDialog"
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md bg-white dark:bg-[#181b26] border border-slate-200 dark:border-white/15 rounded-2xl shadow-2xl p-5 select-none space-y-4 animate-in zoom-in-95 duration-150"
          >
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-500/15 text-indigo-600 dark:text-[#a8c7fa] flex items-center justify-center shrink-0">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                  />
                </svg>
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                  Export data
                </h3>
                <p className="text-xs text-slate-500 dark:text-[#a8a8a8] leading-relaxed">
                  Export all your conversations, shared links, and settings for backup or analysis.
                </p>
              </div>
            </div>

            {/* Export Summary Cards */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-white/[0.03] border border-slate-200/80 dark:border-white/10">
                <span className="text-slate-500 dark:text-[#a8a8a8] text-[11px]">Active Chats</span>
                <p className="font-semibold text-slate-900 dark:text-white text-sm">
                  {sessions.length}
                </p>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-white/[0.03] border border-slate-200/80 dark:border-white/10">
                <span className="text-slate-500 dark:text-[#a8a8a8] text-[11px]">
                  Archived Chats
                </span>
                <p className="font-semibold text-slate-900 dark:text-white text-sm">
                  {archivedSessions.length}
                </p>
              </div>
            </div>

            {/* Format selection */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                Export Format
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setExportFormat('json')}
                  className={`p-2.5 rounded-xl text-left border transition-all cursor-pointer ${
                    exportFormat === 'json'
                      ? 'border-indigo-600 bg-indigo-50/50 dark:bg-indigo-500/10 text-indigo-700 dark:text-[#a8c7fa]'
                      : 'border-slate-200 dark:border-white/10 text-slate-700 dark:text-slate-300'
                  }`}
                >
                  <span className="text-xs font-semibold block">JSON Data</span>
                  <span className="text-[10px] text-slate-500 dark:text-[#a8a8a8]">
                    Complete structure
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => setExportFormat('markdown')}
                  className={`p-2.5 rounded-xl text-left border transition-all cursor-pointer ${
                    exportFormat === 'markdown'
                      ? 'border-indigo-600 bg-indigo-50/50 dark:bg-indigo-500/10 text-indigo-700 dark:text-[#a8c7fa]'
                      : 'border-slate-200 dark:border-white/10 text-slate-700 dark:text-slate-300'
                  }`}
                >
                  <span className="text-xs font-semibold block">Markdown</span>
                  <span className="text-[10px] text-slate-500 dark:text-[#a8a8a8]">
                    Readable text
                  </span>
                </button>
              </div>
            </div>

            {/* Footer buttons */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200/80 dark:border-white/10">
              <button
                type="button"
                onClick={() => setIsExportOpen(false)}
                className="px-3.5 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/10 rounded-xl transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handlePerformExport}
                className="px-4 py-1.5 text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl transition-colors cursor-pointer"
              >
                Download Export
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
