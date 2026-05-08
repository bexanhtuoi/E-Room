import { useState } from 'react';
import { useAuth } from '../../app/AuthContext';

export function LoginPage() {
  const { login, register } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      if (isRegister) {
        await register(email, password, displayName);
        await login(email, password);
      } else {
        await login(email, password);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #020617 0%, #0c1a3a 50%, #020617 100%)',
      padding: 20,
    }}>
      <div style={{
        width: '100%',
        maxWidth: 400,
        padding: 36,
        borderRadius: 20,
        background: 'rgba(15, 23, 42, 0.85)',
        border: '1px solid rgba(148, 163, 184, 0.15)',
        backdropFilter: 'blur(20px)',
      }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginBottom: 8 }}>
            <span style={{ width: 8, height: 8, borderRadius: 99, background: '#34d399', boxShadow: '0 0 10px #34d399' }} />
            <span style={{ color: '#38bdf8', fontSize: 13, letterSpacing: '0.1em', fontWeight: 600 }}>E-Room</span>
          </div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: '#e2e8f0', margin: 0 }}>
            {isRegister ? 'Create account' : 'Welcome back'}
          </h1>
          <p style={{ color: '#94a3b8', fontSize: 14, marginTop: 4 }}>
            {isRegister ? 'Join English speaking rooms' : 'Sign in to start speaking'}
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 12 }}>
          {isRegister && (
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Display name"
              style={{ padding: '11px 14px', borderRadius: 10, border: '1px solid rgba(148,163,184,0.12)', background: 'rgba(15,23,42,0.7)', color: '#e2e8f0', outline: 'none', fontSize: 14 }}
            />
          )}
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            type="email"
            autoFocus
            style={{ padding: '11px 14px', borderRadius: 10, border: '1px solid rgba(148,163,184,0.12)', background: 'rgba(15,23,42,0.7)', color: '#e2e8f0', outline: 'none', fontSize: 14 }}
          />
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            type="password"
            style={{ padding: '11px 14px', borderRadius: 10, border: '1px solid rgba(148,163,184,0.12)', background: 'rgba(15,23,42,0.7)', color: '#e2e8f0', outline: 'none', fontSize: 14 }}
          />
          {error && (
            <div style={{ padding: '10px 14px', borderRadius: 10, background: 'rgba(248,113,113,0.08)', color: '#fca5a5', fontSize: 13, border: '1px solid rgba(248,113,113,0.15)' }}>
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={busy || !email || !password}
            style={{
              marginTop: 4,
              padding: '11px 18px',
              borderRadius: 10,
              border: 0,
              background: '#38bdf8',
              color: '#082f49',
              fontWeight: 600,
              fontSize: 14,
              cursor: 'pointer',
              opacity: busy || !email || !password ? 0.5 : 1,
            }}
          >
            {busy ? 'Please wait...' : isRegister ? 'Create account' : 'Sign in'}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: 18 }}>
          <button
            onClick={() => { setIsRegister(!isRegister); setError(''); }}
            style={{ background: 'none', border: 0, color: '#94a3b8', fontSize: 13, cursor: 'pointer' }}
          >
            {isRegister ? 'Already have an account? Sign in' : "Don't have an account? Register"}
          </button>
        </div>
      </div>
    </div>
  );
}
