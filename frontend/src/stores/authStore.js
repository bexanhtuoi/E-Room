import { create } from 'zustand';

const STORAGE_KEY = 'e-room-auth';

function loadAuth() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : { user: null, accessToken: null, refreshToken: null };
  } catch {
    return { user: null, accessToken: null, refreshToken: null };
  }
}

function saveAuth(state) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      user: state.user,
      accessToken: state.accessToken,
      refreshToken: state.refreshToken,
    }));
  } catch { /* quota exceeded — degrade silently */ }
}

function clearAuth() {
  try { localStorage.removeItem(STORAGE_KEY); } catch {}
}

export const useAuthStore = create((set, get) => ({
  ...loadAuth(),

  isAuthenticated: () => !!get().accessToken,

  setTokens: (accessToken, refreshToken) => {
    set({ accessToken, refreshToken });
    saveAuth(get());
  },

  setUser: (user) => {
    set({ user });
    saveAuth(get());
  },

  login: (user, accessToken, refreshToken) => {
    set({ user, accessToken, refreshToken });
    saveAuth(get());
  },

  logout: () => {
    set({ user: null, accessToken: null, refreshToken: null });
    clearAuth();
  },
}));
