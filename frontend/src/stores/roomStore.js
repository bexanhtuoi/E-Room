import { create } from 'zustand';

export const useRoomStore = create((set, get) => ({
  rooms: [],
  currentRoom: null,
  filters: { search: '', tags: [], level: '', status: 'active' },
  isLoading: false,

  setRooms: (rooms) => set({ rooms }),
  setCurrentRoom: (room) => set({ currentRoom: room }),
  setFilters: (filters) => set({ filters: { ...get().filters, ...filters } }),
  setLoading: (isLoading) => set({ isLoading }),

  clearCurrentRoom: () => set({ currentRoom: null }),
}));
