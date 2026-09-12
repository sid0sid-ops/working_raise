import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { chatService } from '../../services/ChatService';
import { sourceService } from '../../services/SourceService';
import { systemService } from '../../services/SystemService';
import { useModeStore } from '../../stores/modeStore';
import { useUiStore } from '../../stores/uiStore';
import { SubgraphQueryResponse, Citation } from '../../types';
import { AnswerMarkdown } from '../../components/chat/AnswerMarkdown';
import { Modal } from '../../components/ui/Modal';
import { InlinePdfViewer } from '../../components/citations/InlinePdfViewer';
import { QueryLifecycleTracker, ThoughtDuration } from '../../components/chat/QueryLifecycleTracker';
import { BackendErrorCard, BackendErrorDetails, ResponseStoppedBanner } from '../../components/chat/BackendErrorCard';
import { formatBytes } from '../../utils/formatters';
import { applyStoredTunerConfigToDom } from '../../components/ui/GridGradientTuner';
import { ensureMinimumDuration } from '../../utils/async';
import { LibraryItem } from '../../components/settings/SettingsLibraryTab';
import { LibraryPickerModal } from '../../components/library/LibraryPickerModal';
import { CircularUploadProgress } from '../../components/ui/CircularUploadProgress';
import { ExportResponseDropdown } from '../../components/chat/ExportResponseDropdown';
import { VoiceInputButton } from '../../components/input/VoiceInputButton';
import { copyMarkdownToClipboard } from '../../utils/exportFormats';
import { getStoredUsername, setStoredUsername, setStoredApiKey } from '../../app/config';
import { generateUUID, truncateSessionTitle, formatSessionDate } from '../../utils/uuid';
import { sanitizeStreamText } from '../../utils/sanitizeStreamText';
import { terminalLogger } from '../../utils/terminalLogger';
import { Header as MainHeader, UnconfiguredNotice } from '../header';
import { Sidebar as MainSidebar, SearchModal as MainSearchModal } from '../sidebar';
import { SettingsModal as MainSettingsModal, settingsJunction, useSettingsJunction } from '../settings';

import { useFilterStore } from '../../stores/filterStore';
import {
  SourceDocument,
  ResponseVersion,
  QuestionVersion,
  ChatMessage,
  ChatSession,
  DynamicSuggestion,
} from './types';
import {
  computeVoiceWaveScale,
  cleanTextForSpeech,
  ROBOTIC_VOICE_NAMES,
  filterNaturalVoices,
  selectBestSpeechVoice,
  getTurnQuestionVersions,
} from './utils/speechUtils';
import { ActionTooltip } from './components/ActionTooltip';
import { SpecialTooltip } from '../../components/ui/SpecialTooltip';
import { SourcesDrawer } from './components/SourcesDrawer';

// Re-export types and utilities for consumers & tests
export type {
  SourceDocument,
  ResponseVersion,
  QuestionVersion,
  ChatMessage,
  ChatSession,
  DynamicSuggestion,
};

export {
  computeVoiceWaveScale,
  cleanTextForSpeech,
  ROBOTIC_VOICE_NAMES,
  filterNaturalVoices,
  selectBestSpeechVoice,
  getTurnQuestionVersions,
  ActionTooltip,
  SpecialTooltip,
};

const ANIMATED_PLACEHOLDER_PROMPTS = [
  'Ask any question..',
  'Ask any question about research & innovations..',
  'Ask any question about patents & publications..',
  'Ask any question about documents & analysis..',
];

