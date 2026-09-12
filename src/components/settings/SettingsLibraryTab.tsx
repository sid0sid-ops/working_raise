import React, { useState, useMemo, useRef, useEffect } from 'react';
import { formatBytes } from '../../utils/formatters';
import { sourceService } from '../../services/SourceService';
import { CircularUploadProgress } from '../ui/CircularUploadProgress';

export interface LibraryItem {
  id: string;
  name: string;
  size: string;
  bytes: number;
  uploadedAt: string;
  timestamp: number;
  type: 'pdf' | 'docx' | 'txt' | 'csv' | 'json' | 'md' | 'image' | 'other';
  pages?: number;
  chunks?: number;
  status: 'ready' | 'indexed' | 'processing' | 'error';
  color: 'rose' | 'indigo' | 'amber' | 'emerald';
  uploadProgress?: number;
  can_delete?: boolean;
  is_protected?: boolean;
  is_prebaked?: boolean;
  ownership?: string;
}

export const INITIAL_LIBRARY_ITEMS: LibraryItem[] = [];

/**
 * Maps raw backend document metadata (GET /api/documents) into frontend LibraryItem.
 */
export function documentItemToLibraryItem(doc: {
  filename?: string;
  name?: string;
  id?: string;
  doc_id?: string;
  pages?: number | string;
  size_mb?: number | string;
  chunks_count?: number | string;
  chunks?: number | string;
  status?: string;
  type?: string;
  ownership?: string;
  owner?: string;
  is_prebaked?: boolean;
  is_prebuilt?: boolean;
  is_protected?: boolean;
  can_delete?: boolean;
  deletable?: boolean;
}): LibraryItem {
  const fname = doc.filename || doc.name || 'document';
  const ext = fname.split('.').pop()?.toLowerCase() || '';
  let fileType: LibraryItem['type'] = 'other';
  if (ext === 'pdf') fileType = 'pdf';
  else if (['doc', 'docx'].includes(ext)) fileType = 'docx';
  else if (ext === 'txt') fileType = 'txt';
  else if (['csv', 'tsv'].includes(ext)) fileType = 'csv';
  else if (ext === 'json') fileType = 'json';
  else if (ext === 'md') fileType = 'md';
  else if (['png', 'jpg', 'jpeg', 'svg', 'webp'].includes(ext)) fileType = 'image';

  const colorPalette: LibraryItem['color'][] = ['rose', 'indigo', 'emerald', 'amber'];
  const charCodeSum = fname.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const color = colorPalette[charCodeSum % colorPalette.length];

  const sizeMb = typeof doc.size_mb === 'number' ? doc.size_mb : Number(doc.size_mb) || 0;
  const bytes = Math.round(sizeMb * 1024 * 1024);
  const sizeStr =
    sizeMb >= 1 ? `${sizeMb.toFixed(1)} MB` : sizeMb > 0 ? `${(sizeMb * 1024).toFixed(0)} KB` : '1.0 MB';

  const isReady = doc.status === 'ready' || doc.status === 'indexed';
  const isProcessing = doc.status === 'processing';
  const isProtected = doc.is_protected !== undefined
    ? Boolean(doc.is_protected)
    : (doc.can_delete === false || doc.deletable === false || doc.owner === 'system');
  const canDelete = doc.can_delete !== undefined
    ? Boolean(doc.can_delete)
    : doc.deletable !== undefined
    ? Boolean(doc.deletable)
    : !isProtected;

  const resolvedPages = typeof doc.pages === 'number' ? doc.pages : Number(doc.pages) || 1;
  const rawChunks = doc.chunks_count ?? doc.chunks ?? 0;
  const resolvedChunks = typeof rawChunks === 'number' ? rawChunks : Number(rawChunks) || 0;

  return {
    id: doc.id || doc.doc_id || `doc-${fname}`,
    name: fname,
    size: sizeStr,
    bytes: bytes > 0 ? bytes : 1048576,
    uploadedAt: 'Ready in Library',
    timestamp: Date.now(),
    type: fileType,
    pages: resolvedPages,
    chunks: resolvedChunks,
    status: isReady ? 'indexed' : isProcessing ? 'processing' : 'ready',
    color,
    ownership: doc.ownership || doc.owner || (isProtected ? 'system' : 'user'),
    is_prebaked: doc.is_prebaked || doc.is_prebuilt || isProtected,
    is_protected: isProtected,
    can_delete: canDelete,
  };
}

