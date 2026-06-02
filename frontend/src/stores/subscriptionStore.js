import { create } from 'zustand';

const TIER_DEFAULTS = {
  free: {
    correctionsPerSession: 3,
    heartbeatsPerRoom: 1,
    expert: false,
    tts: false,
    notes: false,
    series: false,
    leaderboard: false,
    aiRoom: false,
    maxParticipants: 3,
  },
  pro: {
    correctionsPerSession: Infinity,
    heartbeatsPerRoom: 3,
    expert: 'web-only',
    tts: false,
    notes: false,
    series: false,
    leaderboard: false,
    aiRoom: true,
    maxParticipants: 5,
  },
  pro_plus: {
    correctionsPerSession: Infinity,
    heartbeatsPerRoom: 5,
    expert: 'full',
    tts: true,
    notes: true,
    series: true,
    leaderboard: true,
    aiRoom: true,
    maxParticipants: 15,
  },
};

export const useSubscriptionStore = create((set, get) => ({
  tier: 'free',
  status: 'active',
  expiresAt: null,
  features: TIER_DEFAULTS.free,

  setTier: (tier) => {
    const features = TIER_DEFAULTS[tier] || TIER_DEFAULTS.free;
    set({ tier, features });
  },

  setSubscription: (data) => {
    const tier = data?.tier || 'free';
    const features = TIER_DEFAULTS[tier] || TIER_DEFAULTS.free;
    set({
      tier,
      status: data?.status || 'active',
      expiresAt: data?.expires_at || null,
      features,
    });
  },

  getAgentLevel: () => {
    const { tier } = get();
    if (tier === 'pro_plus') return 'full';
    if (tier === 'pro') return 'advanced';
    return 'basic';
  },
}));
