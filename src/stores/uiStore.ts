import { create } from 'zustand';
import { Citation, GraphNode } from '../types';

export type ActiveModal = 'pdf' | 'diagnostics' | 'evidence' | 'upload' | 'settings' | null;
export type EvidenceTab = 'claims' | 'chunks' | 'subgraph' | 'quality';
export type ViewMode = 'user' | 'developer';

interface UiState {
  viewMode: ViewMode;
  sidebarCollapsed: boolean;
  activeModal: ActiveModal;
  selectedCitation: Citation | null;
  selectedNode: GraphNode | null;
  activeEvidenceTab: EvidenceTab;

  setViewMode: (mode: ViewMode) => void;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  openModal: (modal: ActiveModal) => void;
  closeModal: () => void;
  setSelectedCitation: (citation: Citation | null) => void;
  setSelectedNode: (node: GraphNode | null) => void;
  setActiveEvidenceTab: (tab: EvidenceTab) => void;
}

export const useUiStore = create<UiState>((set) => ({
  viewMode: (typeof localStorage !== 'undefined' ? (localStorage.getItem('raise_view_mode') as ViewMode) : null) || 'user',
  sidebarCollapsed: false,
  activeModal: null,
  selectedCitation: null,
  selectedNode: null,
  activeEvidenceTab: 'claims',

  setViewMode: (mode) => {
    try {
      localStorage.setItem('raise_view_mode', mode);
    } catch {
      // ignore
    }
    set({ viewMode: mode });
  },
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  openModal: (modal) => set({ activeModal: modal }),
  closeModal: () => set({ activeModal: null }),
  setSelectedCitation: (citation) => set({ selectedCitation: citation }),
  setSelectedNode: (node) => set({ selectedNode: node }),
  setActiveEvidenceTab: (tab) => set({ activeEvidenceTab: tab }),
}));