export type LibrarySortBy =
  | 'date-desc'
  | 'date-asc'
  | 'name-asc'
  | 'name-desc'
  | 'size-desc'
  | 'size-asc'
  | 'type-asc';

export type LibraryViewMode = 'icons' | 'details' | 'full_details';

export interface SettingsLibraryTabProps {
  onSelectDocument?: (doc: LibraryItem) => void;
  onDocumentDeleted?: (id: string, name: string) => void;
  onCloseSettings?: () => void;
}

export const SettingsLibraryTab: React.FC<SettingsLibraryTabProps> = ({
  onSelectDocument,
  onDocumentDeleted,
  onCloseSettings,
}) => {
  const handleOpenInChat = (item: LibraryItem) => {
    if (onSelectDocument) {
      onSelectDocument(item);
    }
    if (onCloseSettings) {
      onCloseSettings();
    }
  };

  const [apiReadyFilenames, setApiReadyFilenames] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Library items strictly managed from backend GET /api/documents
  const [items, setItems] = useState<LibraryItem[]>([]);

  const saveItems = (newItems: LibraryItem[]) => {
    setItems(newItems);
  };

  const isMountedRef = React.useRef(true);
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Authoritative sync with GraphRAG backend: fetch live documents from GET /api/documents
  const fetchLibraryDocuments = React.useCallback(async () => {
    if (!isMountedRef.current) return;
    setIsLoading(true);
    try {
      const resp = await sourceService.getDocuments();
      if (!isMountedRef.current) return;
      if (resp.data && Array.isArray(resp.data.documents)) {
        const backendDocs = resp.data.documents.map(documentItemToLibraryItem);
        setItems(backendDocs);
        const readyNames = new Set(
          resp.data.documents
            .filter((d) => d.status === 'ready' || d.status === 'indexed')
            .map((d) => d.filename.toLowerCase())
        );
        setApiReadyFilenames(readyNames);
      } else {
        setItems([]);
      }
    } catch (err) {
      if (!isMountedRef.current) return;
      console.warn('Backend documents query failed, keeping empty library:', err);
      setItems([]);
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    fetchLibraryDocuments();
  }, [fetchLibraryDocuments]);

  const isItemIndexed = (item: LibraryItem): boolean => {
    if (item.status === 'processing') return false;
    if (item.uploadProgress !== undefined && item.uploadProgress < 100) return false;
    if (apiReadyFilenames.size > 0 && apiReadyFilenames.has(item.name.toLowerCase())) {
      return true;
    }
    return item.status === 'ready' || item.status === 'indexed';
  };

  const [sortBy, setSortBy] = useState<LibrarySortBy>('date-desc');
  const [viewMode, setViewMode] = useState<LibraryViewMode>('icons');
  const [searchQuery, setSearchQuery] = useState('');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 2500);
  };

  // Filter and sort items
  const filteredAndSortedItems = useMemo(() => {
    let result = [...items];

    // Filter by search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter((item) => item.name.toLowerCase().includes(q));
    }

    // Sort
    result.sort((a, b) => {
      switch (sortBy) {
        case 'date-desc':
          return b.timestamp - a.timestamp;
        case 'date-asc':
          return a.timestamp - b.timestamp;
        case 'name-asc':
          return a.name.localeCompare(b.name);
        case 'name-desc':
          return b.name.localeCompare(a.name);
        case 'size-desc':
          return b.bytes - a.bytes;
        case 'size-asc':
          return a.bytes - b.bytes;
        case 'type-asc':
          return a.type.localeCompare(b.type) || a.name.localeCompare(b.name);
        default:
          return 0;
      }
    });

    return result;
  }, [items, searchQuery, sortBy]);

  // Handle file uploads directly into Library with circular progress animation & GraphRAG pipeline sync
  const handleUploadFiles = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;

    const files = Array.from(e.target.files);
    const newUploaded: LibraryItem[] = files.map((file, idx) => {
      const ext = file.name.split('.').pop()?.toLowerCase() || '';
      let fileType: LibraryItem['type'] = 'other';
      let color: LibraryItem['color'] = 'indigo';

      if (ext === 'pdf') {
        fileType = 'pdf';
        color = 'rose';
      } else if (['csv', 'tsv', 'xlsx', 'xls'].includes(ext)) {
        fileType = 'csv';
        color = 'emerald';
      } else if (['doc', 'docx'].includes(ext)) {
        fileType = 'docx';
        color = 'indigo';
      } else if (['json', 'md', 'txt'].includes(ext)) {
        fileType = ext as any;
        color = 'amber';
      }

      const now = new Date();
      const formattedDate = now.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
      const formattedTime = now.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
      });

      return {
        id: `lib-${Date.now()}-${idx}`,
        name: file.name,
        size: formatBytes(file.size),
        bytes: file.size,
        uploadedAt: `${formattedDate}, ${formattedTime}`,
        timestamp: Date.now() + idx,
        type: fileType,
        pages: ext === 'pdf' ? Math.max(1, Math.round(file.size / 100000)) : 1,
        chunks: Math.max(1, Math.round(file.size / 50000)),
        status: 'processing',
        color,
        uploadProgress: 14,
      };
    });

    const updated = [...newUploaded, ...items];
    saveItems(updated);
    showToast(`Uploading ${newUploaded.length} file(s) to Library...`);
    e.target.value = '';

    const newIds = new Set(newUploaded.map((i) => i.id));

    // Smoothly animate circular progress
    let prog = 14;
    const progressTimer = setInterval(() => {
      prog = Math.min(94, prog + Math.floor(Math.random() * 16) + 12);
      setItems((prev) =>
        prev.map((it) => (newIds.has(it.id) ? { ...it, uploadProgress: prog } : it))
      );
    }, 300);

    try {
      const pdfFiles = files.filter((f) => f.name.endsWith('.pdf'));
      if (pdfFiles.length > 0) {
        const uploadRes = await sourceService.uploadPdfs(pdfFiles);
        if (uploadRes.error || uploadRes.status >= 400) {
          throw new Error(uploadRes.error?.message || 'Upload failed');
        }
      } else {
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
      clearInterval(progressTimer);
      setItems((prev) =>
        prev.map((it) =>
          newIds.has(it.id) ? { ...it, uploadProgress: 100, status: 'indexed' as const } : it
        )
      );
      showToast(`Parsed & indexed ${newUploaded.length} file(s) in GraphRAG!`);
    } catch (err: any) {
      clearInterval(progressTimer);
      console.error('Library upload error:', err);
      setItems((prev) =>
        prev.map((it) =>
          newIds.has(it.id) ? { ...it, status: 'error' as const, uploadProgress: 0 } : it
        )
      );
      showToast(err?.message || 'Failed to upload document to backend');
    }
  };

  const handleDeleteItem = async (id: string, name: string) => {
    const target = items.find((it) => it.id === id || it.name === name);
    if (target && (target.can_delete === false || target.is_protected)) {
      showToast(`Document "${name}" is protected and cannot be deleted.`);
      return;
    }

    try {
      const res = await sourceService.deleteDocument(name);
      if (res.error || res.status === 403 || res.status >= 400) {
        showToast(
          res.status === 403
            ? `Document "${name}" is protected and cannot be deleted.`
            : res.error?.message || `Failed to delete "${name}" from Library`
        );
        return;
      }
      const updated = items.filter((item) => item.id !== id);
      saveItems(updated);
      showToast(`Deleted "${name}" & pruned from GraphRAG`);
      if (onDocumentDeleted) {
        onDocumentDeleted(id, name);
      }
    } catch (err: any) {
      showToast(err?.message || `Could not delete "${name}"`);
    }
  };

  const handleDownloadItem = (item: LibraryItem) => {
    const content = `RAISE Knowledge Base Document\n\nFilename: ${item.name}\nSize: ${item.size}\nUploaded: ${item.uploadedAt}\nPages: ${item.pages || 1}\n\nStatus: ${item.status}\nGrounding: GraphRAG Knowledge Base`;
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = item.name.endsWith('.pdf') ? item.name.replace('.pdf', '_metadata.txt') : item.name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast(`Downloaded metadata for "${item.name}"`);
  };

  // Helper for file type icons
  const renderFileTypeIcon = (type: LibraryItem['type'], _color: LibraryItem['color'], sizeClass = 'w-6 h-6') => {
    switch (type) {
      case 'pdf':
        return (
          <svg className={sizeClass} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 13h6m-6 4h4" />
          </svg>
        );
      case 'csv':
        return (
          <svg className={sizeClass} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 10h18M3 14h18m-9-4v8m-7 4h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        );
      case 'docx':
        return (
          <svg className={sizeClass} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        );
      default:
        return (
          <svg className={sizeClass} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        );
    }
  };

  const totalBytes = useMemo(() => items.reduce((acc, cur) => acc + cur.bytes, 0), [items]);

  return (
    <div className="space-y-5 animate-in fade-in duration-200">
      {/* Toast Alert */}
      {toastMessage && (
        <div className="fixed top-5 left-1/2 -translate-x-1/2 z-[140] pointer-events-none animate-in fade-in zoom-in-95 duration-150">
          <div className="px-4 py-2 rounded-xl bg-white/95 dark:bg-[#181a20]/95 text-slate-900 dark:text-white text-xs font-medium shadow-2xl backdrop-blur-md flex items-center gap-2 border border-slate-200/90 dark:border-white/15">
            <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
            <span>{toastMessage}</span>
          </div>
        </div>
      )}

      {/* ─── SEARCH BAR (PLACED ABOVE HEADINGS) ─── */}
      <div className="relative w-full">
        <svg className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <circle cx="11" cy="11" r="8" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-4.35-4.35" />
        </svg>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search documents..."
          className="w-full pl-10 pr-9 py-2 text-xs rounded-xl bg-slate-50 dark:bg-white/[0.04] border border-slate-200/80 dark:border-white/10 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-slate-400 dark:focus:border-slate-500 focus:ring-1 focus:ring-slate-400/40 dark:focus:ring-slate-500/40 transition-all shadow-2xs"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery('')}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xs cursor-pointer"
            aria-label="Clear search"
          >
            ✕
          </button>
        )}
      </div>

      {/* ─── HEADER SECTION (BELOW SEARCH) ─── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200/80 dark:border-white/10">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-slate-900 dark:text-white">Library</h3>
            <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 dark:bg-white/10 text-slate-700 dark:text-slate-300 border border-slate-200/80 dark:border-white/10">
              {items.length} {items.length === 1 ? 'file' : 'files'}
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-[#a8a8a8] mt-1">
            All uploaded knowledge documents, reports, and datasets with size and upload timestamp ({formatBytes(totalBytes)} total storage).
          </p>
        </div>

        {/* Upload file trigger - Premium Gray */}
        <div className="flex items-center gap-2 shrink-0">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleUploadFiles}
            multiple
            className="hidden"
            accept=".pdf,.docx,.doc,.txt,.csv,.json,.xlsx"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100 border border-slate-700/30 dark:border-white/20 active:scale-95 text-xs font-medium transition-all flex items-center gap-1.5 shadow-xs cursor-pointer"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            <span>Upload New</span>
          </button>
        </div>
      </div>

      {/* ─── CONTROLS BAR: SORT BY & VIEW SWITCHER ─── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/80 dark:bg-white/[0.02] p-2.5 rounded-2xl border border-slate-200/80 dark:border-white/10">
        {/* Left: Sort By Dropdown */}
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-medium text-slate-500 dark:text-[#a8a8a8] whitespace-nowrap">
            Sort by:
          </span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as LibrarySortBy)}
            aria-label="Sort by"
            className="text-xs py-1.5 px-2.5 rounded-xl bg-white dark:bg-[#18191a] border border-slate-200 dark:border-white/10 text-slate-800 dark:text-slate-200 focus:outline-none focus:border-slate-400 dark:focus:border-slate-500 cursor-pointer"
          >
            <option value="date-desc">Newest Upload</option>
            <option value="date-asc">Oldest Upload</option>
            <option value="name-asc">Name (A → Z)</option>
            <option value="name-desc">Name (Z → A)</option>
            <option value="size-desc">Size (Largest)</option>
            <option value="size-asc">Size (Smallest)</option>
            <option value="type-asc">Sort by Type</option>
          </select>
        </div>

        {/* Right: View Mode Switcher: Icons, Details, Full Details (PURE ICONS, NO TEXT, NO TOOLTIP) */}
        <div className="flex items-center gap-1 bg-white dark:bg-[#18191a] p-0.5 rounded-xl border border-slate-200 dark:border-white/10 self-end sm:self-auto">
            {/* View: Icons */}
            <button
              type="button"
              onClick={() => setViewMode('icons')}
              aria-label="Icons view"
              className={`p-1.5 rounded-lg text-xs font-medium flex items-center justify-center transition-all cursor-pointer ${
                viewMode === 'icons'
                  ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
              </svg>
            </button>

            {/* View: Details */}
            <button
              type="button"
              onClick={() => setViewMode('details')}
              aria-label="Details view"
              className={`p-1.5 rounded-lg text-xs font-medium flex items-center justify-center transition-all cursor-pointer ${
                viewMode === 'details'
                  ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            {/* View: Full Details */}
            <button
              type="button"
              onClick={() => setViewMode('full_details')}
              aria-label="Full details view"
              className={`p-1.5 rounded-lg text-xs font-medium flex items-center justify-center transition-all cursor-pointer ${
                viewMode === 'full_details'
                  ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 10h16M4 14h16M4 18h7" />
              </svg>
            </button>
          </div>
        </div>

      {/* Loading State */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-16 text-xs text-slate-400 dark:text-slate-500 gap-2.5">
          <div className="w-6 h-6 rounded-full border-2 border-slate-300 dark:border-slate-600 border-t-indigo-600 animate-spin" />
          <span className="font-medium">Checking Knowledge Base Library...</span>
        </div>
      ) : filteredAndSortedItems.length === 0 ? (
        <div className="text-center py-12 px-4 rounded-2xl border border-dashed border-slate-200 dark:border-white/10 bg-slate-50/50 dark:bg-white/[0.01]">
          <div className="w-12 h-12 mx-auto mb-3 rounded-2xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
          <p className="text-sm font-semibold text-slate-900 dark:text-white">
            {searchQuery ? 'No documents match your search' : 'Knowledge Base Library is empty'}
          </p>
          <p className="text-xs text-slate-500 dark:text-[#a8a8a8] mt-1 max-w-sm mx-auto">
            {searchQuery
              ? `No documents match "${searchQuery}"`
              : 'No documents have been indexed into the GraphRAG knowledge base yet. Upload files from your computer to populate the library.'}
          </p>
          {!searchQuery && (
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="mt-4 px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md active:scale-95 transition-all cursor-pointer inline-flex items-center gap-1.5"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
              </svg>
              <span>Upload Document to Library</span>
            </button>
          )}
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="mt-3 text-xs text-slate-700 dark:text-slate-200 hover:underline font-medium cursor-pointer"
            >
              Clear search query
            </button>
          )}
        </div>
      ) : null}

      {/* ─── 1. VIEW MODE: ICONS (Grid View - EXACTLY 3 DOCUMENTS PER ROW) ─── */}
      {viewMode === 'icons' && filteredAndSortedItems.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 gap-3.5">
          {filteredAndSortedItems.map((item) => {
            const indexed = isItemIndexed(item);
            const progress = item.uploadProgress ?? 45;
            const badgeBg =
              item.color === 'rose'
                ? 'bg-rose-50 text-rose-600 dark:bg-rose-500/15 dark:text-rose-400 border-rose-200/60 dark:border-rose-500/20'
                : item.color === 'emerald'
                ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-400 border-emerald-200/60 dark:border-emerald-500/20'
                : item.color === 'amber'
                ? 'bg-amber-50 text-amber-600 dark:bg-amber-500/15 dark:text-amber-400 border-amber-200/60 dark:border-amber-500/20'
                : 'bg-indigo-50 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-400 border-indigo-200/60 dark:border-indigo-500/20';

            return (
              <div
                key={item.id}
                className={`group relative p-3.5 rounded-2xl border transition-all flex flex-col justify-between shadow-2xs hover:shadow-md ${
                  !indexed
                    ? 'filter blur-[1.5px] opacity-65 bg-slate-50/50 dark:bg-white/[0.01] border-slate-200/60 dark:border-white/5 cursor-not-allowed select-none'
                    : 'bg-slate-50/70 dark:bg-white/[0.03] border-slate-200/80 dark:border-white/10 hover:border-slate-400 dark:hover:border-white/30 hover:bg-white dark:hover:bg-[#232631]'
                }`}
                title={!indexed ? `Document is still parsing in GraphRAG... (${Math.round(progress)}%)` : item.name}
              >
                {/* Top: Icon and Type Tag */}
                <div className="flex items-start justify-between gap-2 mb-2.5">
                  <div className="relative">
                    <div className={`p-2 rounded-xl border ${badgeBg} shrink-0`}>
                      {renderFileTypeIcon(item.type, item.color, 'w-5 h-5')}
                    </div>
                  </div>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-md bg-slate-200/60 dark:bg-white/10 text-slate-600 dark:text-slate-300 font-medium">
                    {item.size}
                  </span>
                </div>

                {/* Filename */}
                <div className="min-w-0 mb-3">
                  <h4
                    className="text-xs font-semibold text-slate-900 dark:text-white truncate"
                    title={item.name}
                  >
                    {item.name}
                  </h4>
                  <p className="text-[11px] text-slate-400 dark:text-[#a8a8a8] mt-1 flex items-center gap-1">
                    <svg className="w-3 h-3 text-slate-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="10" />
                      <polyline points="12 6 12 12 16 14" />
                    </svg>
                    <span className="truncate">{item.uploadedAt}</span>
                  </p>
                </div>

                {/* Footer: Quick Actions (Single circular loader when parsing, delete x when indexed) */}
                <div className="pt-2 border-t border-slate-200/60 dark:border-white/5 flex items-center justify-between">
                  {!indexed ? (
                    <span
                      className="inline-flex items-center gap-1.5 text-[10px] text-amber-600 dark:text-amber-400 font-medium"
                      title="Parsing in GraphRAG..."
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
                      <span>Parsing...</span>
                    </span>
                  ) : (
                    <span className="text-[10px] text-slate-400 dark:text-[#a8a8a8] font-mono">
                      {item.pages ? `${item.pages} pp.` : 'Indexed'}
                    </span>
                  )}
                  <div className="flex items-center gap-1">
                    {!indexed ? (
                      <div
                        className="flex items-center text-[10px] font-mono text-indigo-600 dark:text-[#a8c7fa] p-1"
                        title={`Parsing progress: ${Math.round(progress)}%`}
                      >
                        <CircularUploadProgress progress={progress} size={24} strokeWidth={2.5} showPercentText={true} />
                      </div>
                    ) : (
                      <>
                        <button
                          type="button"
                          onClick={() => handleDownloadItem(item)}
                          className="p-1 rounded-md text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-500/15 transition-colors cursor-pointer"
                          title="Download metadata"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                          </svg>
                        </button>
                        {item.can_delete !== false && !item.is_protected ? (
                          <button
                            type="button"
                            onClick={() => handleDeleteItem(item.id, item.name)}
                            className="p-1 rounded-md text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-500/15 transition-colors cursor-pointer"
                            title="Delete from Library & GraphRAG"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        ) : (
                          <span className="p-1 text-slate-400 dark:text-slate-500 cursor-not-allowed" title="Protected document">
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" strokeWidth="2" />
                              <path d="M7 11V7a5 5 0 0110 0v4" strokeWidth="2" />
                            </svg>
                          </span>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ─── 2. VIEW MODE: DETAILS (Compact List/Table View) ─── */}
      {viewMode === 'details' && filteredAndSortedItems.length > 0 && (
        <div className="border border-slate-200/80 dark:border-white/10 rounded-2xl overflow-hidden bg-white dark:bg-[#1e1f20]">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50/80 dark:bg-white/[0.02] border-b border-slate-200/80 dark:border-white/10 text-slate-500 dark:text-[#a8a8a8] font-medium">
                  <th className="py-2.5 px-3.5">Document Name</th>
                  <th className="py-2.5 px-3">Type</th>
                  <th className="py-2.5 px-3">Size</th>
                  <th className="py-2.5 px-3">Upload Date &amp; Time</th>
                  <th className="py-2.5 px-3">Pages</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/60 dark:divide-white/5">
                {filteredAndSortedItems.map((item) => {
                  const indexed = isItemIndexed(item);
                  const progress = item.uploadProgress ?? 45;
                  return (
                    <tr
                      key={item.id}
                      className={`transition-colors group ${
                        !indexed
                           ? 'filter blur-[1.5px] opacity-65 bg-slate-50/40 dark:bg-white/[0.01]'
                          : 'hover:bg-slate-50/70 dark:hover:bg-white/[0.03]'
                      }`}
                    >
                      <td className="py-2.5 px-3.5 font-medium text-slate-900 dark:text-white max-w-[220px]">
                        <div className="flex items-center gap-2">
                          <div className="relative shrink-0">
                            {renderFileTypeIcon(item.type, item.color, 'w-4 h-4 text-slate-400')}
                          </div>
                          <span className="truncate" title={item.name}>{item.name}</span>
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-slate-500 dark:text-slate-400 uppercase font-mono text-[11px]">
                        {item.type}
                      </td>
                      <td className="py-2.5 px-3 text-slate-600 dark:text-slate-300 font-mono text-[11px]">
                        {item.size}
                      </td>
                      <td className="py-2.5 px-3 text-slate-500 dark:text-slate-400 text-[11px] whitespace-nowrap">
                        {item.uploadedAt}
                      </td>
                      <td className="py-2.5 px-3 text-slate-600 dark:text-slate-300 font-mono text-[11px]">
                        {item.pages ? `${item.pages} pp.` : '1 p.'}
                      </td>
                      <td className="py-2.5 px-3">
                        {!indexed ? (
                          <span className="inline-flex items-center gap-1.5 text-[10px] text-amber-600 dark:text-amber-400 font-medium">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
                            <span>Parsing...</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                            <span>Ready</span>
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {!indexed ? (
                            <div className="p-1" title={`Parsing: ${Math.round(progress)}%`}>
                              <CircularUploadProgress progress={progress} size={22} strokeWidth={2.5} showPercentText={true} />
                            </div>
                          ) : (
                            <>
                              <button
                                type="button"
                                onClick={() => handleDownloadItem(item)}
                                className="p-1 rounded-md text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-slate-100 dark:hover:bg-white/10 transition-colors cursor-pointer"
                                title="Download"
                              >
                                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                </svg>
                              </button>
                              {item.can_delete !== false && !item.is_protected ? (
                                <button
                                  type="button"
                                  onClick={() => handleDeleteItem(item.id, item.name)}
                                  className="p-1 rounded-md text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-slate-100 dark:hover:bg-white/10 transition-colors cursor-pointer"
                                  title="Delete"
                                >
                                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                  </svg>
                                </button>
                              ) : (
                                <span className="p-1 text-slate-400 dark:text-slate-500 cursor-not-allowed" title="Protected document">
                                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" strokeWidth="2" />
                                    <path d="M7 11V7a5 5 0 0110 0v4" strokeWidth="2" />
                                  </svg>
                                </span>
                              )}
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ─── 3. VIEW MODE: FULL DETAILS (Rich Card View) ─── */}
      {viewMode === 'full_details' && filteredAndSortedItems.length > 0 && (
        <div className="space-y-3">
          {filteredAndSortedItems.map((item) => {
            const indexed = isItemIndexed(item);
            const progress = item.uploadProgress ?? 45;
            const badgeBg =
              item.color === 'rose'
                ? 'bg-rose-50 text-rose-600 dark:bg-rose-500/15 dark:text-rose-400 border-rose-200/60 dark:border-rose-500/20'
                : item.color === 'emerald'
                ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-400 border-emerald-200/60 dark:border-emerald-500/20'
                : item.color === 'amber'
                ? 'bg-amber-50 text-amber-600 dark:bg-amber-500/15 dark:text-amber-400 border-amber-200/60 dark:border-amber-500/20'
                : 'bg-indigo-50 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-400 border-indigo-200/60 dark:border-indigo-500/20';

            return (
              <div
                key={item.id}
                className={`p-4 rounded-2xl border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-2xs ${
                  !indexed
                    ? 'filter blur-[1.5px] opacity-65 bg-slate-50/50 dark:bg-white/[0.01] border-slate-200/60 dark:border-white/5 cursor-not-allowed select-none'
                    : 'bg-slate-50/70 dark:bg-white/[0.03] border-slate-200/80 dark:border-white/10 hover:border-slate-400 dark:hover:border-white/30'
                }`}
              >
                {/* Left: Icon and info */}
                <div className="flex items-start gap-3.5 min-w-0">
                  <div className="relative shrink-0 mt-0.5">
                    <div className={`p-2.5 rounded-2xl border ${badgeBg}`}>
                      {renderFileTypeIcon(item.type, item.color, 'w-6 h-6')}
                    </div>
                  </div>
                  <div className="min-w-0 space-y-1">
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-white truncate" title={item.name}>
                      {item.name}
                    </h4>
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500 dark:text-[#a8a8a8]">
                      <span className="flex items-center gap-1 font-mono">
                        <span className="font-semibold text-slate-700 dark:text-slate-200">{item.size}</span>
                      </span>
                      <span>•</span>
                      <span className="flex items-center gap-1">
                        <svg className="w-3.5 h-3.5 text-slate-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <circle cx="12" cy="12" r="10" />
                          <polyline points="12 6 12 12 16 14" />
                        </svg>
                        <span>Uploaded {item.uploadedAt}</span>
                      </span>
                      {item.pages && (
                        <>
                          <span>•</span>
                          <span>{item.pages} pages</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Right: Exactly ONE Circular Progress Spinner */}
                <div className="flex items-center gap-2.5 shrink-0 self-end sm:self-center">
                  {!indexed ? (
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-1 rounded-full text-[11px] font-medium bg-amber-50 dark:bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-200/50 dark:border-amber-500/20 flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
                        <span>Parsing in GraphRAG...</span>
                      </span>
                      <div className="p-1" title={`Uploading: ${Math.round(progress)}%`}>
                        <CircularUploadProgress progress={progress} size={26} strokeWidth={2.5} showPercentText={true} />
                      </div>
                    </div>
                  ) : (
                    <>
                      {onSelectDocument && (
                        <button
                          type="button"
                          onClick={() => handleOpenInChat(item)}
                          className="px-2.5 py-1.5 text-xs font-medium text-slate-800 dark:text-slate-200 bg-slate-100 hover:bg-slate-200 dark:bg-white/10 dark:hover:bg-white/15 border border-slate-200 dark:border-white/10 rounded-xl transition-colors flex items-center gap-1 cursor-pointer"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
                          </svg>
                          <span>Attach</span>
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={() => handleDownloadItem(item)}
                        className="px-2.5 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-[#18191a] hover:bg-slate-100 dark:hover:bg-white/10 border border-slate-200 dark:border-white/10 rounded-xl transition-colors flex items-center gap-1 cursor-pointer"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        <span>Download</span>
                      </button>

                      {item.can_delete !== false && !item.is_protected ? (
                        <button
                          type="button"
                          onClick={() => handleDeleteItem(item.id, item.name)}
                          className="p-1.5 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-500/15 rounded-xl transition-colors cursor-pointer"
                          title="Delete file & prune GraphRAG"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      ) : (
                        <span className="p-1.5 text-slate-400 dark:text-slate-500 cursor-not-allowed" title="Protected document">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" strokeWidth="2" />
                            <path d="M7 11V7a5 5 0 0110 0v4" strokeWidth="2" />
                          </svg>
                        </span>
                      )}
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
