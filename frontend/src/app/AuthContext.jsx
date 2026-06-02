import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { API_BASE_URL, clearTokens, getTokens, setTokens } from '../lib/api';
import { useSubscriptionStore } from '../stores/subscriptionStore';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const setSubscription = useSubscriptionStore((s) => s.setSubscription);

  useEffect(() => {
    const { access } = getTokens();
    if (access) {
      Promise.all([
        fetch(`${API_BASE_URL}/users/me`, {
          headers: { Authorization: `Bearer ${access}` },
        }).then((r) => (r.ok ? r.json() : null)),
        fetch(`${API_BASE_URL}/subscriptions/me`, {
          headers: { Authorization: `Bearer ${access}` },
        }).then((r) => (r.ok ? r.json() : null)),
      ])
        .then(([userData, subData]) => {
          if (userData) setUser(userData);
          if (subData) setSubscription(subData);
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (email, password) => {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const detail = Array.isArray(body.detail)
        ? body.detail.map((e) => e.msg).join('; ')
        : body.detail;
      throw new Error(detail || 'Login failed');
    }
    const data = await response.json();
    setTokens(data.access_token, data.refresh_token);

    const [meResponse, subResponse] = await Promise.all([
      fetch(`${API_BASE_URL}/users/me`, {
        headers: { Authorization: `Bearer ${data.access_token}` },
      }),
      fetch(`${API_BASE_URL}/subscriptions/me`, {
        headers: { Authorization: `Bearer ${data.access_token}` },
      }),
    ]);
    const me = await meResponse.json();
    if (subResponse.ok) {
      const subData = await subResponse.json();
      setSubscription(subData);
    }
    setUser(me);
    return me;
  }, []);

  const register = useCallback(async (email, password, firstName, lastName) => {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, first_name: firstName, last_name: lastName }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const detail = Array.isArray(body.detail)
        ? body.detail.map((e) => e.msg).join('; ')
        : body.detail;
      throw new Error(detail || 'Registration failed');
    }
    return response.json();
  }, []);

  const logout = useCallback(async () => {
    const { refresh } = getTokens();
    try {
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      });
    } catch {}
    clearTokens();
    setUser(null);
    useSubscriptionStore.getState().setSubscription({ tier: 'free' });
  }, []);

  useEffect(() => {
    const handler = () => { setUser(null); clearTokens(); };
    window.addEventListener('auth:logout', handler);
    return () => window.removeEventListener('auth:logout', handler);
  }, []);

  const value = useMemo(
    () => ({ user, setUser, loading, login, register, logout, isAuthenticated: !!user }),
    [user, setUser, loading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