export const RaisePage: React.FC = () => {
  const {
    apiBaseUrl,
    appMode,
    gatewayUsername,
    isTunnelConfigured,
    runCapabilityProbe,
    setUsername,
    setApiKey,
    clearTunnelUrl,
  } = useModeStore();
  const isOnline = isTunnelConfigured && appMode === 'connected';
  const hasTopNotice = !isTunnelConfigured || (isTunnelConfigured && appMode === 'offline');

  // Navigation & Drawer states
  const [isPipelineDrawerOpen, setIsPipelineDrawerOpen] = useState(false);
  const [isSourcesDrawerOpen, setIsSourcesDrawerOpen] = useState(false);
  const [isSearchModalOpen, setIsSearchModalOpen] = useState(false);
  const {
    isOpen: isSettingsOpen,
    isTunerMode,
    open: openSettingsJunction,
    close: closeSettingsJunction,
    toggle: toggleSettingsJunction,
    setTab: setSettingsActiveTab,
    setMobileView: setMobileSettingsView,
    setTunerMode: setIsTunerMode,
    setShowOutsideClickTip,
  } = useSettingsJunction();

  const setIsSettingsOpen = (val: boolean | ((prev: boolean) => boolean)) => {
    if (typeof val === 'function') {
      const next = val(isSettingsOpen);
      if (next) openSettingsJunction();
      else closeSettingsJunction();
    } else {
      if (val) openSettingsJunction();
      else closeSettingsJunction();
    }
  };
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Keyboard navigation & suggestions states
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(-1);

  // Initialize stored grid & ambient light CSS variables on application mount
  useEffect(() => {
    applyStoredTunerConfigToDom();
  }, []);

  const [apiReadyFilenames, setApiReadyFilenames] = useState<Set<string>>(new Set());

  // Authoritative sync with GraphRAG backend: query ready documents
  useEffect(() => {
    let active = true;
    sourceService
      .getDocuments()
      .then((resp) => {
        if (!active) return;
        if (resp.data && resp.data.documents) {
          const readyNames = new Set(
            resp.data.documents
              .filter((d) => d.status === 'ready')
              .map((d) => d.filename.toLowerCase())
          );
          setApiReadyFilenames(readyNames);
        }
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const isDocReady = (doc: SourceDocument): boolean => {
    if (doc.uploadProgress !== undefined && doc.uploadProgress < 100) return false;
    if (doc.status === 'processing') return false;
    if (apiReadyFilenames.size > 0) {
      return apiReadyFilenames.has(doc.name.toLowerCase());
    }
    return doc.status === 'ready' || doc.status === undefined;
  };

  const [isVoiceSamplePlaying, setIsVoiceSamplePlaying] = useState(false);
  const [parseMode, setParseMode] = useState<'fast' | 'expert'>('fast');
  const [errorPopup, setErrorPopup] = useState<{
    title: string;
    message?: string;
    onRetry?: () => void;
  } | null>(null);

  const showErrorPopup = (title: string, message?: string, onRetry?: () => void) => {
    setErrorPopup({ title, message, onRetry });
    setTimeout(() => {
      setErrorPopup((curr) => (curr?.title === title ? null : curr));
    }, 6000);
  };
  const [pinnedSessionIds, setPinnedSessionIds] = useState<string[]>([]);

  const handleTogglePinSession = (sessionId: string) => {
    setPinnedSessionIds((prev) => {
      return prev.includes(sessionId)
        ? prev.filter((id) => id !== sessionId)
        : [sessionId, ...prev];
    });
  };
  const { activeModal, openModal, closeModal, selectedCitation, setSelectedCitation } = useUiStore();
  const [theme, setTheme] = useState<'dark' | 'light' | 'system'>(() => {
    const saved = localStorage.getItem('raise_theme');
    if (saved === 'dark' || saved === 'light' || saved === 'system') return saved;
    return 'dark';
  });

  // Handle active theme toggling (Dark, Light, System) across html and body
  useEffect(() => {
    const root = document.documentElement;
    localStorage.setItem('raise_theme', theme);

    const applyTheme = (isDark: boolean) => {
      if (isDark) {
        root.classList.add('dark');
        root.classList.remove('light');
        root.setAttribute('data-theme', 'dark');
        document.body.style.backgroundColor = '#0e1017';
        document.body.style.color = '#f1f5f9';
      } else {
        root.classList.remove('dark');
        root.classList.add('light');
        root.setAttribute('data-theme', 'light');
        document.body.style.backgroundColor = '#f8fafc';
        document.body.style.color = '#0f172a';
      }
    };

    if (theme === 'system') {
      const media = window.matchMedia('(prefers-color-scheme: dark)');
      applyTheme(media.matches);
      const listener = (e: MediaQueryListEvent) => applyTheme(e.matches);
      media.addEventListener('change', listener);
      return () => media.removeEventListener('change', listener);
    } else {
      applyTheme(theme === 'dark');
    }
  }, [theme]);


  // Cancel any voice sample preview when settings dialog closes
  useEffect(() => {
    if (!isSettingsOpen && isVoiceSamplePlaying) {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
      setIsVoiceSamplePlaying(false);
    }
  }, [isSettingsOpen, isVoiceSamplePlaying]);

  // Chat Sessions state from backend / user history
  const [sessions, setSessions] = useState<ChatSession[]>([]);

  // Current session ID: starts null for new chat
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  // Conversation messages: starts empty for new chat
  const [conversation, setConversation] = useState<ChatMessage[]>([]);

  // Fetch PostgreSQL sessions when tunnel is configured and online
  useEffect(() => {
    if (!isTunnelConfigured) {
      setSessions([]);
      setConversation([]);
      setSourceDocs([]);
      setCurrentSessionId(null);
      return;
    }

    let isMounted = true;
    const restoreSessionAndHistory = async () => {
      const username = getStoredUsername();

      // Fetch sessions list from backend (PostgreSQL)
      try {
        const sessionsRes = await chatService.listChatSessions?.(username);
        if (isMounted && sessionsRes?.data && Array.isArray(sessionsRes.data)) {
          const fetchedRemoteSessions: ChatSession[] = sessionsRes.data.map((item: any) => {
            const attachedDocList: string[] = Array.isArray(item.attached_docs)
              ? item.attached_docs
              : [];
            let resolvedSources = Array.isArray(item.sources) ? item.sources : [];

            if (attachedDocList.length > 0 && resolvedSources.length > 0) {
              resolvedSources = resolvedSources.map((s: SourceDocument) => ({
                ...s,
                selected: attachedDocList.includes(s.name) || attachedDocList.includes(s.id),
              }));
            } else if (attachedDocList.length > 0 && resolvedSources.length === 0) {
              resolvedSources = attachedDocList.map((docName: string, idx: number) => ({
                id: `attached-${idx}-${docName}`,
                name: docName,
                size: '12 MB',
                pages: 20,
                selected: true,
                color: 'indigo',
                status: 'ready',
              }));
            }

            return {
              id: item.thread_id || item.session_id || item.id,
              thread_id: item.thread_id || item.session_id || item.id,
              session_id: item.thread_id || item.session_id || item.id,
              title: item.title || 'Chat Session',
              timestamp: item.timestamp || formatSessionDate(item.updated_at || item.created_at),
              messages: Array.isArray(item.messages) ? item.messages : [],
              selectedSourceIds: item.selectedSourceIds || resolvedSources.filter((s: any) => s.selected).map((s: any) => s.id),
              sources: resolvedSources,
              attached_docs: attachedDocList,
              is_saved: Boolean(item.is_saved),
              created_at: item.created_at,
              updated_at: item.updated_at,
            };
          });

          if (isMounted) {
            setSessions(fetchedRemoteSessions);
          }
        }
      } catch (err) {
        console.warn('Could not sync chat sessions from backend:', err);
      }
    };

    restoreSessionAndHistory();
    return () => {
      isMounted = false;
    };
  }, [isTunnelConfigured]);

  const [activeSessionMenuId, setActiveSessionMenuId] = useState<string | null>(null);
  const [renamingSessionId, setRenamingSessionId] = useState<string | null>(null);
  const [newSessionTitle, setNewSessionTitle] = useState('');

  // Sort sessions with pinned sessions first, preserving recency order (newest on top)
  const sortedSessions = useMemo(() => {
    return [...sessions].sort((a, b) => {
      const aPinned = pinnedSessionIds.includes(a.id);
      const bPinned = pinnedSessionIds.includes(b.id);
      if (aPinned && !bPinned) return -1;
      if (!aPinned && bPinned) return 1;
      const aTime = a.updated_at ? new Date(a.updated_at).getTime() : (a.created_at ? new Date(a.created_at).getTime() : 0);
      const bTime = b.updated_at ? new Date(b.updated_at).getTime() : (b.created_at ? new Date(b.created_at).getTime() : 0);
      if (aTime && bTime && aTime !== bTime) {
        return bTime - aTime;
      }
      return 0;
    });
  }, [sessions, pinnedSessionIds]);


  // Close three dots dropdown on outside click
  useEffect(() => {
    if (!activeSessionMenuId) return;
    const handleOutsideClick = () => setActiveSessionMenuId(null);
    window.addEventListener('click', handleOutsideClick);
    return () => window.removeEventListener('click', handleOutsideClick);
  }, [activeSessionMenuId]);

  // Chat & Query states
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Dynamic graph-grounded query suggestions from GET /api/suggestions
  const [dynamicSuggestions, setDynamicSuggestions] = useState<DynamicSuggestion[]>([]);
  const [, setIsLoadingSuggestions] = useState(false);

  const filteredSuggestions = useMemo(() => {
    if (dynamicSuggestions.length === 0) return [];
    if (!query.trim()) return dynamicSuggestions;
    const q = query.toLowerCase().trim();
    return dynamicSuggestions.filter((s) => s.query.toLowerCase().includes(q));
  }, [dynamicSuggestions, query]);

  // Animated placeholder typewriter states for new chat question box
  const [placeholderText, setPlaceholderText] = useState('');
  const [promptIndex, setPromptIndex] = useState(0);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    if (conversation.length > 0 || query.length > 0) return;

    const currentPrompt = ANIMATED_PLACEHOLDER_PROMPTS[promptIndex % ANIMATED_PLACEHOLDER_PROMPTS.length];
    let timer: NodeJS.Timeout;

    if (!isDeleting) {
      if (placeholderText.length < currentPrompt.length) {
        timer = setTimeout(() => {
          setPlaceholderText(currentPrompt.slice(0, placeholderText.length + 1));
        }, 50);
      } else {
        const pauseDuration = promptIndex % ANIMATED_PLACEHOLDER_PROMPTS.length === 0 ? 4500 : 3200;
        timer = setTimeout(() => {
          setIsDeleting(true);
        }, pauseDuration);
      }
    } else {
      if (placeholderText.length > 0) {
        timer = setTimeout(() => {
          setPlaceholderText(currentPrompt.slice(0, placeholderText.length - 1));
        }, 25);
      } else {
        setIsDeleting(false);
        setPromptIndex((prev) => (prev + 1) % ANIMATED_PLACEHOLDER_PROMPTS.length);
      }
    }

    return () => clearTimeout(timer);
  }, [conversation.length, query.length, placeholderText, isDeleting, promptIndex]);

  // User Question & AI Response action states
  const [editingMessageIndex, setEditingMessageIndex] = useState<number | null>(null);
  const [editingQuestionText, setEditingQuestionText] = useState('');
  const [regeneratingIndex, setRegeneratingIndex] = useState<number | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null);
  const [expandedQVersionsIndex, setExpandedQVersionsIndex] = useState<number | null>(null);
  const [expandedRespVersionsIndex, setExpandedRespVersionsIndex] = useState<number | null>(null);

  // Read Aloud Speech Synthesis voices state
  const [availableVoices, setAvailableVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [selectedVoiceName, setSelectedVoiceName] = useState<string>(() => {
    try {
      return localStorage.getItem('raise_tts_voice') || '';
    } catch {
      return '';
    }
  });

  // Voice Query (Speech Recognition & Animated Audio Waveform) state
  const [isListening, setIsListening] = useState(false);
  const [isVoiceSpeaking, setIsVoiceSpeaking] = useState(false);
  const [voiceAudioLevels, setVoiceAudioLevels] = useState<number[]>([0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25]);
  const [voiceDurationSec, setVoiceDurationSec] = useState(0);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);
  const baseQueryRef = useRef<string>('');
  const speechTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const voiceTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioAnalyserRef = useRef<AnalyserNode | null>(null);
  const audioAnimFrameRef = useRef<number | null>(null);

  const formatVoiceDuration = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const stopVoiceListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
      recognitionRef.current = null;
    }
    if (voiceTimerRef.current) {
      clearInterval(voiceTimerRef.current);
      voiceTimerRef.current = null;
    }
    setVoiceDurationSec(0);
    if (audioAnimFrameRef.current) {
      cancelAnimationFrame(audioAnimFrameRef.current);
      audioAnimFrameRef.current = null;
    }
    if (audioStreamRef.current) {
      try {
        audioStreamRef.current.getTracks().forEach((track) => track.stop());
      } catch {}
      audioStreamRef.current = null;
    }
    if (audioContextRef.current) {
      try {
        audioContextRef.current.close();
      } catch {}
      audioContextRef.current = null;
    }
    audioAnalyserRef.current = null;
    if (speechTimeoutRef.current) {
      clearTimeout(speechTimeoutRef.current);
      speechTimeoutRef.current = null;
    }
    setIsListening(false);
    setIsVoiceSpeaking(false);
    setVoiceAudioLevels([0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25]);
  }, []);

  // Cleanup speech recognition and media on unmount
  useEffect(() => {
    return () => {
      stopVoiceListening();
    };
  }, [stopVoiceListening]);

  // Preload and refresh available voices from SpeechSynthesis
  useEffect(() => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;

    const loadVoices = () => {
      const all = window.speechSynthesis.getVoices();
      if (!all || all.length === 0) return;
      const natural = filterNaturalVoices(all);
      setAvailableVoices(natural.length > 0 ? natural : all);

      const best = selectBestSpeechVoice(all, selectedVoiceName);
      if (best) {
        if (!selectedVoiceName || !all.some((v) => v.name === selectedVoiceName)) {
          setSelectedVoiceName(best.name);
          try {
            localStorage.setItem('raise_tts_voice', best.name);
          } catch {}
        }
      }
    };

    loadVoices();
    window.speechSynthesis.onvoiceschanged = loadVoices;

    return () => {
      if (window.speechSynthesis) {
        window.speechSynthesis.onvoiceschanged = null;
      }
    };
  }, [selectedVoiceName]);

  // Close question and response version navigation when clicking anywhere on the screen or pressing Escape
  useEffect(() => {
    if (expandedQVersionsIndex === null && expandedRespVersionsIndex === null) return;
    const handleOutsideClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement | null;
      if (target?.closest('[data-version-nav]')) {
        return;
      }
      setExpandedQVersionsIndex(null);
      setExpandedRespVersionsIndex(null);
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setExpandedQVersionsIndex(null);
        setExpandedRespVersionsIndex(null);
      }
    };

    window.addEventListener('click', handleOutsideClick);
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('click', handleOutsideClick);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [expandedQVersionsIndex, expandedRespVersionsIndex]);

  // Synchronized source documents (scoped to current chat session; starts empty for new chat)
  const [sourceDocs, setSourceDocs] = useState<SourceDocument[]>([]);
  const [sourceFilter, setSourceFilter] = useState('');

  // Active documents in the Drawer
  const activeDocNames = useMemo(() => {
    return sourceDocs.filter((d) => d.selected).map((d) => d.name);
  }, [sourceDocs]);

  // Dynamic graph-grounded suggestions from GET /api/suggestions
  useEffect(() => {
    // When 0 documents are in Drawer, returns [] (clean chat interface, no suggestion cards)
    if (activeDocNames.length === 0) {
      setDynamicSuggestions([]);
      return;
    }

    let active = true;
    setIsLoadingSuggestions(true);

    chatService
      .getSuggestions?.(activeDocNames)
      ?.then((res) => {
        if (!active) return;
        if (res.data && Array.isArray(res.data)) {
          const normalized: DynamicSuggestion[] = res.data
            .map((item: any) => {
              if (typeof item === 'string') {
                return { query: item };
              }
              return {
                query: item.query || item.title || item.prompt || '',
                category: item.category,
                grounding_confidence: item.grounding_confidence,
                complexity: item.complexity,
                relationship_path: item.relationship_path,
              };
            })
            .filter((s) => Boolean(s.query));
          setDynamicSuggestions(normalized);
        } else {
          setDynamicSuggestions([]);
        }
      })
      .catch(() => {
        if (active) setDynamicSuggestions([]);
      })
      .finally(() => {
        if (active) setIsLoadingSuggestions(false);
      });

    return () => {
      active = false;
    };
  }, [activeDocNames]);

  const toggleSourceDoc = (id: string) => {
    const docToToggle = sourceDocs.find((d) => d.id === id);
    const docName = docToToggle?.name;
    const willBeSelected = docToToggle ? !docToToggle.selected : false;

    setSourceDocs((prev) => {
      const updated = prev.map((doc) => (doc.id === id ? { ...doc, selected: !doc.selected } : doc));
      if (currentSessionId && currentSessionId !== 'new') {
        const activeIds = updated.filter((d) => d.selected).map((d) => d.id);
        const activeNames = updated.filter((d) => d.selected).map((d) => d.name);
        setSessions((prevSessions) => {
          return prevSessions.map((s) =>
            s.id === currentSessionId ? { ...s, selectedSourceIds: activeIds, sources: updated, attached_docs: activeNames } : s
          );
        });
        if (docName) {
          if (willBeSelected) {
            chatService.attachToSessionDrawer?.(currentSessionId, docName).catch(() => {});
          } else {
            chatService.removeFromSessionDrawer?.(currentSessionId, docName).catch(() => {});
          }
        }
        chatService.updateSessionDrawer?.(currentSessionId, activeNames).catch(() => {});
      }
      return updated;
    });
  };

  const removeAttachedFile = (id: string) => {
    toggleSourceDoc(id);
  };

  const handleDeleteSourceDoc = (id: string, _name?: string) => {
    const docToDelete = sourceDocs.find((d) => d.id === id);
    const docName = _name || docToDelete?.name;
    setSourceDocs((prev) => {
      const updated = prev.filter((doc) => doc.id !== id);
      if (currentSessionId && currentSessionId !== 'new') {
        const activeIds = updated.filter((d) => d.selected).map((d) => d.id);
        const activeNames = updated.filter((d) => d.selected).map((d) => d.name);
        setSessions((prevSessions) => {
          return prevSessions.map((s) =>
            s.id === currentSessionId ? { ...s, selectedSourceIds: activeIds, sources: updated, attached_docs: activeNames } : s
          );
        });
        if (docName) {
          chatService.removeFromSessionDrawer?.(currentSessionId, docName).catch(() => {});
        }
        chatService.updateSessionDrawer?.(currentSessionId, activeNames).catch(() => {});
      }
      return updated;
    });
    // NOTE: Removing from chat dock or drawer only detaches it from the current chat session.
    // It does NOT delete it from the Knowledge Base Library or prune its GraphRAG embeddings.
  };

  const [addSourceMenuOpen, setAddSourceMenuOpen] = useState<'input' | 'drawer' | null>(null);
  const [isLibraryPickerOpen, setIsLibraryPickerOpen] = useState(false);

  // Close add source popover menus on outside click or ESC
  useEffect(() => {
    if (!addSourceMenuOpen) return;
    const handleOutside = (e: MouseEvent | TouchEvent) => {
      const target = e.target as HTMLElement | null;
      if (target?.closest('[data-add-source-container]')) return;
      setAddSourceMenuOpen(null);
    };
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setAddSourceMenuOpen(null);
    };
    window.addEventListener('mousedown', handleOutside);
    window.addEventListener('touchstart', handleOutside, { passive: true });
    window.addEventListener('keydown', handleEscape);
    return () => {
      window.removeEventListener('mousedown', handleOutside);
      window.removeEventListener('touchstart', handleOutside);
      window.removeEventListener('keydown', handleEscape);
    };
  }, [addSourceMenuOpen]);

  // Attach a pre-indexed document from the Library directly to current chat session
  const handleSelectLibraryDocument = (item: LibraryItem) => {
    setSourceDocs((prev) => {
      const existing = prev.find(
        (d) => d.name.toLowerCase() === item.name.toLowerCase() || d.id === item.id
      );
      let updated: SourceDocument[];
      const isDetaching = existing ? existing.selected : false;

      if (existing) {
        // Toggle active selection state
        updated = prev.map((d) =>
          d.id === existing.id || d.name.toLowerCase() === item.name.toLowerCase()
            ? { ...d, selected: !d.selected }
            : d
        );
      } else {
        const newDoc: SourceDocument = {
          id: item.id.startsWith('src-') ? item.id : `src-${item.id}`,
          name: item.name,
          size: item.size,
          bytes: item.bytes,
          pages: item.pages || 1,
          color: item.color,
          selected: true,
          status: 'ready',
        };
        updated = [...prev, newDoc];
      }

      if (currentSessionId && currentSessionId !== 'new') {
        const activeIds = updated.filter((d) => d.selected).map((d) => d.id);
        const activeNames = updated.filter((d) => d.selected).map((d) => d.name);
        setSessions((prevSessions) => {
          return prevSessions.map((s) =>
            s.id === currentSessionId ? { ...s, selectedSourceIds: activeIds, sources: updated, attached_docs: activeNames } : s
          );
        });

        if (isDetaching) {
          chatService.removeFromSessionDrawer?.(currentSessionId, item.name).catch(() => {});
        } else {
          chatService.attachToSessionDrawer?.(currentSessionId, item.name).catch(() => {});
        }
        chatService.updateSessionDrawer?.(currentSessionId, activeNames).catch(() => {});
      }
      return updated;
    });
  };

  const selectedDocs = sourceDocs.filter((doc) => doc.selected);
  const activeSourcesCount = selectedDocs.length;

  const handleOpenPdfViewer = (filename: string, pageNumber: number = 1, heading?: string) => {
    setSelectedCitation({
      citation_index: 1,
      chunk_id: `view-${filename}-${pageNumber}`,
      document_id: filename,
      pdf_filename: filename,
      primary_page: pageNumber,
      heading: heading || filename,
      plain_text: `Viewing document ${filename} (page ${pageNumber}) from research drawer.`,
      university: 'Research Vault',
      similarity: 1.0,
    });
    openModal('pdf');
  };

  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const contentContainerRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const isUserAbortingRef = useRef<boolean>(false);
  const isUnmountedRef = useRef<boolean>(false);
  const latestStreamedTextRef = useRef<string>('');

  // Clean unmount cancellation without showing error UI
  useEffect(() => {
    return () => {
      isUnmountedRef.current = true;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Dynamically adjust textarea height when typing, expanding smoothly with responsive resize awareness
  useEffect(() => {
    const handleResize = () => {
      const textarea = textareaRef.current;
      if (!textarea) return;
      const isDesktop = typeof window !== 'undefined' && window.innerWidth >= 640;
      const isNewChat = conversation.length === 0;

      if (!isDesktop) {
        // Mobile / Small Screens (< 640px): strictly compact single-line pill when empty
        textarea.style.height = 'auto';
        const scrollH = textarea.scrollHeight;
        if (!query.trim()) {
          textarea.style.height = `${Math.max(scrollH, 22)}px`;
        } else {
          textarea.style.height = `${Math.min(Math.max(scrollH, 22), 96)}px`;
        }
        return;
      }

      // Desktop (>= 640px):
      textarea.style.height = 'auto';
      const baseMin = isNewChat ? 52 : (query.length > 0 ? 36 : 28);
      const scrollH = textarea.scrollHeight;
      const computedH = !query.trim() ? Math.max(scrollH, 28) : Math.max(scrollH, baseMin);
      const maxH = isNewChat ? 220 : 140;
      textarea.style.height = `${Math.min(computedH, maxH)}px`;
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [query, conversation.length]);

  // Global Keyboard Navigation Shortcuts:
  // • Cmd/Ctrl + K -> Focus query input from anywhere
  // • Cmd/Ctrl + / -> Open/toggle Settings modal
  // • Esc -> Close any open modal/drawer/dropdown
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      const isCmdOrCtrl = e.metaKey || e.ctrlKey;

      // 1. Cmd/Ctrl + K: Focus query input from anywhere
      if (isCmdOrCtrl && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        textareaRef.current?.focus();
        textareaRef.current?.select();
        return;
      }

      // 2. Cmd/Ctrl + /: Open Settings modal
      if (isCmdOrCtrl && e.key === '/') {
        e.preventDefault();
        toggleSettingsJunction();
        return;
      }

      // 3. Esc: Close any open modal / drawer / popup
      if (e.key === 'Escape') {
        let closedSomething = false;

        if (isSearchModalOpen) {
          setIsSearchModalOpen(false);
          closedSomething = true;
        }
        if (isSettingsOpen || isTunerMode) {
          setIsSettingsOpen(false);
          setIsTunerMode(false);
          setShowOutsideClickTip(false);
          closedSomething = true;
        }
        if (isSourcesDrawerOpen) {
          setIsSourcesDrawerOpen(false);
          closedSomething = true;
        }
        if (isPipelineDrawerOpen) {
          setIsPipelineDrawerOpen(false);
          closedSomething = true;
        }
        if (isLibraryPickerOpen) {
          setIsLibraryPickerOpen(false);
          closedSomething = true;
        }
        if (activeModal === 'pdf' || selectedCitation) {
          closeModal();
          closedSomething = true;
        }
        if (addSourceMenuOpen) {
          setAddSourceMenuOpen(null);
          closedSomething = true;
        }
        if (activeSessionMenuId) {
          setActiveSessionMenuId(null);
          closedSomething = true;
        }
        if (expandedQVersionsIndex !== null) {
          setExpandedQVersionsIndex(null);
          closedSomething = true;
        }
        if (expandedRespVersionsIndex !== null) {
          setExpandedRespVersionsIndex(null);
          closedSomething = true;
        }
        if (showSuggestions) {
          setShowSuggestions(false);
          setActiveSuggestionIndex(-1);
          closedSomething = true;
        }
        if (isUserMenuOpen) {
          setIsUserMenuOpen(false);
          closedSomething = true;
        }
        if (editingMessageIndex !== null) {
          setEditingMessageIndex(null);
          closedSomething = true;
        }

        if (closedSomething) {
          e.preventDefault();
        }
      }
    };

    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, [
    isSearchModalOpen,
    isSettingsOpen,
    isTunerMode,
    isSourcesDrawerOpen,
    isPipelineDrawerOpen,
    isLibraryPickerOpen,
    activeModal,
    selectedCitation,
    addSourceMenuOpen,
    activeSessionMenuId,
    expandedQVersionsIndex,
    expandedRespVersionsIndex,
    showSuggestions,
    isUserMenuOpen,
    editingMessageIndex,
    closeModal,
  ]);


  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (isUserMenuOpen && userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setIsUserMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [isUserMenuOpen]);

  const [isAutoScrollLocked, setIsAutoScrollLocked] = useState(false);
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);
  const [activeExecutingQuery, setActiveExecutingQuery] = useState<string>('');

  const createErrorDetails = (apiErr?: any, rawError?: any): BackendErrorDetails => {
    const isAborted =
      isUserAbortingRef.current ||
      apiErr?.code === 'CLIENT_REQUEST_CANCELLED' ||
      rawError?.name === 'AbortError' ||
      (typeof rawError?.message === 'string' && rawError.message.toLowerCase().includes('abort'));
    const isTimeout =
      apiErr?.code === 'TIMEOUT' ||
      apiErr?.code === 'ETIMEDOUT' ||
      (typeof rawError?.message === 'string' && rawError.message.toLowerCase().includes('timeout'));
    const isOffline =
      !isAborted &&
      !isTimeout &&
      (apiErr?.code === 'BACKEND_UNREACHABLE' ||
        (rawError instanceof TypeError && rawError.message.includes('fetch')) ||
        (apiErr?.status === 0 && apiErr?.code !== 'CLIENT_REQUEST_CANCELLED'));

    let title = 'Backend Communication Failure';
    if (isAborted) {
      title = 'Response stopped';
    } else if (isTimeout) {
      title = 'Request Timeout Exceeded (60s)';
    } else if (isOffline) {
      title = 'Server is offline';
    } else if (apiErr?.code === 'SCHEMA_VALIDATION_FAILED') {
      title = 'Response Contract Schema Mismatch';
    } else if (apiErr?.status) {
      title = `Gateway Error (HTTP ${apiErr.status})`;
    }

    return {
      title,
      message:
        isAborted
          ? 'Response stopped.'
          : isOffline
            ? 'The backend server is currently offline or unreachable. Please check if the server is running.'
            : apiErr?.message ||
              (typeof rawError?.message === 'string'
                ? rawError.message
                : 'Failed to communicate with the backend server.'),
      cause:
        isAborted || isOffline
          ? undefined
          : apiErr?.likelyCause,
      action:
        isAborted || isOffline
          ? undefined
          : apiErr?.recommendedAction || 'Inspect request parameters and retry.',
      status: isAborted ? undefined : apiErr?.status,
      isOffline,
      isTimeout,
      isAborted,
    };
  };

  const handleAbortActiveQuery = () => {
    isUserAbortingRef.current = true;
    terminalLogger.info('Query execution stopped by user.', {
      session_id: currentSessionId,
    });
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setIsLoading(false);
    setRegeneratingIndex(null);
    setActiveExecutingQuery('');
  };

  const getFormattedChatHistory = (msgs: ChatMessage[]): { human: string; ai: string }[] => {
    const history: { human: string; ai: string }[] = [];
    for (let idx = 0; idx < msgs.length; idx += 2) {
      const u = msgs[idx];
      const a = msgs[idx + 1];
      if (u && u.role === 'user' && a && a.role === 'assistant' && a.text && !a.error) {
        history.push({
          human: u.text,
          ai: a.text,
        });
      }
    }
    return history.slice(-6);
  };

  // Print startup connection confirmation in console as requested
  useEffect(() => {
    const printConnectionAudit = async () => {
      await runCapabilityProbe();
      const caps = await systemService.probeCapabilities();
      const currentMode = useModeStore.getState().appMode;
      const currentUrl = useModeStore.getState().apiBaseUrl;

      let targetHost = currentUrl;
      try {
        const urlObj = new URL(currentUrl);
        targetHost = `${urlObj.hostname}${urlObj.port ? `:${urlObj.port}` : ''}`;
      } catch {
        targetHost = currentUrl;
      }

      let telemData: any = null;
      if (caps.hardwareTelemetryAvailable) {
        try {
          const tRes = await systemService.getHardwareTelemetry();
          if (tRes?.data) telemData = tRes.data;
        } catch {}
      }

      let neoData: any = null;
      if (caps.neo4jStatusAvailable) {
        try {
          const nRes = await systemService.getNeo4jStatus();
          if (nRes?.data) neoData = nRes.data;
        } catch {}
      }

      const gatewayStatus =
        currentMode === 'mock'
          ? 'SIMULATED (Offline Fixture)'
          : caps.apiReachable
          ? `CONNECTED (${targetHost})`
          : `OFFLINE (${targetHost} Unreachable)`;

      const neo4jStatus =
        currentMode === 'mock'
          ? 'SIMULATED (Local Graph Fixture)'
          : neoData?.connected && neoData?.uri
          ? `CONNECTED (${neoData.uri}${neoData.total_nodes !== undefined ? ` • ${neoData.total_nodes} nodes` : ''})`
          : caps.neo4jStatusAvailable
          ? `CONNECTED (${neoData?.uri || 'Graph Substrate'})`
          : 'DISCONNECTED';

      const vectorStatus =
        currentMode === 'mock'
          ? 'SIMULATED (Local Vector Fixture)'
          : caps.searchAvailable
          ? `CONNECTED (${telemData?.embedding_model || 'Vector Substrate'})`
          : 'LOCAL / OFFLINE';

      const vllmStatus =
        currentMode === 'mock'
          ? 'SIMULATED (Local Mock Engine)'
          : caps.chatAvailable && caps.apiReachable
          ? `ONLINE (${telemData?.gpu_model && telemData.gpu_model !== 'Unknown GPU' ? telemData.gpu_model : 'Active Pipeline'})`
          : 'OFFLINE (Gateway Unreachable)';

      let detectedClient = 'Web Client';
      if (typeof navigator !== 'undefined') {
        const ua = navigator.userAgent;
        if (ua.includes('Macintosh') || ua.includes('Mac OS')) {
          detectedClient = 'macOS Client';
        } else if (ua.includes('Windows')) {
          detectedClient = 'Windows Client';
        } else if (ua.includes('Linux')) {
          detectedClient = 'Linux Client';
        } else if (ua.includes('iPhone') || ua.includes('iPad')) {
          detectedClient = 'iOS Mobile Device';
        } else if (ua.includes('Android')) {
          detectedClient = 'Android Mobile Device';
        }
      }

      console.log(
        `%c┌─────────────────────────────────────────────────────────────┐\n` +
        `│             RAISE ADVANCED RAG PIPELINE SYSTEM              │\n` +
        `│                  Connection Status Audit                    │\n` +
        `├─────────────────────────────────────────────────────────────┤\n` +
        `│ • Client Device:       ${detectedClient.slice(0, 37).padEnd(37)}│\n` +
        `│ • Operational Mode:    ${currentMode.toUpperCase().slice(0, 37).padEnd(37)}│\n` +
        `│ • Gateway URL:         ${currentUrl.slice(0, 37).padEnd(37)}│\n` +
        `│ • FastAPI Gateway:     ${gatewayStatus.slice(0, 37).padEnd(37)}│\n` +
        `│ • ChromaDB Substrate:  ${vectorStatus.slice(0, 37).padEnd(37)}│\n` +
        `│ • Neo4j Bolt Graph:    ${neo4jStatus.slice(0, 37).padEnd(37)}│\n` +
        `│ • Inference Engine:    ${vllmStatus.slice(0, 37).padEnd(37)}│\n` +
        `└─────────────────────────────────────────────────────────────┘`,
        'color: #818cf8; font-weight: bold; font-family: monospace;'
      );
    };

    printConnectionAudit();
  }, []);

  useEffect(() => {
    if (!isAutoScrollLocked) {
      if (typeof messagesEndRef.current?.scrollIntoView === 'function') {
        messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
      }
    }
  }, [conversation, isLoading, isAutoScrollLocked]);

  const scrollToBottom = () => {
    setIsAutoScrollLocked(false);
    setShowScrollToBottom(false);
    if (typeof messagesEndRef.current?.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  // Smart scroll & mouse movement detection:
  // - Only displays "Scroll to bottom" button when the page has scrollable overflow AND content exists below the fold
  // - When everything fits on screen or user is already at the bottom, button is strictly hidden
  useEffect(() => {
    if (conversation.length === 0) {
      setIsAutoScrollLocked(false);
      setShowScrollToBottom(false);
      return;
    }

    const isContentBelowFold = (): boolean => {
      if (conversation.length === 0) return false;
      const container = contentContainerRef.current;
      const scrollHeight = container
        ? container.scrollHeight
        : (document.documentElement.scrollHeight || document.body.scrollHeight);
      const clientHeight = container ? container.clientHeight : window.innerHeight;
      // If the document has no overflow (entire content fits in screen), nothing below
      if (scrollHeight <= clientHeight + 60) return false;

      // Check if end of messages is already visible in viewport
      if (messagesEndRef.current) {
        const rect = messagesEndRef.current.getBoundingClientRect();
        if (rect.top <= clientHeight + 40) {
          return false;
        }
      }

      const scrollTop = container ? container.scrollTop : (window.scrollY || document.documentElement.scrollTop);
      const distanceFromBottom = scrollHeight - (scrollTop + clientHeight);
      return distanceFromBottom > 90;
    };

    const checkScrollPosition = () => {
      if (isContentBelowFold()) {
        setIsAutoScrollLocked(true);
        setShowScrollToBottom(true);
      } else {
        setIsAutoScrollLocked(false);
        setShowScrollToBottom(false);
      }
    };

    const handleWheel = (e: WheelEvent) => {
      if (e.deltaY < -4) {
        // User scrolled upward, verify if there is actually content below
        if (isContentBelowFold()) {
          setIsAutoScrollLocked(true);
          setShowScrollToBottom(true);
        } else {
          setIsAutoScrollLocked(false);
          setShowScrollToBottom(false);
        }
      } else if (e.deltaY > 4) {
        if (!isContentBelowFold()) {
          setIsAutoScrollLocked(false);
          setShowScrollToBottom(false);
        }
      }
    };

    const timer = setTimeout(() => {
      if (!isContentBelowFold()) {
        setIsAutoScrollLocked(false);
        setShowScrollToBottom(false);
      }
    }, 100);

    const containerEl = contentContainerRef.current;
    containerEl?.addEventListener('scroll', checkScrollPosition, { passive: true });
    window.addEventListener('scroll', checkScrollPosition, { passive: true });
    window.addEventListener('wheel', handleWheel, { passive: true });
    window.addEventListener('resize', checkScrollPosition, { passive: true });

    return () => {
      clearTimeout(timer);
      containerEl?.removeEventListener('scroll', checkScrollPosition);
      window.removeEventListener('scroll', checkScrollPosition);
      window.removeEventListener('wheel', handleWheel);
      window.removeEventListener('resize', checkScrollPosition);
    };
  }, [conversation.length]);

  useEffect(() => {
    return () => {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const handleToggleSpeak = (text: string, id: string) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      return;
    }
    if (isListening) {
      stopVoiceListening();
    }
    if (speakingMessageId === id) {
      window.speechSynthesis.cancel();
      setSpeakingMessageId(null);
      return;
    }
    window.speechSynthesis.cancel();
    const clean = cleanTextForSpeech(text);
    if (!clean) return;

    const utterance = new SpeechSynthesisUtterance(clean);
    const allVoices = window.speechSynthesis.getVoices();
    const voice = selectBestSpeechVoice(allVoices, selectedVoiceName);

    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang;
    } else {
      utterance.lang = 'en-US';
    }

    // Natural cadence and pitch
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    utterance.onend = () => setSpeakingMessageId(null);
    utterance.onerror = () => setSpeakingMessageId(null);
    setSpeakingMessageId(id);
    window.speechSynthesis.speak(utterance);
  };

  const handleTestVoiceSample = () => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
    if (isVoiceSamplePlaying) {
      window.speechSynthesis.cancel();
      setIsVoiceSamplePlaying(false);
      return;
    }
    window.speechSynthesis.cancel();
    const sample = 'Hello! I am your Raise AI assistant. This is a preview of the selected voice.';
    const utterance = new SpeechSynthesisUtterance(sample);
    const allVoices = window.speechSynthesis.getVoices();
    const voice = selectBestSpeechVoice(allVoices, selectedVoiceName);

    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang;
    } else {
      utterance.lang = 'en-US';
    }

    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    utterance.onend = () => setIsVoiceSamplePlaying(false);
    utterance.onerror = () => setIsVoiceSamplePlaying(false);
    setIsVoiceSamplePlaying(true);
    window.speechSynthesis.speak(utterance);
  };

  const handleToggleVoiceQuery = () => {
    if (typeof window === 'undefined') return;

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setVoiceError('Voice query is not supported in this browser. Please use Chrome, Edge, Safari, or a Chromium browser.');
      setTimeout(() => setVoiceError(null), 5000);
      return;
    }

    // If currently listening, clicking either microphone button or X stops it
    if (isListening) {
      stopVoiceListening();
      return;
    }

    // If text-to-speech is playing, cancel it to avoid mic feedback
    if ('speechSynthesis' in window && window.speechSynthesis.speaking) {
      window.speechSynthesis.cancel();
      setSpeakingMessageId(null);
    }

    try {
      setVoiceError(null);
      baseQueryRef.current = query;

      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      const triggerSpeaking = (durationMs = 900) => {
        setIsVoiceSpeaking(true);
        if (speechTimeoutRef.current) {
          clearTimeout(speechTimeoutRef.current);
        }
        speechTimeoutRef.current = setTimeout(() => {
          setIsVoiceSpeaking(false);
        }, durationMs);
      };

      recognition.onstart = () => {
        setIsListening(true);
        setIsVoiceSpeaking(false);
        setVoiceDurationSec(0);
        if (voiceTimerRef.current) clearInterval(voiceTimerRef.current);
        voiceTimerRef.current = setInterval(() => {
          setVoiceDurationSec((prev) => prev + 1);
        }, 1000);
      };

      recognition.onspeechstart = () => {
        triggerSpeaking(1200);
      };

      recognition.onspeechend = () => {
        setIsVoiceSpeaking(false);
      };

      recognition.onsoundstart = () => {
        triggerSpeaking(1000);
      };

      recognition.onsoundend = () => {
        setIsVoiceSpeaking(false);
      };

      recognition.onaudiostart = () => {
        triggerSpeaking(800);
      };

      recognition.onresult = (event: any) => {
        triggerSpeaking(1100);
        let transcript = '';
        for (let i = 0; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        const base = baseQueryRef.current.trim();
        const speech = transcript.trim();
        const combined = base ? `${base} ${speech}` : speech;
        setQuery(combined);
        textareaRef.current?.focus();
      };

      recognition.onerror = (event: any) => {
        console.warn('Speech recognition error:', event.error);
        if (event.error === 'not-allowed') {
          setVoiceError('Microphone permission denied. Please allow microphone access in your browser.');
        } else if (event.error === 'no-speech') {
          // No speech detected, quietly ignore
        } else {
          setVoiceError(`Voice recognition error: ${event.error}`);
        }
        stopVoiceListening();
        setTimeout(() => setVoiceError(null), 5000);
      };

      recognition.onend = () => {
        stopVoiceListening();
      };

      recognitionRef.current = recognition;
      recognition.start();

      // Connect to Web Audio Analyser for real-time frequency & volume waveform visualization
      if (typeof navigator !== 'undefined' && navigator.mediaDevices?.getUserMedia) {
        navigator.mediaDevices
          .getUserMedia({ audio: true })
          .then((stream) => {
            if (!recognitionRef.current) {
              stream.getTracks().forEach((t) => t.stop());
              return;
            }
            audioStreamRef.current = stream;
            const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
            if (AudioCtx) {
              const ctx = new AudioCtx();
              audioContextRef.current = ctx;
              const source = ctx.createMediaStreamSource(stream);
              const analyser = ctx.createAnalyser();
              analyser.fftSize = 64;
              analyser.smoothingTimeConstant = 0.4;
              source.connect(analyser);
              audioAnalyserRef.current = analyser;

              const bufferLength = analyser.frequencyBinCount;
              const dataArray = new Uint8Array(bufferLength);

              const loop = () => {
                if (!audioAnalyserRef.current) return;
                audioAnalyserRef.current.getByteFrequencyData(dataArray);

                const numBars = 7;
                const step = Math.max(1, Math.floor(bufferLength / numBars));
                const newLevels: number[] = [];
                let sum = 0;

                for (let i = 0; i < numBars; i++) {
                  const val = dataArray[i * step] || 0;
                  sum += val;
                  const normalized = Math.min(1.8, Math.max(0.25, (val / 140) * 1.5));
                  newLevels.push(normalized);
                }

                if (sum / numBars > 12) {
                  triggerSpeaking(500);
                }
                setVoiceAudioLevels(newLevels);
                audioAnimFrameRef.current = requestAnimationFrame(loop);
              };

              audioAnimFrameRef.current = requestAnimationFrame(loop);
            }
          })
          .catch(() => {
            // Graceful fallback to recognition speech events
          });
      }
    } catch (err: any) {
      console.error('Failed to start speech recognition:', err);
      setVoiceError('Could not start microphone. Check browser permissions.');
      stopVoiceListening();
      setTimeout(() => setVoiceError(null), 5000);
    }
  };

  const handleCopyText = (text: string, key: string) => {
    copyMarkdownToClipboard(text);
    setCopiedKey(key);
    setTimeout(() => {
      setCopiedKey((prev) => (prev === key ? null : prev));
    }, 2000);
  };

  const isResponsePersisted = (data: any): boolean => {
    if (!data) return false;
    if (
      data.persisted === false ||
      data.saved === false ||
      data.persistence_status === 'failed' ||
      data.persistence_status === 'error' ||
      Boolean(data.persistence_error)
    ) {
      return false;
    }
    return true;
  };

  const updateSessionInMemory = (messages: ChatMessage[], effectiveSessionId: string) => {
    const currentActiveSourceIds = sourceDocs.filter((d) => d.selected).map((d) => d.id);
    const username = getStoredUsername();
    const firstUserMsg = messages.find((m) => m.role === 'user')?.text || 'New Chat';
    const newTitle = truncateSessionTitle(firstUserMsg, 44);
    const dateFormatted = formatSessionDate(new Date());

    setSessions((prev) => {
      const existing = prev.find((s) => s.id === effectiveSessionId);
      const updatedSession: ChatSession = existing
        ? {
            ...existing,
            title: newTitle && newTitle !== 'New Chat' ? newTitle : existing.title,
            messages,
            timestamp: dateFormatted,
            updated_at: new Date().toISOString(),
            selectedSourceIds: currentActiveSourceIds,
            sources: sourceDocs,
          }
        : {
            id: effectiveSessionId,
            thread_id: effectiveSessionId,
            session_id: effectiveSessionId,
            username,
            title: newTitle,
            timestamp: dateFormatted,
            messages,
            selectedSourceIds: currentActiveSourceIds,
            sources: sourceDocs,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          };

      const remaining = prev.filter((s) => s.id !== effectiveSessionId);
      return [updatedSession, ...remaining];
    });
  };



  const handleSelectSession = (session: ChatSession) => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    setSpeakingMessageId(null);
    setEditingMessageIndex(null);
    setRegeneratingIndex(null);
    setCopiedKey(null);
    setExpandedQVersionsIndex(null);
    setExpandedRespVersionsIndex(null);
    setIsAutoScrollLocked(false);
    setShowScrollToBottom(false);
    setCurrentSessionId(session.id);
    setConversation(session.messages || []);
    const sessionSources = session.sources ?? [];
    setSourceDocs(sessionSources);
    setIsPipelineDrawerOpen(false);

    // Rehydrate drawer from backend for this specific session (per-chat drawer isolation)
    chatService.getSessionDrawer?.(session.id).then((res) => {
      if (res?.data && Array.isArray(res.data.attached_docs)) {
        const attachedNames = res.data.attached_docs;
        const enrichedDocs = Array.isArray(res.data.documents) ? res.data.documents : [];
        const reconstructedSources: SourceDocument[] = attachedNames.map((name: string, idx: number) => {
          const matched = enrichedDocs.find((d: any) => d.filename === name || d.id === name);
          const szMb = matched?.size_mb || 1.0;
          return {
            id: matched?.id || matched?.doc_id || `src-${idx}-${name}`,
            name,
            size: szMb >= 1 ? `${szMb.toFixed(1)} MB` : `${Math.round(szMb * 1024)} KB`,
            bytes: Math.round(szMb * 1024 * 1024),
            pages: matched?.pages || 1,
            color: name.endsWith('.pdf') ? 'rose' : 'indigo',
            selected: true,
            status: 'ready',
          };
        });
        setSourceDocs(reconstructedSources);
        setSessions((prev) =>
          prev.map((s) =>
            s.id === session.id
              ? {
                  ...s,
                  sources: reconstructedSources,
                  attached_docs: attachedNames,
                  selectedSourceIds: reconstructedSources.map((d) => d.id),
                }
              : s
          )
        );
      } else {
        setSourceDocs(session.sources ?? []);
      }
    }).catch(() => {
      setSourceDocs(session.sources ?? []);
    });

    // Call GET /api/chat/history?session_id={thread_id} to ensure latest messages from PostgreSQL
    chatService.getChatHistory?.(session.id).then((res) => {
      if (res?.data?.messages && Array.isArray(res.data.messages) && res.data.messages.length > 0) {
        setConversation(res.data.messages);
      }
    }).catch(() => {});
  };

  const handleNewChat = () => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    chatService.clearChat?.(currentSessionId || undefined).catch(() => {});
    setSpeakingMessageId(null);
    setEditingMessageIndex(null);
    setRegeneratingIndex(null);
    setCopiedKey(null);
    setExpandedQVersionsIndex(null);
    setExpandedRespVersionsIndex(null);
    setIsAutoScrollLocked(false);
    setShowScrollToBottom(false);

    // "New Chat" button creates a new thread_id UUID
    const newThreadId = generateUUID();
    setCurrentSessionId(newThreadId);

    setConversation([]);
    setSourceDocs([]);
    setIsPipelineDrawerOpen(false);
    setQuery('');
    setPlaceholderText('');
    setPromptIndex(0);
    setIsDeleting(false);
  };

  const handleLogout = () => {
    setIsUserMenuOpen(false);
    setIsPipelineDrawerOpen(false);
    setUsername('Operator');
    setApiKey('');
    setStoredUsername('Operator');
    setStoredApiKey('');
    clearTunnelUrl();
    setSessions([]);
    setConversation([]);
    setSourceDocs([]);
    setCurrentSessionId(null);
    setPinnedSessionIds([]);
    try {
      localStorage.removeItem('raise_chat_sessions');
      localStorage.removeItem('raise_current_session_id');
      localStorage.removeItem('raise_active_conversation');
      localStorage.removeItem('raise_pinned_sessions');
      localStorage.removeItem('raise_archived_sessions');
    } catch {}
    handleNewChat();
  };

  const handleDeleteSession = (sessionId: string) => {
    // Delete on PostgreSQL backend
    chatService.deleteChatSession?.(sessionId).catch((err) => {
      console.warn('Failed to delete chat session on backend:', err);
    });

    setSessions((prev) => prev.filter((s) => s.id !== sessionId));

    if (currentSessionId === sessionId) {
      handleNewChat();
    }
  };

  // Permanently clear all chat sessions across backend (PostgreSQL) and browser storage
  const handleDeleteAllChats = async () => {
    try {
      // 1. Tell backend to purge database history
      await chatService.clearChat?.();
    } catch (err) {
      console.warn('Backend clearChat error:', err);
    }

    // 2. Also delete individual sessions if backend supports DELETE /api/chat/sessions/{id}
    if (sessions.length > 0) {
      await Promise.allSettled(
        sessions.map((s) => chatService.deleteChatSession?.(s.id))
      );
    }

    // 4. Reset local React state
    setSessions([]);
    setPinnedSessionIds([]);
    setCurrentSessionId(null);
    setConversation([]);
    setSourceDocs([]);
    handleNewChat();

    // 5. Guarantee sync with backend
    try {
      const username = getStoredUsername();
      const res = await chatService.listChatSessions?.(username);
      if (res?.data && Array.isArray(res.data)) {
        const synced = res.data.map((item: any) => ({
          id: item.thread_id || item.session_id || item.id,
          thread_id: item.thread_id || item.session_id || item.id,
          session_id: item.thread_id || item.session_id || item.id,
          title: item.title || 'Chat Session',
          timestamp: item.timestamp || formatSessionDate(item.updated_at || item.created_at),
          messages: Array.isArray(item.messages) ? item.messages : [],
          selectedSourceIds: item.selectedSourceIds || [],
          sources: item.sources || [],
        }));
        setSessions(synced);
      }
    } catch {}
  };

  const handleSaveRename = (sessionId: string) => {
    const trimmed = newSessionTitle.trim();
    if (trimmed) {
      const username = getStoredUsername();
      // Rename on PostgreSQL backend
      chatService.renameChatSession?.(sessionId, trimmed, username).catch((err) => {
        console.warn('Failed to rename chat session on backend:', err);
      });

      setSessions((prev) => {
        const updated = prev.map((s) => (s.id === sessionId ? { ...s, title: trimmed, updated_at: new Date().toISOString() } : s));
        return updated;
      });
    }
    setRenamingSessionId(null);
  };

  const handleExecuteQuery = async () => {
    const q = query.trim();
    if (!q || isLoading) return;

    if (isListening) {
      stopVoiceListening();
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const initialQVer: QuestionVersion = {
      id: `qver-${Date.now()}`,
      question: q,
      responseVersions: [],
      currentResponseVersionIndex: 0,
      timestamp: 'Just now',
    };

    const userMsg: ChatMessage = {
      role: 'user',
      text: q,
      questionVersions: [initialQVer],
      currentQuestionVersionIndex: 0,
    };

    const updatedConversation = [...conversation, userMsg];
    setConversation(updatedConversation);
    setQuery('');
    setActiveExecutingQuery(q);
    setIsLoading(true);
    setIsAutoScrollLocked(false);
    setShowScrollToBottom(false);

    const threadId = currentSessionId || generateUUID();
    if (!currentSessionId) {
      setCurrentSessionId(threadId);
    }
    updateSessionInMemory(updatedConversation, threadId);
    const recentHistory = getFormattedChatHistory(conversation);
    const executionStartTime = performance.now();

    const activeDocNames = sourceDocs.filter((d) => d.selected).map((d) => d.name);
    const { hops: filterHops, topK: filterTopK, documentFilter: storeDocFilter } = useFilterStore.getState();
    latestStreamedTextRef.current = '';
    isUserAbortingRef.current = false;

    try {
      const queryTask = chatService.querySubgraph(
        {
          query: q,
          hops: filterHops ?? (parseMode === 'expert' ? 3 : 1),
          top_k: filterTopK ?? (parseMode === 'expert' ? 8 : 4),
          mode: parseMode,
          thread_id: threadId,
          chat_history: recentHistory,
          active_docs: activeDocNames,
          document_filter: storeDocFilter || (activeDocNames.length === 1 ? activeDocNames[0] : undefined),
          parser: 'docling',
          full_potential: parseMode === 'expert',
        },
        controller.signal,
        (_chunk, fullAccumulated) => {
          // Live progressive stream token updates into conversation
          const cleanText = sanitizeStreamText(fullAccumulated);
          latestStreamedTextRef.current = cleanText;
          setConversation((prev) => {
            const last = prev[prev.length - 1];
            if (last && last.role === 'assistant') {
              return [...prev.slice(0, -1), { ...last, text: cleanText }];
            }
            return [...prev, { role: 'assistant', text: cleanText }];
          });
        }
      );

      const res = appMode === 'connected'
        ? await ensureMinimumDuration(queryTask, 1000, controller.signal)
        : await queryTask;

      if (isUnmountedRef.current) return;
      const elapsedSec = parseFloat(((performance.now() - executionStartTime) / 1000).toFixed(1));

      let assistantMsg: ChatMessage;

      if (res.data) {
        const persisted = isResponsePersisted(res.data);
        assistantMsg = {
          role: 'assistant',
          text: sanitizeStreamText(res.data.grounded_answer),
          response: res.data,
          durationSec: elapsedSec,
          persistenceFailed: !persisted,
        };
      } else {
        const isManualAbort =
          isUserAbortingRef.current ||
          res.error?.code === 'CLIENT_REQUEST_CANCELLED' ||
          (typeof res.error?.message === 'string' && res.error.message.toLowerCase().includes('abort'));

        if (isManualAbort) {
          terminalLogger.info('Query execution stopped by user.', {
            session_id: threadId,
            elapsed_sec: elapsedSec,
          });
          assistantMsg = {
            role: 'assistant',
            text: latestStreamedTextRef.current,
            isStopped: true,
            durationSec: elapsedSec,
          };
        } else {
          const errorDetails = createErrorDetails(res.error, null);
          if (!errorDetails.isOffline) {
            showErrorPopup(errorDetails.title, errorDetails.message, async () => {
              if (appMode !== 'connected') {
                await runCapabilityProbe();
              }
              handleRegenerateResponse(updatedConversation.length);
            });
          }
          assistantMsg = {
            role: 'assistant',
            text: '',
            error: errorDetails,
            durationSec: elapsedSec,
          };
        }
      }

      const initialRespVer: ResponseVersion = {
        id: `resp-${Date.now()}`,
        text: assistantMsg.text,
        response: assistantMsg.response,
        error: assistantMsg.error,
        durationSec: elapsedSec,
        timestamp: 'Just now',
        isStopped: assistantMsg.isStopped,
      };

      userMsg.questionVersions = [
        {
          ...initialQVer,
          responseVersions: [initialRespVer],
          currentResponseVersionIndex: 0,
        },
      ];

      const finalMessages = [...updatedConversation, assistantMsg];
      setConversation(finalMessages);
      if (res.data && !assistantMsg.persistenceFailed) {
        updateSessionInMemory(finalMessages, threadId);
      }
    } catch (err: any) {
      if (isUnmountedRef.current) return;
      const elapsedSec = parseFloat(((performance.now() - executionStartTime) / 1000).toFixed(1));
      const isManualAbort =
        isUserAbortingRef.current ||
        err?.name === 'AbortError' ||
        err?.code === 'CLIENT_REQUEST_CANCELLED' ||
        (typeof err?.message === 'string' && err.message.toLowerCase().includes('abort'));

      if (isManualAbort) {
        terminalLogger.info('Query execution cancelled by user.', {
          session_id: threadId,
          elapsed_sec: elapsedSec,
        });
        const stoppedText = latestStreamedTextRef.current;
        const stoppedMsg: ChatMessage = {
          role: 'assistant',
          text: stoppedText,
          isStopped: true,
          durationSec: elapsedSec,
        };
        const initialRespVer: ResponseVersion = {
          id: `resp-${Date.now()}`,
          text: stoppedText,
          isStopped: true,
          durationSec: elapsedSec,
          timestamp: 'Just now',
        };
        userMsg.questionVersions = [
          {
            ...initialQVer,
            responseVersions: [initialRespVer],
            currentResponseVersionIndex: 0,
          },
        ];
        const finalMessages = [...updatedConversation, stoppedMsg];
        setConversation(finalMessages);
      } else {
        const errorDetails = createErrorDetails(null, err);
        if (!errorDetails.isOffline) {
          showErrorPopup(errorDetails.title, errorDetails.message, async () => {
            if (appMode !== 'connected') {
              await runCapabilityProbe();
            }
            handleRegenerateResponse(updatedConversation.length);
          });
        }
        const errorAssistantMsg: ChatMessage = {
          role: 'assistant',
          text: '',
          error: errorDetails,
          durationSec: elapsedSec,
        };
        const initialRespVer: ResponseVersion = {
          id: `resp-${Date.now()}`,
          text: '',
          error: errorDetails,
          durationSec: elapsedSec,
          timestamp: 'Just now',
        };
        userMsg.questionVersions = [
          {
            ...initialQVer,
            responseVersions: [initialRespVer],
            currentResponseVersionIndex: 0,
          },
        ];
        const finalMessages = [...updatedConversation, errorAssistantMsg];
        setConversation(finalMessages);
      }
    } finally {
      setIsLoading(false);
      setActiveExecutingQuery('');
      abortControllerRef.current = null;
      isUserAbortingRef.current = false;
      latestStreamedTextRef.current = '';
    }
  };

  const handleSaveEditedQuestion = async (userIndex: number, newQuestionText: string) => {
    const trimmed = newQuestionText.trim();
    if (!trimmed || isLoading) return;

    const userMsg = conversation[userIndex];
    if (!userMsg || userMsg.role !== 'user') return;

    const assistantIndex = userIndex + 1;
    const assistantMsg = conversation[assistantIndex]?.role === 'assistant' ? conversation[assistantIndex] : undefined;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    // Retrieve or initialize existing question versions
    const existingQVers = getTurnQuestionVersions(userMsg, assistantMsg);
    const currQIdx = userMsg.currentQuestionVersionIndex ?? (existingQVers.length - 1);

    // Ensure active response version is recorded on current question version
    if (existingQVers[currQIdx] && assistantMsg) {
      const respVersions = [...existingQVers[currQIdx].responseVersions];
      const currRespIdx = existingQVers[currQIdx].currentResponseVersionIndex ?? 0;
      if (respVersions[currRespIdx]) {
        respVersions[currRespIdx] = {
          ...respVersions[currRespIdx],
          text: assistantMsg.text,
          response: assistantMsg.response,
          error: assistantMsg.error,
        };
      } else if (assistantMsg.text || assistantMsg.error) {
        respVersions.push({
          id: `resp-${Date.now()}`,
          text: assistantMsg.text,
          response: assistantMsg.response,
          error: assistantMsg.error,
        });
      }
      existingQVers[currQIdx] = {
        ...existingQVers[currQIdx],
        responseVersions: respVersions,
      };
    }

    // Create the new question version
    const newQVer: QuestionVersion = {
      id: `qver-${Date.now()}`,
      question: trimmed,
      responseVersions: [],
      currentResponseVersionIndex: 0,
      timestamp: 'Just now',
    };

    const updatedQVers = [...existingQVers, newQVer];
    const newQIdx = updatedQVers.length - 1;

    // Optimistically update conversation
    const updatedConversation = [...conversation];
    updatedConversation[userIndex] = {
      ...userMsg,
      text: trimmed,
      questionVersions: updatedQVers,
      currentQuestionVersionIndex: newQIdx,
    };

    if (updatedConversation[assistantIndex] && updatedConversation[assistantIndex].role === 'assistant') {
      updatedConversation[assistantIndex] = {
        ...updatedConversation[assistantIndex],
        text: '',
        response: undefined,
        error: undefined,
      };
    } else {
      updatedConversation.splice(assistantIndex, 0, {
        role: 'assistant',
        text: '',
        response: undefined,
        error: undefined,
      });
    }

    setConversation(updatedConversation);
    setEditingMessageIndex(null);
    setRegeneratingIndex(assistantIndex);
    setActiveExecutingQuery(trimmed);
    setIsLoading(true);
    setIsAutoScrollLocked(false);
    setShowScrollToBottom(false);

    const threadId = currentSessionId || generateUUID();
    if (!currentSessionId) {
      setCurrentSessionId(threadId);
    }
    updateSessionInMemory(updatedConversation, threadId);
    const recentHistory = getFormattedChatHistory(updatedConversation.slice(0, userIndex));
    const executionStartTime = performance.now();

    const activeDocNames = sourceDocs.filter((d) => d.selected).map((d) => d.name);
    const { hops: filterHops, topK: filterTopK, documentFilter: storeDocFilter } = useFilterStore.getState();
    latestStreamedTextRef.current = '';
    isUserAbortingRef.current = false;

    try {
      const queryTask = chatService.querySubgraph(
        {
          query: trimmed,
          hops: filterHops ?? (parseMode === 'expert' ? 3 : 1),
          top_k: filterTopK ?? (parseMode === 'expert' ? 8 : 4),
          mode: parseMode,
          thread_id: threadId,
          chat_history: recentHistory,
          active_docs: activeDocNames,
          document_filter: storeDocFilter || (activeDocNames.length === 1 ? activeDocNames[0] : undefined),
          parser: 'docling',
          full_potential: parseMode === 'expert',
        },
        controller.signal,
        (_chunk, fullAccumulated) => {
          const cleanText = sanitizeStreamText(fullAccumulated);
          latestStreamedTextRef.current = cleanText;
          setConversation((prev) => {
            const updated = [...prev];
            if (updated[assistantIndex] && updated[assistantIndex].role === 'assistant') {
              updated[assistantIndex] = {
                ...updated[assistantIndex],
                text: cleanText,
              };
            }
            return updated;
          });
        }
      );

      const res = appMode === 'connected'
        ? await ensureMinimumDuration(queryTask, 1000, controller.signal)
        : await queryTask;

      if (isUnmountedRef.current) return;
      const elapsedSec = parseFloat(((performance.now() - executionStartTime) / 1000).toFixed(1));

      let answerText = '';
      let respData: Partial<SubgraphQueryResponse> | undefined;
      let errorDetails: BackendErrorDetails | undefined;
      let isStopped = false;
      const persisted = res.data ? isResponsePersisted(res.data) : false;

      if (res.data) {
        answerText = sanitizeStreamText(res.data.grounded_answer);
        respData = res.data;
      } else {
        const isManualAbort =
          isUserAbortingRef.current ||
          res.error?.code === 'CLIENT_REQUEST_CANCELLED' ||
          (typeof res.error?.message === 'string' && res.error.message.toLowerCase().includes('abort'));

        if (isManualAbort) {
          terminalLogger.info('Query execution stopped by user.', {
            session_id: threadId,
            elapsed_sec: elapsedSec,
          });
          answerText = latestStreamedTextRef.current;
          isStopped = true;
        } else {
          errorDetails = createErrorDetails(res.error, null);
          const isOfflineError = Boolean(errorDetails.isOffline);
          if (!isOfflineError) {
            showErrorPopup(errorDetails.title, errorDetails.message, async () => {
              if (appMode !== 'connected') {
                await runCapabilityProbe();
              }
              handleRegenerateResponse(assistantIndex);
            });
          }
        }
      }

      const initialRespForNewQ: ResponseVersion = {
        id: `resp-${Date.now()}`,
        text: answerText,
        response: respData,
        error: errorDetails,
        durationSec: elapsedSec,
        timestamp: 'Just now',
        isStopped,
      };

      updatedQVers[newQIdx] = {
        ...newQVer,
        responseVersions: [initialRespForNewQ],
        currentResponseVersionIndex: 0,
      };

      setConversation((prev) => {
        const updated = [...prev];
        updated[userIndex] = {
          ...updated[userIndex],
          text: trimmed,
          questionVersions: updatedQVers,
          currentQuestionVersionIndex: newQIdx,
        };
        if (updated[assistantIndex] && updated[assistantIndex].role === 'assistant') {
          updated[assistantIndex] = {
            ...updated[assistantIndex],
            text: answerText,
            response: respData,
            error: errorDetails,
            durationSec: elapsedSec,
            persistenceFailed: !persisted,
            isStopped,
          };
        }
        if (res.data && persisted) {
          updateSessionInMemory(updated, threadId);
        }
        return updated;
      });
    } catch (err: any) {
      if (isUnmountedRef.current) return;
      const elapsedSec = parseFloat(((performance.now() - executionStartTime) / 1000).toFixed(1));
      const isManualAbort =
        isUserAbortingRef.current ||
        err?.name === 'AbortError' ||
        err?.code === 'CLIENT_REQUEST_CANCELLED' ||
        (typeof err?.message === 'string' && err.message.toLowerCase().includes('abort'));

      if (isManualAbort) {
        terminalLogger.info('Query execution stopped by user.', {
          session_id: threadId,
          elapsed_sec: elapsedSec,
        });
        const stoppedText = latestStreamedTextRef.current;
        const initialRespForNewQ: ResponseVersion = {
          id: `resp-${Date.now()}`,
          text: stoppedText,
          isStopped: true,
          durationSec: elapsedSec,
          timestamp: 'Just now',
        };
        updatedQVers[newQIdx] = {
          ...newQVer,
          responseVersions: [initialRespForNewQ],
          currentResponseVersionIndex: 0,
        };
        setConversation((prev) => {
          const updated = [...prev];
          updated[userIndex] = {
            ...updated[userIndex],
            text: trimmed,
            questionVersions: updatedQVers,
            currentQuestionVersionIndex: newQIdx,
          };
          if (updated[assistantIndex] && updated[assistantIndex].role === 'assistant') {
            updated[assistantIndex] = {
              ...updated[assistantIndex],
              text: stoppedText,
              response: undefined,
              error: undefined,
              durationSec: elapsedSec,
              isStopped: true,
            };
          }
          return updated;
        });
      } else {
        const errorDetails = createErrorDetails(null, err);
        if (!errorDetails.isOffline) {
          showErrorPopup(errorDetails.title, errorDetails.message, async () => {
            if (appMode !== 'connected') {
              await runCapabilityProbe();
            }
            handleRegenerateResponse(assistantIndex);
          });
        }
        const initialRespForNewQ: ResponseVersion = {
          id: `resp-${Date.now()}`,
          text: '',
          error: errorDetails,
          durationSec: elapsedSec,
          timestamp: 'Just now',
        };
        updatedQVers[newQIdx] = {
          ...newQVer,
          responseVersions: [initialRespForNewQ],
          currentResponseVersionIndex: 0,
        };
        setConversation((prev) => {
          const updated = [...prev];
          updated[userIndex] = {
            ...updated[userIndex],
            text: trimmed,
            questionVersions: updatedQVers,
            currentQuestionVersionIndex: newQIdx,
          };
          if (updated[assistantIndex] && updated[assistantIndex].role === 'assistant') {
            updated[assistantIndex] = {
              ...updated[assistantIndex],
              text: '',
              response: undefined,
              error: errorDetails,
              durationSec: elapsedSec,
            };
          }
          return updated;
        });
      }
    } finally {
      setIsLoading(false);
      setRegeneratingIndex(null);
      setActiveExecutingQuery('');
      abortControllerRef.current = null;
      isUserAbortingRef.current = false;
      latestStreamedTextRef.current = '';
    }
  };

  const handleSwitchQuestionVersion = (userIndex: number, targetQIdx: number) => {
    setConversation((prev) => {
      const updated = [...prev];
      const userMsg = updated[userIndex];
      if (!userMsg || userMsg.role !== 'user') return prev;

      const assistantIndex = userIndex + 1;
      const assistantMsg = updated[assistantIndex]?.role === 'assistant' ? updated[assistantIndex] : undefined;

      const qVersions = getTurnQuestionVersions(userMsg, assistantMsg);
      if (targetQIdx < 0 || targetQIdx >= qVersions.length) return prev;

      // Sync active response on current question version before switching
      const currQIdx = userMsg.currentQuestionVersionIndex ?? (qVersions.length - 1);
      if (qVersions[currQIdx] && assistantMsg) {
        const currRespIdx = qVersions[currQIdx].currentResponseVersionIndex ?? 0;
        const respVersions = [...qVersions[currQIdx].responseVersions];
        if (respVersions[currRespIdx]) {
          respVersions[currRespIdx] = {
            ...respVersions[currRespIdx],
            text: assistantMsg.text,
            response: assistantMsg.response,
            error: assistantMsg.error,
            durationSec: assistantMsg.durationSec,
          };
        } else if (assistantMsg.text || assistantMsg.error) {
          respVersions.push({
            id: `resp-${Date.now()}`,
            text: assistantMsg.text,
            response: assistantMsg.response,
            error: assistantMsg.error,
            durationSec: assistantMsg.durationSec,
          });
        }
        qVersions[currQIdx] = {
          ...qVersions[currQIdx],
          responseVersions: respVersions,
        };
      }

      const targetQVer = qVersions[targetQIdx];
      const activeRespIdx = targetQVer.currentResponseVersionIndex ?? (targetQVer.responseVersions.length - 1);
      const activeResp = targetQVer.responseVersions[activeRespIdx] || targetQVer.responseVersions[0];

      updated[userIndex] = {
        ...userMsg,
        text: targetQVer.question,
        questionVersions: qVersions,
        currentQuestionVersionIndex: targetQIdx,
      };

      if (updated[assistantIndex] && updated[assistantIndex].role === 'assistant') {
        updated[assistantIndex] = {
          ...updated[assistantIndex],
          text: activeResp?.text || '',
          response: activeResp?.response,
          error: activeResp?.error,
          durationSec: activeResp?.durationSec,
        };
      }

      if (currentSessionId) {
        updateSessionInMemory(updated, currentSessionId);
      }
      return updated;
    });
  };

  const handleRegenerateResponse = async (assistantIndex: number) => {
    if (isLoading) return;
    const userIndex = assistantIndex - 1;
    if (userIndex < 0 || !conversation[userIndex] || conversation[userIndex].role !== 'user') return;

    const userMsg = conversation[userIndex];
    const assistantMsg = conversation[assistantIndex];

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const qVersions = getTurnQuestionVersions(userMsg, assistantMsg);
    const currQIdx = userMsg.currentQuestionVersionIndex ?? (qVersions.length - 1);
    const activeQVer = qVersions[currQIdx] || qVersions[0];
    const activeQuestion = activeQVer.question;

    setRegeneratingIndex(assistantIndex);
    setActiveExecutingQuery(activeQuestion);
    setIsLoading(true);

    const threadId = currentSessionId || generateUUID();
    if (!currentSessionId) {
      setCurrentSessionId(threadId);
    }
    const recentHistory = getFormattedChatHistory(conversation.slice(0, userIndex));
    const executionStartTime = performance.now();

    const activeDocNames = sourceDocs.filter((d) => d.selected).map((d) => d.name);
    const { hops: filterHops, topK: filterTopK, documentFilter: storeDocFilter } = useFilterStore.getState();
    latestStreamedTextRef.current = '';
    isUserAbortingRef.current = false;

    try {
      const queryTask = chatService.querySubgraph(
        {
          query: activeQuestion,
          hops: filterHops ?? (parseMode === 'expert' ? 3 : 1),
          top_k: filterTopK ?? (parseMode === 'expert' ? 8 : 4),
          mode: parseMode,
          thread_id: threadId,
          chat_history: recentHistory,
          active_docs: activeDocNames,
          document_filter: storeDocFilter || (activeDocNames.length === 1 ? activeDocNames[0] : undefined),
          parser: 'docling',
          full_potential: parseMode === 'expert',
        },
        controller.signal,
        (_chunk, fullAccumulated) => {
          const cleanText = sanitizeStreamText(fullAccumulated);
          latestStreamedTextRef.current = cleanText;
          setConversation((prev) => {
            const updated = [...prev];
            if (updated[assistantIndex] && updated[assistantIndex].role === 'assistant') {
              updated[assistantIndex] = {
                ...updated[assistantIndex],
                text: cleanText,
              };
            }
            return updated;
          });
        }
      );

      const res = appMode === 'connected'
        ? await ensureMinimumDuration(queryTask, 1000, controller.signal)
        : await queryTask;

      if (isUnmountedRef.current) return;
      const elapsedSec = parseFloat(((performance.now() - executionStartTime) / 1000).toFixed(1));

      let newAnswerText = '';
      let newResponseData: Partial<SubgraphQueryResponse> | undefined;
      let errorDetails: BackendErrorDetails | undefined;
      let isStopped = false;
      const persisted = res.data ? isResponsePersisted(res.data) : false;

      if (res.data) {
        newAnswerText = sanitizeStreamText(res.data.grounded_answer);
        newResponseData = res.data;
      } else {
        const isManualAbort =
          isUserAbortingRef.current ||
          res.error?.code === 'CLIENT_REQUEST_CANCELLED' ||
          (typeof res.error?.message === 'string' && res.error.message.toLowerCase().includes('abort'));

        if (isManualAbort) {
          terminalLogger.info('Query execution stopped by user.', {
            session_id: threadId,
            elapsed_sec: elapsedSec,
          });
          newAnswerText = latestStreamedTextRef.current;
          isStopped = true;
        } else {
          errorDetails = createErrorDetails(res.error, null);
          const isOfflineError = Boolean(errorDetails.isOffline);
          if (!isOfflineError) {
            showErrorPopup(errorDetails.title, errorDetails.message, async () => {
              if (appMode !== 'connected') {
                await runCapabilityProbe();
              }
              handleRegenerateResponse(assistantIndex);
            });
          }
        }
      }

      const newRespVer: ResponseVersion = {
        id: `resp-${Date.now()}`,
        text: newAnswerText,
        response: newResponseData,
        error: errorDetails,
        durationSec: elapsedSec,
        timestamp: 'Just now',
        isStopped,
      };

      const updatedRespVersions = [...activeQVer.responseVersions, newRespVer];
      const newRespIdx = updatedRespVersions.length - 1;

      const updatedQVersions = [...qVersions];
      updatedQVersions[currQIdx] = {
        ...activeQVer,
        responseVersions: updatedRespVersions,
        currentResponseVersionIndex: newRespIdx,
      };

      setConversation((prev) => {
        const updated = [...prev];
        updated[userIndex] = {
          ...updated[userIndex],
          questionVersions: updatedQVersions,
          currentQuestionVersionIndex: currQIdx,
        };
        updated[assistantIndex] = {
          ...updated[assistantIndex],
          text: newAnswerText,
          response: newResponseData,
          error: errorDetails,
          durationSec: elapsedSec,
          persistenceFailed: !persisted,
          isStopped,
        };
        if (res.data && persisted) {
          updateSessionInMemory(updated, threadId);
        }
        return updated;
      });
    } catch (err: any) {
      if (isUnmountedRef.current) return;
      const elapsedSec = parseFloat(((performance.now() - executionStartTime) / 1000).toFixed(1));
      const isManualAbort =
        isUserAbortingRef.current ||
        err?.name === 'AbortError' ||
        err?.code === 'CLIENT_REQUEST_CANCELLED' ||
        (typeof err?.message === 'string' && err.message.toLowerCase().includes('abort'));

      if (isManualAbort) {
        terminalLogger.info('Query execution stopped by user.', {
          session_id: threadId,
          elapsed_sec: elapsedSec,
        });
        const stoppedText = latestStreamedTextRef.current;
        const newRespVer: ResponseVersion = {
          id: `resp-${Date.now()}`,
          text: stoppedText,
          isStopped: true,
          durationSec: elapsedSec,
          timestamp: 'Just now',
        };
        const updatedRespVersions = [...activeQVer.responseVersions, newRespVer];
        const newRespIdx = updatedRespVersions.length - 1;

        const updatedQVersions = [...qVersions];
        updatedQVersions[currQIdx] = {
          ...activeQVer,
          responseVersions: updatedRespVersions,
          currentResponseVersionIndex: newRespIdx,
        };

        setConversation((prev) => {
          const updated = [...prev];
          updated[userIndex] = {
            ...updated[userIndex],
            questionVersions: updatedQVersions,
            currentQuestionVersionIndex: currQIdx,
          };
          updated[assistantIndex] = {
            ...updated[assistantIndex],
            text: stoppedText,
            response: undefined,
            error: undefined,
            durationSec: elapsedSec,
            isStopped: true,
          };
          return updated;
        });
      } else {
        const errorDetails = createErrorDetails(null, err);
        if (!errorDetails.isOffline) {
          showErrorPopup(errorDetails.title, errorDetails.message, async () => {
            if (appMode !== 'connected') {
              await runCapabilityProbe();
            }
            handleRegenerateResponse(assistantIndex);
          });
        }
        const newRespVer: ResponseVersion = {
          id: `resp-${Date.now()}`,
          text: '',
          error: errorDetails,
          durationSec: elapsedSec,
          timestamp: 'Just now',
        };
        const updatedRespVersions = [...activeQVer.responseVersions, newRespVer];
        const newRespIdx = updatedRespVersions.length - 1;

        const updatedQVersions = [...qVersions];
        updatedQVersions[currQIdx] = {
          ...activeQVer,
          responseVersions: updatedRespVersions,
          currentResponseVersionIndex: newRespIdx,
        };

        setConversation((prev) => {
          const updated = [...prev];
          updated[userIndex] = {
            ...updated[userIndex],
            questionVersions: updatedQVersions,
            currentQuestionVersionIndex: currQIdx,
          };
          updated[assistantIndex] = {
            ...updated[assistantIndex],
            text: '',
            response: undefined,
            error: errorDetails,
            durationSec: elapsedSec,
          };
          return updated;
        });
      }
    } finally {
      setIsLoading(false);
      setRegeneratingIndex(null);
      setActiveExecutingQuery('');
      abortControllerRef.current = null;
      isUserAbortingRef.current = false;
      latestStreamedTextRef.current = '';
    }
  };

  const handleSwitchResponseVersion = (assistantIndex: number, targetRespIdx: number) => {
    const userIndex = assistantIndex - 1;
    if (userIndex < 0 || !conversation[userIndex] || conversation[userIndex].role !== 'user') return;

    setConversation((prev) => {
      const updated = [...prev];
      const userMsg = updated[userIndex];
      const assistantMsg = updated[assistantIndex];
      const qVersions = getTurnQuestionVersions(userMsg, assistantMsg);
      const currQIdx = userMsg.currentQuestionVersionIndex ?? (qVersions.length - 1);
      const activeQVer = qVersions[currQIdx] || qVersions[0];

      if (targetRespIdx < 0 || targetRespIdx >= activeQVer.responseVersions.length) return prev;

      const targetResp = activeQVer.responseVersions[targetRespIdx];
      const updatedQVersions = [...qVersions];
      updatedQVersions[currQIdx] = {
        ...activeQVer,
        currentResponseVersionIndex: targetRespIdx,
      };

      updated[userIndex] = {
        ...userMsg,
        questionVersions: updatedQVersions,
        currentQuestionVersionIndex: currQIdx,
      };
      updated[assistantIndex] = {
        ...assistantMsg,
        text: targetResp.text,
        response: targetResp.response,
        error: targetResp.error,
        durationSec: targetResp.durationSec,
      };

      if (currentSessionId) {
        updateSessionInMemory(updated, currentSessionId);
      }
      return updated;
    });
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const tempDocId = `src-${Date.now()}`;
      const newDoc: SourceDocument = {
        id: tempDocId,
        name: file.name,
        size: formatBytes(file.size),
        bytes: file.size,
        pages: 1,
        color: file.name.endsWith('.pdf') ? 'rose' : 'indigo',
        selected: true,
        status: 'processing',
        uploadProgress: 15,
      };

      setSourceDocs((prev) => {
        const updated = [...prev, newDoc];
        if (currentSessionId) {
          const activeIds = updated.filter((d) => d.selected).map((d) => d.id);
          const activeNames = updated.filter((d) => d.selected).map((d) => d.name);
          setSessions((prevSessions) => {
            return prevSessions.map((s) =>
              s.id === currentSessionId ? { ...s, selectedSourceIds: activeIds, sources: updated, attached_docs: activeNames } : s
            );
          });
        }
        return updated;
      });

      // Smooth progress animation during upload / initial stages
      let currentProg = 15;
      const progressTimer = setInterval(() => {
        currentProg = Math.min(88, currentProg + Math.floor(Math.random() * 8) + 4);
        setSourceDocs((prev) =>
          prev.map((d) => (d.id === tempDocId && d.status === 'processing' ? { ...d, uploadProgress: currentProg } : d))
        );
      }, 400);

      try {
        const uploadRes = await sourceService.uploadPdfs([file], undefined, {
          parseMode,
          parser: 'docling',
          sessionId: currentSessionId || undefined,
        });
        clearInterval(progressTimer);

        if (uploadRes?.error || uploadRes?.status >= 400) {
          setSourceDocs((prev) =>
            prev.map((d) => (d.id === tempDocId ? { ...d, uploadProgress: 0, status: 'failed' } : d))
          );
          showErrorPopup('Upload failed', uploadRes?.error?.message || 'Document processing could not be completed. Please try again.');
        } else {
          const report = uploadRes?.data?.reports?.[0];
          const backendDocId = report?.doc_id || report?.document_id;
          const isImmediateReady = report?.status === 'ready' || !backendDocId;

          const markReady = () => {
            setSourceDocs((prev) =>
              prev.map((d) =>
                d.id === tempDocId || d.name === file.name
                  ? { ...d, uploadProgress: 100, status: 'ready', selected: true }
                  : d
              )
            );
            setApiReadyFilenames((prev) => new Set([...prev, file.name.toLowerCase()]));

            if (currentSessionId && currentSessionId !== 'new') {
              chatService.attachToSessionDrawer?.(currentSessionId, file.name).catch(() => {});
            }
          };

          if (isImmediateReady) {
            markReady();
          } else if (backendDocId) {
            // Stream real progress events from SSE
            sourceService.watchDocumentIngestionEvents(
              backendDocId,
              (progStatus) => {
                const pct = Math.max(15, Math.min(100, progStatus.percent));
                setSourceDocs((prev) =>
                  prev.map((d) =>
                    d.id === tempDocId || d.name === file.name
                      ? { ...d, uploadProgress: pct, status: progStatus.status === 'ready' || pct >= 100 ? 'ready' : 'processing' }
                      : d
                  )
                );
              },
              () => {
                markReady();
              },
              () => {
                // If SSE fails or completes, finalize based on backend manifest check
                markReady();
              }
            );
          } else {
            markReady();
          }
        }
      } catch (err: any) {
        clearInterval(progressTimer);
        console.error('Source upload error:', err);
        setSourceDocs((prev) =>
          prev.map((d) => (d.id === tempDocId ? { ...d, uploadProgress: 0, status: 'failed' } : d))
        );
        showErrorPopup('Upload failed', 'Document processing could not be completed. Please try again.');
      }
      e.target.value = '';
    }
  };

  return (
    <div className="bg-dot-pattern text-slate-900 dark:text-slate-100 h-screen h-dvh max-h-screen max-h-dvh antialiased flex flex-col font-sans select-none overflow-hidden relative">
      {/* TopNavigationBar — Modular Header */}
      <MainHeader
        activeSourcesCount={activeSourcesCount}
        onOpenSources={() => setIsSourcesDrawerOpen(true)}
        onOpenMobileMenu={() => setIsPipelineDrawerOpen(true)}
        isDrawerOpen={isPipelineDrawerOpen}
      />

      {/* Upper Side Notification: Unconfigured Pipeline Tunnel Notice */}
      <UnconfiguredNotice
        isTunnelConfigured={isTunnelConfigured}
        onOpenSettings={() => {
          settingsJunction.open('gateway');
        }}
      />

      {/* Upper Side Notification: Gateway Disconnected / Offline Notice with Retry */}
      {isTunnelConfigured && appMode === 'offline' && (
        <div className="fixed top-14 sm:top-16 left-0 sm:left-16 right-0 z-30 flex justify-center px-[clamp(0.5rem,2vw,1rem)] pt-1 pointer-events-none animate-in fade-in slide-in-from-top-1 duration-200">
          <div
            data-testid="gateway-disconnected-notice"
            className="pointer-events-auto inline-flex items-center gap-1.5 sm:gap-2 py-1 px-3 rounded-full bg-rose-500/15 dark:bg-rose-950/75 border border-rose-500/30 text-rose-950 dark:text-rose-200 shadow-sm backdrop-blur-md text-[clamp(10px,2.4vw,12px)] max-w-[calc(100vw-1.5rem)] sm:max-w-none text-center sm:text-left"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500 shrink-0 animate-pulse" />
            <span className="leading-tight truncate sm:whitespace-normal">
              Gateway not connected properly.
            </span>
            <button
              type="button"
              aria-label="Retry Connection"
              onClick={() => runCapabilityProbe()}
              className="font-semibold underline hover:text-rose-950 dark:hover:text-white cursor-pointer ml-1 inline-flex items-center gap-1 shrink-0"
            >
              <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                <polyline points="1 4 1 10 7 10" />
                <polyline points="23 20 23 14 17 14" />
                <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15" />
              </svg>
              Retry
            </button>
            <span className="text-rose-300 dark:text-rose-600">·</span>
            <button
              type="button"
              aria-label="Open Settings"
              onClick={() => settingsJunction.open('gateway')}
              className="font-medium underline hover:text-rose-950 dark:hover:text-white cursor-pointer shrink-0"
            >
              Settings
            </button>
          </div>
        </div>
      )}

      {/* Slideover / Docked Pipeline Drawer — Modular Sidebar */}
      <MainSidebar
        isDrawerOpen={isPipelineDrawerOpen}
        onToggleDrawer={() => setIsPipelineDrawerOpen((prev) => !prev)}
        onNewChat={handleNewChat}
        onOpenSearch={() => {
          setIsPipelineDrawerOpen(false);
          setIsSearchModalOpen(true);
        }}
        onOpenSettings={() => {
          setIsUserMenuOpen(false);
          setIsPipelineDrawerOpen(false);
          settingsJunction.open();
        }}
        onOpenUsage={() => {
          setIsUserMenuOpen(false);
          setIsPipelineDrawerOpen(false);
          setIsSearchModalOpen(true);
        }}
        onLogout={handleLogout}
        sessions={sortedSessions}
        currentSessionId={currentSessionId}
        pinnedSessionIds={pinnedSessionIds}
        activeSessionMenuId={activeSessionMenuId}
        renamingSessionId={renamingSessionId}
        newSessionTitle={newSessionTitle}
        setNewSessionTitle={setNewSessionTitle}
        onSelectSession={handleSelectSession}
        onTogglePinSession={handleTogglePinSession}
        setActiveSessionMenuId={setActiveSessionMenuId}
        setRenamingSessionId={setRenamingSessionId}
        handleSaveRename={handleSaveRename}
        handleDeleteSession={handleDeleteSession}
        gatewayUsername={gatewayUsername}
        isOnline={isOnline}
        isTunnelConfigured={isTunnelConfigured}
        isUserMenuOpen={isUserMenuOpen}
        setIsUserMenuOpen={setIsUserMenuOpen}
      />

      {/* Drawer Backdrops */}
      {isPipelineDrawerOpen && (
        <div
          id="drawerBackdrop"
          onClick={() => setIsPipelineDrawerOpen(false)}
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity"
        />
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          SOURCES / DATA DRAWER POPUP MODAL
          ══════════════════════════════════════════════════════════════════════ */}
      <SourcesDrawer
        isOpen={isSourcesDrawerOpen}
        onClose={() => setIsSourcesDrawerOpen(false)}
        sourceDocs={sourceDocs}
        activeSourcesCount={activeSourcesCount}
        sourceFilter={sourceFilter}
        setSourceFilter={setSourceFilter}
        addSourceMenuOpen={addSourceMenuOpen}
        setAddSourceMenuOpen={setAddSourceMenuOpen}
        onBrowseFileClick={() => fileInputRef.current?.click()}
        onOpenLibraryPicker={() => setIsLibraryPickerOpen(true)}
        isDocReady={isDocReady}
        onToggleSourceDoc={toggleSourceDoc}
        onDeleteSourceDoc={handleDeleteSourceDoc}
        onViewPdf={handleOpenPdfViewer}
      />

      {/* MainContent Area offset for collapsed rail - positioned below header so content never goes under header */}
      <div
        ref={contentContainerRef}
        className={`flex-1 flex flex-col pl-0 sm:pl-16 w-full min-w-0 relative z-10 overflow-y-auto overflow-x-hidden ${
          hasTopNotice ? 'mt-24 sm:mt-24' : 'mt-14 sm:mt-16'
        }`}
      >
        <main
          className={`w-full max-w-2xl mx-auto px-[clamp(0.75rem,3vw,1.25rem)] ${
            conversation.length === 0
              ? 'py-6 justify-center min-h-full flex-1 flex flex-col'
              : 'pt-2 pb-8 flex flex-col'
          } transition-all duration-300`}
        >
        {/* Hero Title & Welcome - Only visible before a question is asked / when conversation is empty */}
        {conversation.length === 0 && (
          <section className="mb-4 sm:mb-6 text-center sm:text-left pt-2 sm:pt-0 select-none" data-purpose="hero-header">
            <h1 className="text-[clamp(1.5rem,4.5vw,2.25rem)] font-semibold tracking-tight text-slate-900 dark:text-white mb-1.5">
              Welcome to Raise
            </h1>
            <p className="text-[clamp(0.8125rem,2.2vw,0.9375rem)] text-slate-500 dark:text-slate-400 font-normal leading-relaxed">
              {activeDocNames.length === 0
                ? 'Ask research questions, synthesize knowledge, or attach documents for deep analysis.'
                : 'Explore insights from your attached sources or ask a follow-up inquiry.'}
            </p>
          </section>
        )}

        {/* Dynamic Graph-Grounded Suggestion Cards: ONLY rendered when documents are uploaded in the Drawer */}
        {conversation.length === 0 && dynamicSuggestions.length > 0 && (
          <div className="mb-4 sm:mb-6 w-full space-y-2 animate-in fade-in slide-in-from-bottom-2 duration-200">
            <div className="flex items-center justify-between px-1">
              <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <svg className="w-3.5 h-3.5 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span>Recommended Research Inquiries</span>
              </span>
              <span className="text-[10px] text-indigo-600 dark:text-[#a8c7fa] font-medium">
                {dynamicSuggestions.length} questions from attached sources
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {dynamicSuggestions.slice(0, 4).map((item, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    setQuery(item.query);
                    textareaRef.current?.focus();
                  }}
                  className={`p-3 text-left rounded-xl border border-slate-200/80 dark:border-white/10 bg-white/80 dark:bg-white/[0.03] hover:bg-indigo-50/70 dark:hover:bg-white/[0.07] hover:border-indigo-300 dark:hover:border-indigo-500/40 transition-all cursor-pointer group shadow-2xs flex-col justify-between gap-2 ${
                    idx >= 2 ? 'hidden sm:flex' : 'flex'
                  }`}
                >
                  <p className="text-xs text-slate-800 dark:text-slate-200 font-medium leading-relaxed group-hover:text-indigo-600 dark:group-hover:text-indigo-300 transition-colors line-clamp-2">
                    {item.query}
                  </p>
                  <div className="flex items-center gap-2 text-[10px] text-slate-400 dark:text-slate-500">
                    {item.category && (
                      <span className="px-1.5 py-0.5 rounded-md bg-slate-100 dark:bg-white/10 text-slate-600 dark:text-slate-300 font-medium truncate max-w-[150px]">
                        {item.category}
                      </span>
                    )}
                    {item.grounding_confidence && (
                      <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                        {item.grounding_confidence} verified
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}



        {/* Conversation Stream */}
        {conversation.length > 0 && (
          <div className="space-y-6 mb-6">
            {conversation.map((msg, i) => {
              if (msg.role === 'user') {
                const nextAssistant = conversation[i + 1]?.role === 'assistant' ? conversation[i + 1] : undefined;
                const qVersions = getTurnQuestionVersions(msg, nextAssistant);
                const currentQIdx = msg.currentQuestionVersionIndex ?? (qVersions.length - 1);
                const currentQVerNum = currentQIdx + 1;
                const totalQVers = qVersions.length;

                return (
                  <div key={`user-turn-${i}`} className="flex flex-col items-end group/query">
                    {editingMessageIndex === i ? (
                      /* Inline Question Editor */
                      <div className="w-full max-w-[85%] bg-white dark:bg-[#131622] border border-indigo-400 dark:border-indigo-500/50 rounded-2xl rounded-tr-sm p-3.5 shadow-md dark:shadow-xl transition-all">
                        <textarea
                          value={editingQuestionText}
                          onChange={(e) => setEditingQuestionText(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                              e.preventDefault();
                              handleSaveEditedQuestion(i, editingQuestionText);
                            } else if (e.key === 'Escape') {
                              setEditingMessageIndex(null);
                            }
                          }}
                          autoFocus
                          rows={3}
                          className="w-full bg-transparent text-sm sm:text-base text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none resize-none font-normal leading-relaxed"
                          placeholder="Edit your question..."
                        />
                        <div className="flex items-center justify-end mt-2 pt-2 border-t border-slate-200/70 dark:border-white/[0.08]">
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => setEditingMessageIndex(null)}
                              className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 transition-colors cursor-pointer"
                            >
                              Cancel
                            </button>
                            <button
                              type="button"
                              disabled={!editingQuestionText.trim() || isLoading}
                              onClick={() => handleSaveEditedQuestion(i, editingQuestionText)}
                              className="px-3.5 py-1.5 text-xs font-medium bg-indigo-600 hover:bg-indigo-500 active:scale-95 disabled:opacity-50 disabled:pointer-events-none text-white rounded-lg transition-all cursor-pointer flex items-center gap-1.5 shadow-sm"
                            >
                              <span>Ask again</span>
                              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                              </svg>
                            </button>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <>
                        {/* User Inquiry Bubble */}
                        <div className="user-query-bubble max-w-[85%] bg-indigo-50/90 dark:bg-indigo-500/15 border border-indigo-200/80 dark:border-indigo-500/25 rounded-2xl rounded-tr-sm px-[clamp(0.75rem,2.5vw,1rem)] py-[clamp(0.5rem,2vw,0.75rem)] shadow-xs dark:shadow-md">
                          <p className="text-sm sm:text-base leading-relaxed text-slate-900 dark:text-slate-100 font-normal select-text break-words">
                            {msg.text}
                          </p>
                        </div>

                        {/* Question Action Bar directly below user inquiry */}
                        <div className="flex items-center gap-1 mt-1.5 mr-1 text-slate-500 dark:text-slate-400">
                          {/* Copy Question Button */}
                          <ActionTooltip label={copiedKey === `q-${i}` ? 'Copied!' : 'Copy question'}>
                            <button
                              type="button"
                              onClick={() => handleCopyText(msg.text, `q-${i}`)}
                              title={copiedKey === `q-${i}` ? 'Copied!' : 'Copy question'}
                              aria-label="Copy question"
                              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-white/5 active:scale-95 transition-all cursor-pointer flex items-center justify-center"
                            >
                              {copiedKey === `q-${i}` ? (
                                <svg className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                  <polyline points="20 6 9 17 4 12" />
                                </svg>
                              ) : (
                                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                                </svg>
                              )}
                            </button>
                          </ActionTooltip>

                          {/* Edit Question Pencil Button */}
                          <ActionTooltip label="Edit question">
                            <button
                              type="button"
                              onClick={() => {
                                setEditingMessageIndex(i);
                                setEditingQuestionText(msg.text);
                              }}
                              title="Edit question"
                              aria-label="Edit question"
                              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-white/5 active:scale-95 transition-all cursor-pointer flex items-center justify-center"
                            >
                              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                              </svg>
                            </button>
                          </ActionTooltip>

                          {/* Question Versions Control (‹ X/Y ›) - Only show if user has edited question (totalQVers > 1) */}
                          {totalQVers > 1 && (
                            expandedQVersionsIndex === i ? (
                              <div
                                data-version-nav="true"
                                onClick={(e) => e.stopPropagation()}
                                className="flex items-center gap-0.5 bg-slate-100/90 dark:bg-[#1a1e2d] border border-indigo-300/80 dark:border-indigo-500/40 rounded-lg px-1 py-0.5 ml-0.5 animate-in fade-in zoom-in-95 duration-150"
                              >
                                <ActionTooltip label="Previous version">
                                  <button
                                    type="button"
                                    disabled={currentQVerNum <= 1}
                                    onClick={() => handleSwitchQuestionVersion(i, currentQIdx - 1)}
                                    title="Previous version"
                                    aria-label="Previous version"
                                    className="p-1 rounded text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/80 dark:hover:bg-white/10 disabled:opacity-30 disabled:pointer-events-none transition-all cursor-pointer flex items-center justify-center"
                                  >
                                    <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                      <polyline points="15 18 9 12 15 6" />
                                    </svg>
                                  </button>
                                </ActionTooltip>

                                <ActionTooltip label="Hide version navigation">
                                  <button
                                    type="button"
                                    onClick={() => setExpandedQVersionsIndex(null)}
                                    title="Hide version navigation"
                                    aria-label="Hide version navigation"
                                    className="flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-slate-200/70 dark:hover:bg-white/10 transition-colors cursor-pointer select-none"
                                  >
                                    <svg className="w-3 h-3 text-indigo-600 dark:text-indigo-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                      <circle cx="12" cy="12" r="10" />
                                      <polyline points="12 6 12 12 16 14" />
                                    </svg>
                                    <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                                      {currentQVerNum}/{totalQVers}
                                    </span>
                                  </button>
                                </ActionTooltip>

                                <ActionTooltip label="Next version">
                                  <button
                                    type="button"
                                    disabled={currentQVerNum >= totalQVers}
                                    onClick={() => handleSwitchQuestionVersion(i, currentQIdx + 1)}
                                    title="Next version"
                                    aria-label="Next version"
                                    className="p-1 rounded text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/80 dark:hover:bg-white/10 disabled:opacity-30 disabled:pointer-events-none transition-all cursor-pointer flex items-center justify-center"
                                  >
                                    <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                      <polyline points="9 18 15 12 9 6" />
                                    </svg>
                                  </button>
                                </ActionTooltip>
                              </div>
                            ) : (
                              <ActionTooltip label={`See versions (${currentQVerNum} of ${totalQVers})`}>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setExpandedQVersionsIndex(i);
                                  }}
                                  title={`See versions (${currentQVerNum} of ${totalQVers})`}
                                  aria-label={`See versions (${currentQVerNum} of ${totalQVers})`}
                                  className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-white/5 active:scale-95 transition-all cursor-pointer flex items-center justify-center gap-1"
                                >
                                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <circle cx="12" cy="12" r="10" />
                                    <polyline points="12 6 12 12 16 14" />
                                  </svg>
                                  <span className="text-[10px] font-semibold text-slate-600 dark:text-slate-300">
                                    {currentQVerNum}/{totalQVers}
                                  </span>
                                </button>
                              </ActionTooltip>
                            )
                          )}
                        </div>
                      </>
                    )}
                  </div>
                );
              } else {
                /* AI Assistant Grounded Response Card */
                const prevUser = conversation[i - 1]?.role === 'user' ? conversation[i - 1] : undefined;
                const qVersions = prevUser ? getTurnQuestionVersions(prevUser, msg) : [];
                const currentQIdx = prevUser ? (prevUser.currentQuestionVersionIndex ?? (qVersions.length - 1)) : 0;
                const activeQVer = qVersions[currentQIdx];
                const respVersions = activeQVer?.responseVersions && activeQVer.responseVersions.length > 0
                  ? activeQVer.responseVersions
                  : [{ id: `resp-${i}`, text: msg.text, response: msg.response, error: msg.error, durationSec: msg.durationSec }];
                const currentRespIdx = activeQVer?.currentResponseVersionIndex ?? (respVersions.length - 1);
                const activeResp = respVersions[currentRespIdx] || respVersions[0];
                const currentRespVerNum = currentRespIdx + 1;
                const totalRespVers = respVersions.length;

                const isSpeaking = speakingMessageId === `msg-${i}`;
                const isRegenerating = regeneratingIndex === i;
                const isCurrentlyActive = Boolean(
                  isLoading && (isRegenerating || (i === conversation.length - 1 && !msg.response && !msg.error && !msg.isStopped))
                );

                const isStopped = Boolean(
                  activeResp?.isStopped ??
                  msg.isStopped ??
                  (msg.error?.isAborted)
                );

                if (msg.error && !isCurrentlyActive && !isStopped) {
                  return (
                    <div key={`assistant-turn-${i}`} className="w-full mb-4">
                      <BackendErrorCard
                        error={msg.error}
                        targetUrl={apiBaseUrl}
                        onRetry={async () => {
                          if (msg.error?.isOffline || appMode !== 'connected') {
                            await runCapabilityProbe();
                          }
                          handleRegenerateResponse(i);
                        }}
                        onOpenSettings={() => {
                          setSettingsActiveTab('gateway');
                          setMobileSettingsView('detail');
                          setIsSettingsOpen(true);
                        }}
                      />
                    </div>
                  );
                }

                const executionTimeSec =
                  activeResp?.durationSec ??
                  msg.durationSec ??
                  (typeof msg.response?.latency_sec === 'number'
                    ? parseFloat(msg.response.latency_sec.toFixed(1))
                    : 2.1);

                return (
                  <div key={`assistant-turn-${i}`} className="flex flex-col items-start group/response w-full mb-5">
                    {/* Unified Single-Line Thinking & Searching Tracker while active; Thought Duration when complete */}
                    {isCurrentlyActive ? (
                      appMode === 'connected' ? (
                        <div className="w-full mb-2">
                          <QueryLifecycleTracker
                            query={activeExecutingQuery}
                            onAbort={handleAbortActiveQuery}
                          />
                        </div>
                      ) : (
                        <div data-testid="gateway-connecting-fallback" className="inline-flex items-center gap-2 py-1.5 px-3 mb-2 rounded-xl bg-amber-500/10 dark:bg-amber-500/15 border border-amber-500/30 text-amber-900 dark:text-amber-200 text-xs font-medium animate-in fade-in select-none">
                          <span className="w-2 h-2 rounded-full bg-amber-500 shrink-0 animate-ping" />
                          <span>Connecting to gateway...</span>
                        </div>
                      )
                    ) : (
                      !msg.error && !isStopped && appMode === 'connected' && (
                        <ThoughtDuration executionTimeSec={executionTimeSec} />
                      )
                    )}

                    {/* AI Response Card Box */}
                    {(!isCurrentlyActive || Boolean(msg.text)) && Boolean(msg.text) && (
                      <div className="ai-response-card w-full bg-white dark:bg-[#131622] border border-slate-200/90 dark:border-white/[0.08] rounded-2xl rounded-tl-sm p-[clamp(0.75rem,2.5vw,1.25rem)] shadow-sm dark:shadow-xl transition-all">
                        {/* Save-failure warning banner if generation succeeded but persistence failed */}
                        {msg.persistenceFailed && (
                          <div
                            data-testid="persistence-failure-warning"
                            className="mb-3.5 px-3.5 py-2.5 bg-amber-500/10 dark:bg-amber-500/15 border border-amber-500/30 rounded-xl flex items-center gap-2.5 text-xs text-amber-800 dark:text-amber-200"
                          >
                            <svg className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                            <span>
                              <strong>Save Warning:</strong> Message was generated but could not be saved to backend database. This turn is not saved and will disappear on page refresh.
                            </span>
                          </div>
                        )}

                        {/* Markdown Answer Body */}
                        {(() => {
                          const messageCitations: Citation[] =
                            (activeResp?.response?.citations && activeResp.response.citations.length > 0)
                              ? activeResp.response.citations
                              : (msg.response?.citations && msg.response.citations.length > 0)
                              ? msg.response.citations
                              : ((msg as any).citations && (msg as any).citations.length > 0)
                              ? (msg as any).citations
                              : [];

                          return (
                            <>
                              <div className="text-sm leading-relaxed text-slate-800 dark:text-slate-200 select-text">
                                <AnswerMarkdown
                                  content={msg.text}
                                  citations={messageCitations}
                                  showCitations={true}
                                />
                              </div>

                              {/* Verified Source Evidence Cards — Distinct container, never merging with answers */}
                              {messageCitations.length > 0 && (
                                <div
                                  className="mt-5 pt-4 border-t-2 border-slate-200/90 dark:border-white/10"
                                  role="region"
                                  aria-label="Verified Source Citations"
                                >
                                  {/* Evidence Header */}
                                  <div className="flex items-center justify-between gap-2 mb-3 px-0.5">
                                    <div className="flex items-center gap-2 min-w-0">
                                      <span className="w-2 h-2 rounded-full bg-indigo-600 dark:bg-indigo-400 shrink-0" />
                                      <span className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider flex items-center gap-1.5 truncate">
                                        <svg className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                                        </svg>
                                        Verified Sources &amp; Citations
                                      </span>
                                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-50 text-indigo-700 dark:bg-indigo-950/80 dark:text-indigo-300 border border-indigo-200/80 dark:border-indigo-800/80 font-mono shrink-0">
                                        {messageCitations.length} {messageCitations.length === 1 ? 'source' : 'sources'}
                                      </span>
                                    </div>
                                    <span className="text-[10px] text-slate-500 dark:text-slate-400 font-mono hidden sm:inline">
                                      Click card or page badge to inspect PDF
                                    </span>
                                  </div>

                                  {/* Evidence Cards Grid */}
                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5" role="list" aria-label="Citation Cards">
                                    {messageCitations.map((cit, citIdx) => (
                                      <button
                                        key={cit.citation_index || citIdx}
                                        type="button"
                                        tabIndex={0}
                                        role="button"
                                        data-testid="citation-card"
                                        aria-label={`Citation [${cit.citation_index}]: ${cit.pdf_filename}, page ${cit.primary_page}. ${cit.heading || ''}`}
                                        onClick={() => {
                                          setSelectedCitation(cit);
                                          openModal('pdf');
                                        }}
                                        onKeyDown={(e) => {
                                          if (e.key === 'Enter' || e.key === ' ') {
                                            e.preventDefault();
                                            setSelectedCitation(cit);
                                            openModal('pdf');
                                          }
                                        }}
                                        className="text-left p-3 rounded-2xl bg-slate-50/80 hover:bg-slate-100/90 dark:bg-white/[0.04] dark:hover:bg-white/[0.08] border border-slate-200/90 dark:border-white/10 hover:border-indigo-400/80 dark:hover:border-indigo-400/60 transition-all cursor-pointer group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:border-transparent shadow-2xs hover:shadow-xs"
                                      >
                                        <div className="flex items-center justify-between gap-1.5 mb-1.5">
                                          <div className="flex items-center gap-1.5 min-w-0">
                                            <span className="px-1.5 py-0.5 rounded text-[10.5px] font-mono font-bold bg-indigo-100 dark:bg-indigo-950/90 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 shrink-0 shadow-2xs">
                                              [{cit.citation_index || citIdx + 1}]
                                            </span>
                                            <span className="text-xs font-bold text-slate-800 dark:text-slate-200 truncate group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors flex items-center gap-1">
                                              <svg className="w-3 h-3 text-slate-400 group-hover:text-indigo-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                              </svg>
                                              <span className="truncate">{cit.pdf_filename}</span>
                                            </span>
                                          </div>
                                          <span
                                            className="px-2 py-0.5 rounded-md text-[10.5px] font-mono font-bold bg-indigo-50 dark:bg-indigo-950/80 text-indigo-600 dark:text-[#a8c7fa] border border-indigo-200/80 dark:border-indigo-800/80 shrink-0 flex items-center gap-1 group-hover:bg-indigo-100 dark:group-hover:bg-indigo-900 transition-colors"
                                            title={`Jump to page ${cit.primary_page} in ${cit.pdf_filename}`}
                                          >
                                            <span>Page {cit.primary_page}</span>
                                            <span className="text-[9px] opacity-70">↗</span>
                                          </span>
                                        </div>
                                        {cit.heading && (
                                          <p className="text-[11.5px] font-semibold text-slate-700 dark:text-slate-300 truncate mb-1 flex items-center gap-1">
                                            <span className="w-1 h-3 rounded-full bg-indigo-500/60 shrink-0" />
                                            <span className="truncate">{cit.heading}</span>
                                          </p>
                                        )}
                                        <div className="p-2 rounded-xl bg-white dark:bg-black/20 border border-slate-200/60 dark:border-white/5 my-1">
                                          <p className="text-[11px] text-slate-600 dark:text-slate-400 line-clamp-2 leading-relaxed italic font-serif">
                                            "{cit.plain_text}"
                                          </p>
                                        </div>
                                        <div className="flex items-center justify-between text-[10px] text-slate-400 dark:text-slate-500 mt-1 pt-1 border-t border-slate-100 dark:border-white/5">
                                          <span className="font-mono text-emerald-600 dark:text-emerald-400 font-medium">
                                            {Math.round((cit.similarity || 0.95) * 100)}% Match
                                          </span>
                                          <span className="text-indigo-600 dark:text-indigo-400 font-medium flex items-center gap-0.5 group-hover:underline">
                                            <span>Inspect PDF</span>
                                            <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                            </svg>
                                          </span>
                                        </div>
                                      </button>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </>
                          );
                        })()}
                    </div>
                  )}

                  {/* AI Response Action Toolbar OUTSIDE the box, placed identically to Question action bar */}
                  {Boolean(msg.text && !msg.error) && (
                    <div className="flex items-center gap-1 mt-1.5 ml-1 text-slate-500 dark:text-slate-400">
                      {/* 1. Copy Response Button */}
                      <ActionTooltip label={copiedKey === `resp-${i}` ? 'Copied!' : 'Copy response'}>
                        <button
                          type="button"
                          onClick={() => handleCopyText(msg.text, `resp-${i}`)}
                          title={copiedKey === `resp-${i}` ? 'Copied!' : 'Copy response'}
                          aria-label="Copy response"
                          className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-white/5 active:scale-95 transition-all cursor-pointer flex items-center justify-center"
                        >
                          {copiedKey === `resp-${i}` ? (
                            <svg className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                              <polyline points="20 6 9 17 4 12" />
                            </svg>
                          ) : (
                            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                            </svg>
                          )}
                        </button>
                      </ActionTooltip>

                      {/* 2. Export Response Dropdown */}
                      <ActionTooltip label="Export response">
                        <ExportResponseDropdown
                          query={prevUser?.text || msg.response?.query || 'Research Inquiry'}
                          answerText={msg.text}
                          response={msg.response}
                        />
                      </ActionTooltip>

                      {/* 3. Try Again / Regenerate Response Button */}
                      <ActionTooltip label="Regenerate response">
                        <button
                          type="button"
                          disabled={isLoading || isRegenerating}
                          onClick={() => handleRegenerateResponse(i)}
                          title="Regenerate response"
                          aria-label="Regenerate response"
                          className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-white/5 active:scale-95 disabled:opacity-40 disabled:pointer-events-none transition-all cursor-pointer flex items-center justify-center"
                        >
                          <svg
                            className={`w-3.5 h-3.5 ${isRegenerating ? 'animate-spin text-indigo-600 dark:text-indigo-400' : ''}`}
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <polyline points="1 4 1 10 7 10" />
                            <polyline points="23 20 23 14 17 14" />
                            <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15" />
                          </svg>
                        </button>
                      </ActionTooltip>

                      {/* 3. Speak Aloud / Read Aloud Button */}
                      <ActionTooltip label={isSpeaking ? 'Stop speaking' : 'Read aloud'}>
                        <button
                          type="button"
                          onClick={() => handleToggleSpeak(msg.text, `msg-${i}`)}
                          title={isSpeaking ? 'Stop speaking' : 'Read aloud'}
                          aria-label={isSpeaking ? 'Stop speaking' : 'Read aloud'}
                          className={`p-1.5 rounded-lg active:scale-95 transition-all cursor-pointer flex items-center justify-center ${
                            isSpeaking
                              ? 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-500/20 ring-1 ring-indigo-500/40'
                              : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-white/5'
                          }`}
                        >
                          {isSpeaking ? (
                            <svg className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" viewBox="0 0 24 24" fill="currentColor">
                              <rect x="6" y="6" width="12" height="12" rx="2" />
                            </svg>
                          ) : (
                            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                              <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                              <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
                            </svg>
                          )}
                        </button>
                      </ActionTooltip>

                      {/* 4. Response Versions Control - Only show if totalRespVers > 1, with previous/next toggled by clicking SVG */}
                      {totalRespVers > 1 && (
                        expandedRespVersionsIndex === i ? (
                          <div
                            data-version-nav="true"
                            onClick={(e) => e.stopPropagation()}
                            className="flex items-center gap-0.5 bg-slate-100/90 dark:bg-[#1a1e2d] border border-indigo-300/80 dark:border-indigo-500/40 rounded-lg px-1 py-0.5 ml-0.5 animate-in fade-in zoom-in-95 duration-150"
                          >
                            <ActionTooltip label="Previous response">
                              <button
                                type="button"
                                disabled={currentRespVerNum <= 1 || isRegenerating}
                                onClick={() => handleSwitchResponseVersion(i, currentRespIdx - 1)}
                                title="Previous response"
                                aria-label="Previous response"
                                className="p-1 rounded text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/80 dark:hover:bg-white/10 disabled:opacity-30 disabled:pointer-events-none transition-all cursor-pointer flex items-center justify-center"
                              >
                                <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                  <polyline points="15 18 9 12 15 6" />
                                </svg>
                              </button>
                            </ActionTooltip>

                            <ActionTooltip label="Hide response versions navigation">
                              <button
                                type="button"
                                onClick={() => setExpandedRespVersionsIndex(null)}
                                title="Hide response versions navigation"
                                aria-label="Hide response versions navigation"
                                className="flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-slate-200/70 dark:hover:bg-white/10 transition-colors cursor-pointer select-none"
                              >
                                <svg className="w-3 h-3 text-indigo-600 dark:text-indigo-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                  <polygon points="12 2 2 7 12 12 22 7 12 2" />
                                  <polyline points="2 17 12 22 22 17" />
                                  <polyline points="2 12 12 17 22 12" />
                                </svg>
                                <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                                  {currentRespVerNum}/{totalRespVers}
                                </span>
                              </button>
                            </ActionTooltip>

                            <ActionTooltip label="Next response">
                              <button
                                type="button"
                                disabled={currentRespVerNum >= totalRespVers || isRegenerating}
                                onClick={() => handleSwitchResponseVersion(i, currentRespIdx + 1)}
                                title="Next response"
                                aria-label="Next response"
                                className="p-1 rounded text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/80 dark:hover:bg-white/10 disabled:opacity-30 disabled:pointer-events-none transition-all cursor-pointer flex items-center justify-center"
                              >
                                <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                  <polyline points="9 18 15 12 9 6" />
                                </svg>
                              </button>
                            </ActionTooltip>
                          </div>
                        ) : (
                          <ActionTooltip label={`See response versions (${currentRespVerNum} of ${totalRespVers})`}>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setExpandedRespVersionsIndex(i);
                              }}
                              title={`See response versions (${currentRespVerNum} of ${totalRespVers})`}
                              aria-label={`See response versions (${currentRespVerNum} of ${totalRespVers})`}
                              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-white/5 active:scale-95 transition-all cursor-pointer flex items-center justify-center gap-1"
                            >
                              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <polygon points="12 2 2 7 12 12 22 7 12 2" />
                                <polyline points="2 17 12 22 22 17" />
                                <polyline points="2 12 12 17 22 12" />
                              </svg>
                              <span className="text-[10px] font-semibold text-slate-600 dark:text-slate-300">
                                {currentRespVerNum}/{totalRespVers}
                              </span>
                            </button>
                          </ActionTooltip>
                        )
                      )}

                    </div>
                  )}

                  {/* Clean response stopped banner with Retry action */}
                  {isStopped && !isCurrentlyActive && (
                    <ResponseStoppedBanner
                      onRetry={() => handleRegenerateResponse(i)}
                      className="mt-2 mb-1"
                    />
                  )}
                </div>
              );
            }
          })}
          {isLoading && regeneratingIndex === null && conversation[conversation.length - 1]?.role === 'user' && (
            <div className="w-full mb-3">
              {appMode === 'connected' ? (
                <QueryLifecycleTracker
                  query={activeExecutingQuery}
                  onAbort={handleAbortActiveQuery}
                />
              ) : (
                <div data-testid="gateway-connecting-fallback" className="inline-flex items-center gap-2 py-1.5 px-3 rounded-xl bg-amber-500/10 dark:bg-amber-500/15 border border-amber-500/30 text-amber-900 dark:text-amber-200 text-xs font-medium animate-in fade-in select-none">
                  <span className="w-2 h-2 rounded-full bg-amber-500 shrink-0 animate-ping" />
                  <span>Connecting to gateway...</span>
                </div>
              )}
            </div>
          )}
          </div>
        )}

        {/* Smart Jump-to-Bottom Button - Only visible when user moves/scrolls upward */}
        {showScrollToBottom && conversation.length > 0 && (
          <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 animate-in fade-in slide-in-from-bottom-2 duration-150 pointer-events-auto">
            <button
              type="button"
              onClick={scrollToBottom}
              aria-label="Scroll to latest response"
              title="Resume smooth scroll to bottom"
              className="bg-white/95 dark:bg-[#151928]/95 hover:bg-slate-50 dark:hover:bg-[#1c2236] text-slate-700 dark:text-slate-200 border border-slate-300/90 dark:border-white/15 px-3.5 py-1.5 rounded-full shadow-lg hover:shadow-xl backdrop-blur-md flex items-center gap-1.5 text-xs font-medium active:scale-95 transition-all cursor-pointer group"
            >
              <svg
                className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400 group-hover:translate-y-0.5 transition-transform"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
              </svg>
              <span>Scroll to bottom</span>
            </button>
          </div>
        )}

        {/* RAGQueryInterface - RAISE Input Container (In-flow below latest question/answer) */}
        <section
          className={`transition-all duration-300 w-full ${
            addSourceMenuOpen === 'input' ? '-translate-y-2.5 sm:translate-y-0' : 'translate-y-0'
          } ${
            conversation.length > 0
              ? 'relative mt-4 sm:mt-6 mb-8 z-20'
              : 'relative mb-1 sm:mb-0'
          }`}
          data-purpose="rag-prompt-container"
        >
          <div aria-hidden="true" className="query-aura-glow" />

          <div className="interactive-query-box">
            <div aria-hidden="true" className="beam-shimmer-sweep" />

            {/* Keyboard-navigable suggestions dropdown - compact small box without instructions or enter button */}
            {showSuggestions && filteredSuggestions.length > 0 && (
              <div
                id="query-suggestions-list"
                data-testid="query-suggestions-list"
                role="listbox"
                aria-label="Prompt Suggestions"
                className="mb-1.5 p-1 rounded-xl bg-white/95 dark:bg-[#181b26]/95 border border-slate-200 dark:border-white/10 shadow-lg backdrop-blur-md space-y-0.5 animate-in fade-in slide-in-from-bottom-2 duration-150 z-30"
              >
                {filteredSuggestions.map((item, sIdx) => {
                  const isHighlighted = activeSuggestionIndex === sIdx;
                  return (
                    <div
                      key={item.query}
                      id={`query-suggestion-${sIdx}`}
                      data-testid={`query-suggestion-item-${sIdx}`}
                      role="option"
                      aria-selected={isHighlighted}
                      tabIndex={-1}
                      onClick={() => {
                        setQuery(item.query);
                        setShowSuggestions(false);
                        setActiveSuggestionIndex(-1);
                        textareaRef.current?.focus();
                      }}
                      onMouseEnter={() => setActiveSuggestionIndex(sIdx)}
                      className={`w-full text-left px-2.5 py-1 sm:py-1.5 rounded-lg text-xs transition-all flex items-center justify-between gap-2 cursor-pointer ${
                        isHighlighted
                          ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 font-medium ring-1 ring-indigo-300 dark:ring-indigo-700/50 shadow-2xs'
                          : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5'
                      }`}
                    >
                      <span className="truncate block flex-1">{item.query}</span>
                      {item.category && (
                        <span className="text-[10px] text-slate-400 dark:text-slate-500 px-1.5 py-0.5 rounded bg-slate-100 dark:bg-white/5 shrink-0">
                          {item.category}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {/* Mobile Attached Sources: Floating chip strip cleanly placed ABOVE the WhatsApp question box */}
            {selectedDocs.length > 0 && (
              <div
                className="flex sm:hidden items-center gap-1.5 mb-1.5 px-2.5 py-1 bg-white/95 dark:bg-[#1e1f20]/95 border border-slate-200/90 dark:border-white/10 rounded-full shadow-xs overflow-x-auto scrollbar-none animate-in fade-in slide-in-from-bottom-1 select-none"
                data-purpose="mobile-attached-sources"
              >
                <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider pl-0.5 shrink-0">
                  Sources ({selectedDocs.length}):
                </span>
                {selectedDocs.map((file) => {
                  const ready = isDocReady(file);
                  const isProcessing = !ready;
                  const progress = file.uploadProgress ?? (isProcessing ? 45 : 100);

                  return (
                    <div
                      key={`mob-${file.id}`}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 dark:bg-white/10 border border-slate-200 dark:border-white/10 shrink-0 text-[11px]"
                    >
                      <span className="truncate max-w-[100px] font-medium text-slate-700 dark:text-slate-200">
                        {file.name}
                      </span>
                      {isProcessing ? (
                        <div className="w-3 h-3">
                          <CircularUploadProgress progress={progress} size={12} strokeWidth={2} />
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            removeAttachedFile(file.id);
                          }}
                          aria-label={`Remove mobile ${file.name}`}
                          className="text-slate-400 hover:text-slate-700 dark:hover:text-white rounded-full p-0.5 cursor-pointer"
                        >
                          <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {/* WhatsApp-Style Input Bar on Mobile / Full RAG Card on Desktop */}
            <div
              className={`glass-input-container rounded-[26px] sm:rounded-2xl flex flex-row items-center sm:flex-col sm:items-stretch sm:justify-between relative z-10 transition-all border border-slate-300/90 dark:border-white/[0.08] focus-within:ring-2 focus-within:ring-indigo-500/30 dark:focus-within:ring-indigo-400/40 px-2 py-1 sm:p-3 gap-1 sm:gap-2 ${
                conversation.length === 0
                  ? 'min-h-[44px] sm:min-h-[120px]'
                  : 'min-h-[44px] sm:min-h-[58px] shadow-lg dark:shadow-2xl backdrop-blur-2xl'
              }`}
              style={{
                position: 'relative',
                borderRadius: 'calc(1.75rem - 1px)',
              }}
            >
              <div
                className={`order-2 sm:order-1 w-full flex-1 min-w-0 px-1 relative z-20 no-scrollbar ${
                  conversation.length === 0 ? 'py-0.5 sm:pt-1 sm:pb-3' : 'py-0.5 sm:pt-0 sm:pb-0.5'
                }`}
              >
                {/* Real-time Voice Listening Floating Badge */}
                {isListening && (
                  <div className="absolute -top-7 sm:-top-7.5 left-1 flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-slate-900/90 dark:bg-white/95 text-white dark:text-slate-900 text-[11px] font-medium shadow-md animate-in fade-in slide-in-from-bottom-1 duration-150 pointer-events-none max-w-[88%] truncate z-30">
                    <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping shrink-0" />
                    <span className="shrink-0 text-rose-300 dark:text-rose-600 font-semibold">Listening:</span>
                    <span className="truncate opacity-90">{query.trim() || 'Speak your question...'}</span>
                  </div>
                )}

                {conversation.length === 0 && !query && (
                  <div
                    onClick={() => textareaRef.current?.focus()}
                    className="absolute top-1 left-1 right-2 pointer-events-none select-none text-[13px] sm:text-base leading-snug sm:leading-relaxed font-normal overflow-hidden whitespace-nowrap text-ellipsis"
                    aria-hidden="true"
                  >
                    {isListening ? (
                      <span className="text-rose-500 dark:text-rose-400 font-medium animate-pulse flex items-center gap-1.5">
                        <span className="inline-block w-2 h-2 rounded-full bg-rose-500 animate-ping" />
                        Listening... Speak your research inquiry
                      </span>
                    ) : (
                      <>
                        <span className="animated-ask-placeholder">{placeholderText}</span>
                        <span className="hidden sm:inline-block w-[2px] h-[1.15em] bg-indigo-500/85 dark:bg-indigo-400/90 ml-0.5 animated-cursor-blink align-middle rounded-full" />
                      </>
                    )}
                  </div>
                )}
                <textarea
                  ref={textareaRef}
                  value={query}
                  role="combobox"
                  aria-label="Ask a research inquiry (Cmd/Ctrl + K to focus)"
                  aria-expanded={showSuggestions}
                  aria-autocomplete="list"
                  aria-controls="query-suggestions-list"
                  aria-activedescendant={
                    showSuggestions && activeSuggestionIndex >= 0
                      ? `query-suggestion-${activeSuggestionIndex}`
                      : undefined
                  }
                  onChange={(e) => {
                    setQuery(e.target.value);
                    if (!showSuggestions && e.target.value.trim()) {
                      setShowSuggestions(true);
                    }
                  }}
                  onFocus={() => {
                    if (conversation.length === 0 || query.length > 0) {
                      setShowSuggestions(true);
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'ArrowDown') {
                      if (filteredSuggestions.length > 0) {
                        e.preventDefault();
                        if (!showSuggestions) {
                          setShowSuggestions(true);
                          setActiveSuggestionIndex(0);
                        } else {
                          setActiveSuggestionIndex((prev) =>
                            prev < filteredSuggestions.length - 1 ? prev + 1 : 0
                          );
                        }
                      }
                    } else if (e.key === 'ArrowUp') {
                      if (filteredSuggestions.length > 0) {
                        e.preventDefault();
                        if (!showSuggestions) {
                          setShowSuggestions(true);
                          setActiveSuggestionIndex(filteredSuggestions.length - 1);
                        } else {
                          setActiveSuggestionIndex((prev) =>
                            prev > 0 ? prev - 1 : filteredSuggestions.length - 1
                          );
                        }
                      }
                    } else if (e.key === 'Enter' && !e.shiftKey) {
                      if (showSuggestions && activeSuggestionIndex >= 0 && activeSuggestionIndex < filteredSuggestions.length) {
                        e.preventDefault();
                        const selected = filteredSuggestions[activeSuggestionIndex];
                        setQuery(selected.query);
                        setShowSuggestions(false);
                        setActiveSuggestionIndex(-1);
                      } else {
                        e.preventDefault();
                        if (isLoading) {
                          handleAbortActiveQuery();
                        } else {
                          setShowSuggestions(false);
                          setActiveSuggestionIndex(-1);
                          handleExecuteQuery();
                        }
                      }
                    } else if (e.key === 'Escape') {
                      if (showSuggestions) {
                        e.preventDefault();
                        setShowSuggestions(false);
                        setActiveSuggestionIndex(-1);
                      }
                    }
                  }}
                  className={`w-full bg-transparent border-0 resize-none text-[13.5px] sm:text-[clamp(0.875rem,2vw,1rem)] text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:ring-0 py-0.5 px-0 leading-snug sm:leading-relaxed font-normal focus:outline-none transition-[height] duration-100 overflow-y-auto no-scrollbar scrollbar-none [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden ${
                    conversation.length === 0
                      ? 'min-h-[22px] sm:min-h-[52px]'
                      : 'min-h-[22px] sm:min-h-[24px]'
                  } max-h-[96px] sm:max-h-[140px]`}
                  style={{
                    scrollbarWidth: 'none',
                    msOverflowStyle: 'none',
                  }}
                  placeholder={
                    isListening
                      ? 'Listening... Speak your research inquiry'
                      : conversation.length === 0
                      ? ''
                      : 'Ask a follow-up inquiry...'
                  }
                  rows={1}
                />
              </div>

              <div
                className={`contents sm:flex sm:order-2 sm:w-full sm:items-center sm:justify-between sm:gap-2 relative z-20 ${
                  conversation.length === 0 ? 'sm:pt-1 sm:pt-1.5' : 'sm:pt-0.5 sm:pt-1'
                }`}
              >
                {/* Attachments Section: On mobile, only + button on the left (order-1). On desktop, + button and desktop chips on lower-left */}
                <div className="order-1 sm:order-none flex items-center gap-1.5 sm:gap-2 shrink-0 select-none">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.txt,.docx,.md,.csv"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                  <div className="relative shrink-0 select-none z-30" data-add-source-container="input">
                    <button
                      type="button"
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => setAddSourceMenuOpen((prev) => (prev === 'input' ? null : 'input'))}
                      title="Add context, sources, or switch mode (Browse PC, Library, Mode)"
                      aria-label="Add context or source"
                      aria-expanded={addSourceMenuOpen === 'input'}
                      className={`${conversation.length === 0 ? 'w-7.5 h-7.5 sm:w-8 sm:h-8' : 'w-7 h-7 sm:w-7 sm:h-7'} rounded-full sm:rounded-lg flex items-center justify-center transition-all active:scale-95 cursor-pointer shrink-0 select-none outline-none focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50 ${
                        addSourceMenuOpen === 'input'
                          ? 'bg-indigo-600 hover:bg-indigo-700 text-white border border-indigo-600 dark:bg-indigo-600 dark:hover:bg-indigo-700 dark:text-white dark:border-indigo-600 shadow-md ring-2 ring-indigo-500/30'
                          : 'bg-slate-100 hover:bg-slate-200 text-slate-700 hover:text-slate-900 border border-slate-200/90 dark:bg-white/10 dark:hover:bg-white/15 dark:text-slate-300 dark:hover:text-white dark:border-white/10 shadow-xs hover:border-indigo-400/50 dark:hover:border-indigo-400/50'
                      }`}
                    >
                      {/* Mobile (< sm): WhatsApp pin / paperclip icon */}
                      <svg
                        className={`sm:hidden w-4 h-4 transition-transform duration-200 ${
                          addSourceMenuOpen === 'input' ? 'rotate-45 text-white' : 'rotate-0'
                        }`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2.1"
                          d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
                        />
                      </svg>

                      {/* Desktop (>= sm): Plus (+) icon */}
                      <svg
                        className={`hidden sm:block w-3.5 h-3.5 transition-transform duration-200 ${
                          addSourceMenuOpen === 'input' ? 'rotate-45 text-white' : 'rotate-0'
                        }`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          d="M12 4v16m8-8H4"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2.2"
                        />
                      </svg>
                    </button>

                    {addSourceMenuOpen === 'input' && (
                      <>
                        {/* Mobile WhatsApp-style backdrop overlay */}
                        <div
                          className="fixed inset-0 bg-black/45 backdrop-blur-xs z-[65] sm:hidden animate-in fade-in duration-200"
                          onClick={() => setAddSourceMenuOpen(null)}
                          aria-hidden="true"
                        />

                        {/* WhatsApp-Style Action Sheet on Mobile, anchored below on Desktop */}
                        <div
                          className="fixed sm:absolute bottom-0 sm:bottom-auto sm:top-full left-0 right-0 sm:right-auto sm:left-0 sm:mt-2.5 sm:mb-0 w-full sm:w-72 bg-white dark:bg-[#1e1f20] border-t sm:border border-slate-200/90 dark:border-white/10 rounded-t-3xl sm:rounded-2xl shadow-2xl z-[70] p-4 sm:p-2 animate-in slide-in-from-bottom-8 sm:slide-in-from-top-2 fade-in duration-250 select-none max-h-[85vh] overflow-y-auto"
                          role="menu"
                        >
                          {/* Mobile pull / drag handle indicator */}
                          <div className="w-10 h-1 rounded-full bg-slate-300 dark:bg-white/20 mx-auto mb-3.5 sm:hidden" />

                          {/* Fast / Expert Mode Selector inside Pin Sheet on Mobile */}
                          <div className="mb-4 sm:hidden">
                            <div className="px-1 mb-2">
                              <span className="text-[11px] font-semibold tracking-wider text-slate-400 dark:text-slate-500 uppercase">
                                Research Engine Mode
                              </span>
                            </div>
                            <div className="grid grid-cols-2 gap-2 bg-slate-100 dark:bg-white/[0.06] p-1 rounded-2xl border border-slate-200/80 dark:border-white/10">
                              <button
                                type="button"
                                onClick={() => setParseMode('fast')}
                                className={`flex items-center justify-center gap-2 py-2 px-3 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                                  parseMode === 'fast'
                                    ? 'bg-white dark:bg-white/20 text-slate-900 dark:text-white shadow-xs ring-1 ring-black/5 dark:ring-white/10'
                                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                                }`}
                              >
                                <svg className="w-3.5 h-3.5 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.25" d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                                <span>Fast Mode</span>
                              </button>
                              <button
                                type="button"
                                onClick={() => setParseMode('expert')}
                                className={`flex items-center justify-center gap-2 py-2 px-3 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                                  parseMode === 'expert'
                                    ? 'bg-white dark:bg-white/20 text-indigo-600 dark:text-white shadow-xs ring-1 ring-black/5 dark:ring-white/10'
                                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                                }`}
                              >
                                <svg className="w-3.5 h-3.5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.25" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                                </svg>
                                <span>Expert Mode</span>
                              </button>
                            </div>
                          </div>

                          {/* Add Context & Sources Section */}
                          <div className="space-y-1 sm:space-y-0.5">
                            <div className="px-1 py-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 sm:hidden">
                              Add Context & Sources
                            </div>
                            <button
                              type="button"
                              onMouseDown={(e) => e.preventDefault()}
                              onClick={() => {
                                setAddSourceMenuOpen(null);
                                fileInputRef.current?.click();
                              }}
                              className="w-full text-left px-3.5 py-3 sm:px-3 sm:py-2 rounded-2xl sm:rounded-xl hover:bg-slate-100 dark:hover:bg-white/10 text-slate-800 dark:text-slate-200 text-xs font-medium flex items-center gap-3.5 sm:gap-2.5 transition-colors cursor-pointer group bg-slate-50/70 dark:bg-white/[0.03] sm:bg-transparent"
                            >
                              <div className="w-10 h-10 sm:w-7 sm:h-7 rounded-xl sm:rounded-lg bg-indigo-500 text-white sm:bg-slate-100 sm:text-slate-600 sm:dark:bg-white/10 sm:dark:text-slate-300 flex items-center justify-center shrink-0 shadow-xs group-hover:bg-indigo-600 sm:group-hover:bg-indigo-50 sm:group-hover:text-indigo-600 transition-colors">
                                <svg className="w-5 h-5 sm:w-4 sm:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                                </svg>
                              </div>
                              <div className="min-w-0">
                                <div className="font-semibold text-slate-900 dark:text-slate-100 text-[13px] sm:text-xs">Browse from PC</div>
                                <div className="text-[11px] sm:text-[10px] text-slate-500 dark:text-slate-400 truncate">Upload fresh PDF/DOCX to parse</div>
                              </div>
                            </button>

                            <button
                              type="button"
                              onMouseDown={(e) => e.preventDefault()}
                              onClick={() => {
                                setAddSourceMenuOpen(null);
                                setIsLibraryPickerOpen(true);
                              }}
                              className="w-full text-left px-3.5 py-3 sm:px-3 sm:py-2 rounded-2xl sm:rounded-xl hover:bg-slate-100 dark:hover:bg-white/10 text-slate-800 dark:text-slate-200 text-xs font-medium flex items-center gap-3.5 sm:gap-2.5 transition-colors cursor-pointer group bg-slate-50/70 dark:bg-white/[0.03] sm:bg-transparent mt-1 sm:mt-0.5"
                            >
                              <div className="w-10 h-10 sm:w-7 sm:h-7 rounded-xl sm:rounded-lg bg-emerald-500 text-white sm:bg-indigo-50 sm:text-indigo-600 sm:dark:bg-indigo-500/15 sm:dark:text-[#a8c7fa] flex items-center justify-center shrink-0 shadow-xs group-hover:bg-emerald-600 sm:group-hover:bg-indigo-100 transition-colors">
                                <svg className="w-5 h-5 sm:w-4 sm:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                                </svg>
                              </div>
                              <div className="min-w-0">
                                <div className="flex items-center gap-1.5 font-semibold text-emerald-600 dark:text-emerald-400 sm:text-indigo-600 sm:dark:text-[#a8c7fa] text-[13px] sm:text-xs">
                                  <span>Attach from Library</span>
                                  <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 font-mono">Instant</span>
                                </div>
                                <div className="text-[11px] sm:text-[10px] text-slate-500 dark:text-slate-400 truncate">Pre-indexed GraphRAG docs</div>
                              </div>
                            </button>
                          </div>
                        </div>
                      </>
                    )}
                  </div>

                  {/* Desktop horizontal scrolling chips container */}
                  <div className="hidden sm:flex items-center space-x-1.5 sm:space-x-2 overflow-x-auto scrollbar-none py-0.5 select-none shrink">
                    {selectedDocs.length === 0 && (
                      <span className="text-[11px] text-slate-400 dark:text-slate-500 font-normal sm:hidden select-none truncate">
                        Attach sources
                      </span>
                    )}

                    {selectedDocs.map((file) => {
                      const ready = isDocReady(file);
                      const isProcessing = !ready;
                      const progress = file.uploadProgress ?? (isProcessing ? 45 : 100);

                      return (
                        <div key={file.id} className="relative group cursor-pointer shrink-0 select-none">
                          <button
                            type="button"
                            onMouseDown={(e) => e.preventDefault()}
                            onClick={() => setIsSourcesDrawerOpen(true)}
                            aria-label={file.name}
                            className={`${conversation.length === 0 ? 'w-7.5 h-7.5 sm:w-9 sm:h-9' : 'w-6 h-6 sm:w-7 sm:h-7'} rounded-lg bg-slate-100 hover:bg-slate-200 border border-slate-300/80 dark:bg-white/[0.06] dark:hover:bg-white/10 dark:border-white/10 hover:border-indigo-400/40 flex items-center justify-center transition-all shadow-xs active:scale-95 cursor-pointer relative overflow-hidden select-none outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50 ${
                              isProcessing ? 'filter blur-[1.5px] opacity-70 cursor-wait' : 'filter-none opacity-100'
                            }`}
                            title={isProcessing ? `Uploading & parsing in GraphRAG... (${Math.round(progress)}%)` : `Source: ${file.name} (click to view in drawer)`}
                          >
                            <svg
                              className={`w-3 h-3 sm:w-3.5 sm:h-3.5 ${
                                file.color === 'rose'
                                    ? 'text-rose-600 dark:text-rose-400'
                                    : file.color === 'emerald'
                                    ? 'text-emerald-600 dark:text-emerald-400'
                                    : file.color === 'amber'
                                    ? 'text-amber-600 dark:text-amber-400'
                                    : 'text-indigo-600 dark:text-indigo-400'
                              }`}
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth="1.75"
                                d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                              />
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.75" d="M13 3v5a1 1 0 001 1h5" />
                            </svg>
                          </button>

                          {/* While uploading and parsing: circular moving animation, no x button */}
                          {isProcessing ? (
                            <div
                              className="absolute inset-0 flex items-center justify-center pointer-events-none z-10"
                              title={`Uploading & parsing in GraphRAG... (${Math.round(progress)}%)`}
                            >
                              <CircularUploadProgress
                                progress={progress}
                                size={conversation.length === 0 ? 26 : 22}
                                strokeWidth={2}
                              />
                            </div>
                          ) : (
                            /* Once parsed and full circle: unblurred and show x sign to deselect/remove */
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                removeAttachedFile(file.id);
                              }}
                              aria-label={`Remove ${file.name}`}
                              className="absolute -top-1.5 -right-1.5 w-3.5 h-3.5 sm:w-4 sm:h-4 rounded-full bg-white dark:bg-[#12141d] border border-slate-300 dark:border-white/20 text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-20 shadow-xs cursor-pointer"
                              title="Deselect source"
                            >
                              <svg className="w-2 h-2 sm:w-2.5 sm:h-2.5" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" viewBox="0 0 24 24">
                                <path d="M18 6L6 18M6 6l12 12" />
                              </svg>
                            </button>
                          )}

                          <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-50 pointer-events-none">
                            <div className="bg-slate-900 text-white dark:bg-[#12141d] dark:border dark:border-white/10 dark:text-slate-200 text-[11px] font-medium py-1 px-2 rounded-md shadow-xl whitespace-nowrap">
                              {isProcessing ? `Uploading: ${file.name} (${Math.round(progress)}%)` : file.name}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Right / Lower Side: Fast/Expert, Mic, and Enter actions kept in the same place, fully responsive */}
                <div className="order-3 sm:order-none flex items-center justify-end space-x-1 sm:space-x-2 shrink-0 ml-auto">
                  {/* Mode selector (fast, expert): on mobile it is inside the pin sheet, visible on desktop */}
                  <div className="hidden sm:flex items-center bg-slate-100 dark:bg-white/[0.06] p-0.5 rounded-lg border border-slate-200/80 dark:border-white/[0.08] text-[clamp(10px,2.2vw,11px)] font-medium select-none">
                    <button
                      type="button"
                      onClick={() => setParseMode('fast')}
                      className={`px-[clamp(0.375rem,1.5vw,0.5rem)] py-0.5 rounded-md transition-all cursor-pointer ${
                        parseMode === 'fast'
                          ? 'bg-white dark:bg-white/20 text-slate-900 dark:text-white font-semibold shadow-2xs'
                          : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
                      }`}
                    >
                      Fast
                    </button>
                    <button
                      type="button"
                      onClick={() => setParseMode('expert')}
                      className={`px-[clamp(0.375rem,1.5vw,0.5rem)] py-0.5 rounded-md transition-all cursor-pointer relative overflow-hidden ${
                        parseMode === 'expert'
                          ? 'bg-white dark:bg-white/20 text-slate-900 dark:text-white font-semibold shadow-2xs'
                          : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
                      }`}
                    >
                      {/* Expert mode gentle moving glow ray using light toner primary core color */}
                      {parseMode === 'expert' && isOnline && (
                        <span
                          aria-hidden="true"
                          className="pointer-events-none absolute inset-0 overflow-hidden rounded-md z-0"
                        >
                          <span
                            className="absolute inset-y-0 w-full -left-full animate-tunnel-ray pointer-events-none"
                            style={{
                              background:
                                'linear-gradient(90deg, transparent 0%, var(--box-light-primary, #6366f1) 50%, transparent 100%)',
                              filter: 'blur(1.5px)',
                              opacity: 0.35,
                            }}
                          />
                        </span>
                      )}
                      <span className="relative z-10">
                        Expert
                      </span>
                    </button>
                  </div>

                  <VoiceInputButton
                    isListening={isListening}
                    isVoiceSpeaking={isVoiceSpeaking}
                    voiceAudioLevels={voiceAudioLevels}
                    voiceDurationSec={voiceDurationSec}
                    hasSpeechContent={query.trim().length > 0}
                    onToggleVoice={handleToggleVoiceQuery}
                    onSubmitVoice={() => {
                      stopVoiceListening();
                      handleExecuteQuery();
                    }}
                    formatVoiceDuration={formatVoiceDuration}
                  />

                  {Boolean(query.trim() || isLoading) && (
                    <button
                      type="button"
                      onClick={isLoading ? handleAbortActiveQuery : handleExecuteQuery}
                      disabled={!isLoading && !query.trim()}
                      title={isLoading ? 'Stop generating' : 'Send question'}
                      aria-label={isLoading ? 'Stop generating query process' : 'Execute RAG Query'}
                      className={`${conversation.length === 0 ? 'w-7.5 h-7.5 sm:w-8 sm:h-8' : 'w-6.5 h-6.5 sm:w-8 sm:h-8'} rounded-full bg-slate-900 text-white hover:bg-slate-800 dark:bg-white dark:text-black dark:hover:bg-slate-200 active:scale-90 transition-all flex items-center justify-center shadow-md active-glow hover:shadow-indigo-500/50 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed animate-in fade-in zoom-in-75 duration-150`}
                    >
                      {isLoading ? (
                        /* Circular button with a rectangle inside it */
                        <div className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-xs bg-white dark:bg-black" />
                      ) : (
                        <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-white dark:text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path d="M5 10l7-7m0 0l7 7m-7-7v18" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" />
                        </svg>
                      )}
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Voice query error message banner if mic access fails */}
            {voiceError && (
              <div className="mt-2 px-3 py-1.5 text-xs text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/60 rounded-xl flex items-center justify-between gap-2 animate-in fade-in duration-150">
                <div className="flex items-center gap-1.5 min-w-0">
                  <svg className="w-4 h-4 text-rose-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  <span>{voiceError}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setVoiceError(null)}
                  className="p-1 text-rose-500 hover:text-rose-700 dark:hover:text-rose-200 rounded-md cursor-pointer"
                  aria-label="Dismiss error"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )}
          </div>
        </section>
        <div ref={messagesEndRef} className="h-px -mt-px pointer-events-none" />
      </main>
    </div>

      {/* ══════════════════════════════════════════════════════════════════════
          SETTINGS POPUP MODAL & GRID TUNER (MODULAR FEATURE VIA SETTINGS JUNCTION)
          ══════════════════════════════════════════════════════════════════════ */}
      <MainSettingsModal
        theme={theme}
        setTheme={setTheme}
        onSelectLibraryDocument={handleSelectLibraryDocument}
        onDeleteSourceDoc={handleDeleteSourceDoc}
        sessions={sessions}
        onSessionsChange={setSessions}
        onDeleteAllChats={handleDeleteAllChats}
        selectedVoiceName={selectedVoiceName}
        setSelectedVoiceName={setSelectedVoiceName}
        availableVoices={availableVoices}
        isPlayingSample={isVoiceSamplePlaying}
        onPlaySample={handleTestVoiceSample}
      />

      {/* Global PDF Document Modal */}
      {selectedCitation && (
        <Modal
          isOpen={activeModal === 'pdf'}
          onClose={() => closeModal()}
          title={`Document Evidence: ${selectedCitation.pdf_filename}`}
          subtitle={`Verified Page ${selectedCitation.primary_page} • ${selectedCitation.heading || 'Academic Report'}`}
          maxWidth="full"
        >
          <div className="h-[75vh]">
            <InlinePdfViewer citation={selectedCitation} />
          </div>
        </Modal>
      )}

      {/* Search Chats Modal (Modular feature) */}
      <MainSearchModal
        isOpen={isSearchModalOpen}
        onClose={() => {
          setIsSearchModalOpen(false);
          setActiveSessionMenuId(null);
        }}
        sessions={sortedSessions}
        currentSessionId={currentSessionId}
        pinnedSessionIds={pinnedSessionIds}
        sourceDocs={sourceDocs}
        activeSessionMenuId={activeSessionMenuId}
        setActiveSessionMenuId={setActiveSessionMenuId}
        renamingSessionId={renamingSessionId}
        setRenamingSessionId={setRenamingSessionId}
        newSessionTitle={newSessionTitle}
        setNewSessionTitle={setNewSessionTitle}
        handleSaveRename={handleSaveRename}
        handleTogglePinSession={handleTogglePinSession}
        handleDeleteSession={handleDeleteSession}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
      />

      {/* ─── KNOWLEDGE BASE LIBRARY PICKER MODAL (INSTANT GRAPHRAG PRE-INDEXED DOCS) ─── */}
      <LibraryPickerModal
        isOpen={isLibraryPickerOpen}
        onClose={() => setIsLibraryPickerOpen(false)}
        onSelectDocument={handleSelectLibraryDocument}
        attachedDocNames={sourceDocs.filter((d) => d.selected).map((d) => d.name)}
        onOpenUploadFromPC={() => fileInputRef.current?.click()}
        onViewPdf={handleOpenPdfViewer}
      />

      {/* ─── LITTLE ERROR POPUP TOAST (THEME AWARE & RESPONSIVE POSITIONING) ─── */}
      {errorPopup && (
        <div
          data-testid="little-error-popup"
          role="alert"
          className="fixed bottom-[clamp(4.5rem,10vh,5.5rem)] sm:bottom-5 right-3 sm:right-5 z-50 max-w-sm w-[calc(100vw-1.5rem)] sm:w-auto p-3 sm:p-3.5 rounded-2xl bg-white/95 dark:bg-[#181a20]/95 text-slate-900 dark:text-white border border-slate-200/90 dark:border-white/15 shadow-2xl backdrop-blur-md flex items-center gap-3 animate-in fade-in slide-in-from-bottom-2 duration-200 select-none"
        >
          <div className="w-8 h-8 rounded-xl bg-rose-50 text-rose-600 dark:bg-rose-500/20 dark:text-rose-400 flex items-center justify-center shrink-0 shadow-2xs">
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-slate-900 dark:text-white truncate">{errorPopup.title}</p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
              {errorPopup.message || 'Please try again.'}
            </p>
          </div>
          {errorPopup.onRetry && (
            <button
              type="button"
              onClick={() => {
                const retryFn = errorPopup.onRetry;
                setErrorPopup(null);
                retryFn?.();
              }}
              className="px-2.5 py-1 text-[11px] font-semibold bg-rose-600 hover:bg-rose-700 text-white rounded-lg transition-colors cursor-pointer shrink-0 shadow-xs"
            >
              Retry
            </button>
          )}
          <button
            type="button"
            onClick={() => setErrorPopup(null)}
            className="text-slate-400 hover:text-slate-700 dark:hover:text-white p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition-colors cursor-pointer shrink-0"
            aria-label="Close error popup"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

    </div>
  );
};

export default RaisePage;
