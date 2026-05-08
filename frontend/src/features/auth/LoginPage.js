import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../app/AuthContext';

export function LoginPage() {
  const { login, register, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (isAuthenticated) navigate('/dashboard', { replace: true });
  }, [isAuthenticated, navigate]);

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
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-panel-left">
        <div className="login-brand">
          <div className="login-logo-icon">E</div>
          <h1 className="login-brand-name">E-Room</h1>
          <p className="login-tagline">Speak English, Connect Globally</p>
        </div>
        <ul className="login-features">
          <li>
            <span className="login-feature-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12" /></svg>
            </span>
            Practice with real people in structured rooms
          </li>
          <li>
            <span className="login-feature-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12" /></svg>
            </span>
            AI-powered feedback on your speaking
          </li>
          <li>
            <span className="login-feature-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12" /></svg>
            </span>
            Connect with learners worldwide
          </li>
        </ul>
        <div className="login-decoration" />
      </div>

      <div className="login-panel-right">
        <div className="login-form-wrapper">
          <h2 className="login-form-title">{isRegister ? 'Create account' : 'Welcome back'}</h2>
          <p className="login-form-subtitle">
            {isRegister ? 'Join English speaking rooms' : 'Sign in to start speaking'}
          </p>

          <form className="login-form" onSubmit={handleSubmit}>
            {isRegister && (
              <div className="login-field">
                <label className="login-label" htmlFor="displayName">Display name</label>
                <input
                  id="displayName"
                  className="login-input"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Your name"
                  required
                />
              </div>
            )}
            <div className="login-field">
              <label className="login-label" htmlFor="email">Email</label>
              <input
                id="email"
                className="login-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                type="email"
                autoFocus
                required
              />
            </div>
            <div className="login-field">
              <label className="login-label" htmlFor="password">Password</label>
              <input
                id="password"
                className="login-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                type="password"
                required
                minLength={8}
              />
            </div>

            {error && (
              <div className="login-error" role="alert">{error}</div>
            )}

            <button className="login-submit" type="submit" disabled={busy}>
              {busy ? 'Please wait...' : isRegister ? 'Create account' : 'Sign in'}
            </button>
          </form>

          <p className="login-toggle">
            {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
            <button
              className="login-toggle-btn"
              onClick={() => { setIsRegister(!isRegister); setError(''); }}
            >
              {isRegister ? 'Sign in' : 'Register'}
            </button>
          </p>
        </div>
      </div>

      <style>{`
        .login-page {
          display: flex; min-height: 100vh;
          background: var(--color-bg);
        }
        .login-panel-left {
          display: none; flex-direction: column; justify-content: center;
          width: 40%; padding: 60px;
          background: linear-gradient(135deg, var(--color-bg) 0%, var(--color-bg-elevated) 100%);
          position: relative; overflow: hidden;
        }
        .login-decoration {
          position: absolute; top: -40%; right: -20%;
          width: 600px; height: 600px; border-radius: 50%;
          background: radial-gradient(circle, var(--color-accent-muted) 0%, transparent 70%);
          opacity: 0.5; pointer-events: none;
        }
        .login-brand { position: relative; z-index: 1; }
        .login-logo-icon {
          display: inline-flex; align-items: center; justify-content: center;
          width: 48px; height: 48px; border-radius: var(--radius-md);
          background: var(--color-accent); color: #fff;
          font-size: 22px; font-weight: 700; margin-bottom: 16px;
        }
        .login-brand-name {
          font-family: var(--font-display); font-size: 32px; font-weight: 700;
          color: var(--color-text-primary); margin-bottom: 4px;
        }
        .login-tagline {
          font-size: 15px; color: var(--color-text-secondary);
          margin-bottom: 36px; line-height: 1.5;
        }
        .login-features {
          list-style: none; display: flex; flex-direction: column; gap: 14px;
          position: relative; z-index: 1;
        }
        .login-features li {
          display: flex; align-items: center; gap: 10px;
          font-size: 14px; color: var(--color-text-secondary);
        }
        .login-feature-icon {
          display: flex; align-items: center; justify-content: center;
          width: 24px; height: 24px; border-radius: var(--radius-full);
          background: var(--color-accent-muted); color: var(--color-accent);
          flex-shrink: 0;
        }
        .login-panel-right {
          flex: 1; display: flex; align-items: center; justify-content: center;
          padding: 40px 20px;
        }
        .login-form-wrapper {
          width: 100%; max-width: 400px;
          animation: fadeIn var(--transition-slow) ease both;
        }
        .login-form-title {
          font-family: var(--font-display); font-size: 24px; font-weight: 700;
          color: var(--color-text-primary); margin-bottom: 4px;
        }
        .login-form-subtitle {
          font-size: 14px; color: var(--color-text-secondary); margin-bottom: 28px;
        }
        .login-form { display: flex; flex-direction: column; gap: 16px; }
        .login-field { display: flex; flex-direction: column; gap: 5px; }
        .login-label {
          font-size: 13px; font-weight: 500; color: var(--color-text-secondary);
        }
        .login-input {
          padding: 10px 14px; border-radius: var(--radius-md);
          border: 1px solid var(--color-border);
          background: var(--color-bg-surface); color: var(--color-text-primary);
          font-size: 14px; outline: none; transition: border var(--transition-fast);
        }
        .login-input:focus { border-color: var(--color-accent); box-shadow: 0 0 0 3px var(--color-accent-muted); }
        .login-error {
          padding: 10px 14px; border-radius: var(--radius-md);
          background: var(--color-danger-muted); color: var(--color-danger);
          font-size: 13px; border: 1px solid var(--color-danger);
        }
        .login-submit {
          padding: 11px 18px; border-radius: var(--radius-md);
          background: var(--color-accent); color: #fff;
          font-size: 14px; font-weight: 600; transition: all var(--transition-fast);
          margin-top: 4px;
        }
        .login-submit:disabled { opacity: 0.5; cursor: not-allowed; }
        .login-submit:hover:not(:disabled) { background: var(--color-accent-hover); transform: translateY(-1px); }
        .login-toggle {
          text-align: center; margin-top: 20px; font-size: 13px;
          color: var(--color-text-secondary);
        }
        .login-toggle-btn {
          color: var(--color-accent); font-weight: 600; font-size: 13px;
          background: none; border: none; cursor: pointer; padding: 0;
        }
        .login-toggle-btn:hover { text-decoration: underline; }

        @media (min-width: 768px) { .login-panel-left { display: flex; } }
        @media (max-width: 767px) { .login-panel-right { padding: 60px 20px; } }
      `}</style>
    </div>
  );
}
