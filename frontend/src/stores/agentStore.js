import { create } from 'zustand';

export const useAgentStore = create((set) => ({
  level: 'basic',
  ragLoaded: false,
  misuseCount: 0,
  corrections: { used: 0, total: 3 },
  heartbeats: { used: 0, total: 1 },

  setLevel: (level) => set({ level }),
  setRagLoaded: (loaded) => set({ ragLoaded: loaded }),
  incrementMisuse: () => set((s) => ({ misuseCount: s.misuseCount + 1 })),
  resetMisuse: () => set({ misuseCount: 0 }),

  useCorrection: () => set((s) => ({
    corrections: { ...s.corrections, used: s.corrections.used + 1 },
  })),
  useHeartbeat: () => set((s) => ({
    heartbeats: { ...s.heartbeats, used: s.heartbeats.used + 1 },
  })),

  resetSession: (tier) => {
    const defaults = {
      free: { used: 0, total: 3 },
      pro: { used: 0, total: Infinity },
      pro_plus: { used: 0, total: Infinity },
    };
    const c = defaults[tier] || defaults.free;
    set({
      misuseCount: 0,
      corrections: { used: 0, total: c.total },
      heartbeats: { used: 0, total: tier === 'free' ? 1 : tier === 'pro' ? 3 : 5 },
    });
  },
}));
