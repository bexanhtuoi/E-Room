import { create } from 'zustand';

export const useTagStore = create((set, get) => ({
  userTags: [],
  popularTags: [],
  selectedTags: [],
  searchQuery: '',
  isLoading: false,

  setUserTags: (tags) => set({ userTags: tags }),
  setPopularTags: (tags) => set({ popularTags: tags }),
  setSelectedTags: (tags) => set({ selectedTags: tags }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setLoading: (isLoading) => set({ isLoading }),

  addTag: (tag) => {
    const current = get().selectedTags;
    if (!current.find((t) => t.id === tag.id || t === tag)) {
      set({ selectedTags: [...current, tag] });
    }
  },

  removeTag: (tagId) => {
    set({ selectedTags: get().selectedTags.filter((t) => (t.id || t) !== tagId) });
  },

  clearSelected: () => set({ selectedTags: [] }),
}));
