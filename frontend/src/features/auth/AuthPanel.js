import { useState } from 'react';
import { Card } from '../../components/ui/Card';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1';

export function AuthPanel() {
  const [email, setEmail] = useState('demo@eroom.local');
  const [password, setPassword] = useState('password123');
  const [displayName, setDisplayName] = useState('Demo User');
  const [status, setStatus] = useState('Idle');

  async function register() {
    setStatus('Registering...');
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, display_name: displayName }),
    });
    setStatus(response.ok ? 'Registered' : 'Register failed');
  }

  async function login() {
    setStatus('Logging in...');
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await response.json();
    if (response.ok) {
      localStorage.setItem('e-room-access-token', data.access_token);
      localStorage.setItem('e-room-refresh-token', data.refresh_token);
      setStatus('Logged in');
      return;
    }
    setStatus(data.detail || 'Login failed');
  }

  return (
    <Card title="Auth" subtitle="Register or login to get tokens">
      <div className="form-stack">
        <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="Display name" />
        <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email" />
        <input value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password" type="password" />
      </div>
      <div className="form-row" style={{ marginTop: 12 }}>
        <button onClick={register}>Register</button>
        <button onClick={login}>Login</button>
      </div>
      <p style={{ marginTop: 10, fontSize: 13, color: '#94a3b8' }}>{status}</p>
    </Card>
  );
}
