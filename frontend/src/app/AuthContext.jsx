import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { API_BASE_URL } from '../lib/api';
import { useSubscriptionStore } from '../stores/subscriptionStore';

const AuthContext = createContext(null);

async function fetchMe() {
  const res = await fetch(`${API_BASE_URL}/users/me`, { credentials: 'include' });
  if (!res.ok) return null;
  return res.json();
}

function parseError(body, fallback) {
  const detail = body?.detail;
  if (Array.isArray(detail)) return detail.map((e) => e.msg).join('; ');
  return detail || fallback;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMe()
      .then((me) => { if (me) setUser(me); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      credentials: 'include',
      body: new URLSearchParams({ username: email, password }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(parseError(body, 'Login failed'));
    }
    const me = await fetchMe();
    if (!me) throw new Error('Login succeeded but session was not created. Please try again.');
    setUser(me);
    return me;
  }, []);

  const register = useCallback(async (email, password, firstName, lastName) => {
    const fullName = `${firstName || ''} ${lastName || ''}`.trim() || 'Learner';
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, full_name: fullName, password }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(parseError(body, 'Registration failed'));
    }
    return response.json();
  }, []);

  const logout = useCallback(async () => {
    try {
      await fetch(`${API_BASE_URL}/auth/logout`, { method: 'POST', credentials: 'include' });
    } catch {}
    setUser(null);
    useSubscriptionStore.getState().setSubscription({ tier: 'free' });
  }, []);

  const refresh = useCallback(async () => {
    const me = await fetchMe().catch(() => null);
    if (me) setUser(me);
    return me;
  }, []);

  function googleLogin() {
    window.location.href = `${API_BASE_URL}/auth/google/login`;
  }

  const value = useMemo(
    () => ({ user, setUser, loading, login, register, logout, refresh, googleLogin, isAuthenticated: !!user }),
    [user, setUser, loading, login, register, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
