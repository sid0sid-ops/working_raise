import { create } from 'zustand';

interface FilterState {
  documentFilter: string | null;
  hops: number;
  topK: number;
  graphFilterType: string | null;
  searchQuery: string;

  setDocumentFilter: (doc: string | null) => void;
  setHops: (hops: number) => void;
  setTopK: (topK: number) => void;
  setGraphFilterType: (type: string | null) => void;
  setSearchQuery: (query: string) => void;
  resetFilters: () => void;
}

export const useFilterStore = create<FilterState>((set) => ({
  documentFilter: null,
  hops: 2,
  topK: 4,
  graphFilterType: null,
  searchQuery: '',

  setDocumentFilter: (documentFilter) => set({ documentFilter }),
  setHops: (hops) => set({ hops }),
  setTopK: (topK) => set({ topK }),
  setGraphFilterType: (graphFilterType) => set({ graphFilterType }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  resetFilters: () =>
    set({
      documentFilter: null,
      hops: 2,
      topK: 4,
      graphFilterType: null,
      searchQuery: '',
    }),
}));
