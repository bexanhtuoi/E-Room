import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { FcGoogle } from 'react-icons/fc';
import { useAuth } from '../../app/AuthContext';
import { LogoMark } from '../../components/brand/LogoMark';

function passwordScore(pw) {
  return {
    len: pw.length >= 8,
    letter: /[A-Za-z]/.test(pw),
    digit: /[0-9]/.test(pw),
    upper: /[A-Z]/.test(pw),
    symbol: /[^A-Za-z0-9]/.test(pw),
  };
}

function suggestPassword() {
  const words = ['Kite', 'River', 'Maple', 'Comet', 'Drum', 'Fox', 'Mint', 'Oasis'];
  const word = words[Math.floor(Math.random() * words.length)];
  const digits = String(Math.floor(1000 + Math.random() * 9000));
  const symbols = ['!', '#', '%', '&', '*'];
  const symbol = symbols[Math.floor(Math.random() * symbols.length)];
  return `Eroom-${word}-${digits}${symbol}`;
}

function PasswordGuide({ password }) {
  const [suggested, setSuggested] = useState(false);
  const rules = passwordScore(password);
  const requiredOk = rules.len && rules.letter && rules.digit;
  const great = requiredOk && rules.upper && rules.symbol;

  if (!password) return null;

  if (great) {
    return (
      <div style={{ border: '1px solid #15803d', background: '#f0fdf4', padding: '10px 12px', fontSize: 13, fontWeight: 800, color: '#15803d' }}>
        ✓ Great password — strong and ready.
      </div>
    );
  }

  return (
    <div style={{ border: '1px solid #e8e8e8', padding: '12px', display: 'grid', gap: 7 }}>
      {[
        ['8+ characters', rules.len],
        ['A letter (a–z)', rules.letter],
        ['A number (0–9)', rules.digit],
        ['Uppercase — recommended', rules.upper],
        ['Symbol (!#%…) — recommended', rules.symbol],
      ].map(([label, ok]) => (
        <div key={label} style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, color: ok ? '#111' : '#999' }}>
          <span style={{ width: 18, height: 18, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', border: `1px solid ${ok ? '#111' : '#ddd'}`, background: ok ? '#111' : '#fff', color: '#fff', fontSize: 11, fontWeight: 800 }}>
            {ok ? '✓' : ''}
          </span>
          {label}
        </div>
      ))}
      {!requiredOk && (
        <div style={{ fontSize: 12, color: '#b45309', background: '#fffbeb', border: '1px solid #fcd34d', padding: '8px 10px', marginTop: 4 }}>
          Heads up: sign-up needs 8+ characters with a letter and a number.
        </div>
      )}
      {requiredOk && (
        <div style={{ fontSize: 13, fontWeight: 800, marginTop: 2 }}>Good password — add uppercase + symbol for Great.</div>
      )}
      <button
        type="button"
        onClick={() => { setSuggested(true); }}
        style={{ background: 'none', border: 'none', padding: 0, fontSize: 13, fontWeight: 700, textDecoration: 'underline', cursor: 'pointer', textAlign: 'left', color: '#111' }}
      >
        Suggest a strong one for me
      </button>
      {suggested && <SuggestedBox />}
    </div>
  );
}

function SuggestedBox() {
  const [value, setValue] = useState(() => suggestPassword());
  const [copied, setCopied] = useState(false);

  function regenerate() {
    let next = suggestPassword();
    while (next === value) next = suggestPassword();
    setValue(next);
    setCopied(false);
  }

  function copy() {
    navigator.clipboard?.writeText(value).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function useIt() {
    const input = document.querySelector('input[data-password-input]');
    if (input) {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(input, value);
      input.dispatchEvent(new Event('input', { bubbles: true }));
    }
  }

  return (
    <div style={{ border: '1px dashed #111', padding: '10px', display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
      <code style={{ fontSize: 14, fontWeight: 800 }}>{value}</code>
      <button type="button" onClick={copy} style={{ fontSize: 12, fontWeight: 800, border: '1px solid #111', background: '#fff', padding: '5px 10px', cursor: 'pointer' }}>
        {copied ? 'Copied ✓' : 'Copy'}
      </button>
      <button type="button" onClick={regenerate} title="Suggest another one" style={{ fontSize: 12, fontWeight: 800, border: '1px solid #111', background: '#fff', padding: '5px 10px', cursor: 'pointer' }}>
        ↻ New
      </button>
      <button type="button" onClick={useIt} style={{ fontSize: 12, fontWeight: 800, background: '#111', color: '#fff', border: '1px solid #111', padding: '5px 10px', cursor: 'pointer' }}>
        Use it
      </button>
    </div>
  );
}

export function LoginPage() {
  const { login, register, refresh, googleLogin } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const status = params.get('google');
    if (status === 'ok') {
      refresh().then((me) => {
        if (me) navigate('/rooms', { replace: true });
        else setError('Google sign-in did not create a session. Please try again.');
      });
    } else if (status === 'error') {
      setError('Google sign-in failed or was cancelled. Please try email instead.');
    }
  }, []);

  async function submit(e) {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      if (mode === 'register') {
        const parts = form.name.trim().split(/\s+/);
        await register(form.email, form.password, parts[0] || 'Learner', parts.slice(1).join(' ') || 'User');
      }
      await login(form.email, form.password);
      navigate('/rooms', { replace: true });
    } catch (err) {
      setError(err.message || 'Authentication failed. Check your email and password.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="er" style={{ minHeight: '100svh', display: 'flex', alignItems: 'center', padding: '72px 0', background: '#f7f7f7' }}>
      <div className="er-container" style={{ maxWidth: 520 }}>
        <div style={{ background: '#fff', border: '2px solid #111', padding: 'clamp(28px,4vw,44px)' }}>
          <div style={{ display: 'flex', justifyContent: 'center' }}><LogoMark size={34} /></div>
          <h1 style={{ textAlign: 'center', fontSize: 28, fontWeight: 800, margin: '18px 0 6px', color: '#000' }}>
            {mode === 'login' ? 'Welcome back' : 'Join E-Room free'}
          </h1>
          <p style={{ textAlign: 'center', color: '#666', fontSize: 14, margin: '0 0 20px' }}>
            {mode === 'login' ? 'Sign in to join live topic rooms.' : 'Create an account. First 5 rooms every week are free.'}
          </p>

          <div style={{ display: 'flex', border: '1px solid #111', marginBottom: 20 }}>
            {['login', 'register'].map((m) => (
              <button key={m} type="button" onClick={() => { setMode(m); setError(''); }} style={{ flex: 1, padding: '12px 0', fontWeight: 800, fontSize: 14, background: mode === m ? '#111' : '#fff', color: mode === m ? '#fff' : '#111', border: 'none', cursor: 'pointer' }}>
                {m === 'login' ? 'Sign in' : 'Sign up'}
              </button>
            ))}
          </div>

          <button type="button" className="er-btn er-btn--ghost" style={{ width: '100%', justifyContent: 'center' }} onClick={googleLogin}>
            <FcGoogle size={18} /> Continue with Google
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '20px 0', color: '#999', fontSize: 12, fontWeight: 700 }}>
            <span style={{ flex: 1, height: 1, background: '#e8e8e8' }} /> OR WITH EMAIL <span style={{ flex: 1, height: 1, background: '#e8e8e8' }} />
          </div>

          <form onSubmit={submit} style={{ display: 'grid', gap: 14 }}>
            {mode === 'register' && (
              <div><label className="er-label">Full name</label><input className="er-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Nguyen Van A" required /></div>
            )}
            <div><label className="er-label">Email</label><input className="er-input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@email.com" required /></div>
            <div>
              <label className="er-label">Password</label>
              <div style={{ position: 'relative' }}>
                <input data-password-input className="er-input" type={showPw ? 'text' : 'password'} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="8+ characters" required minLength={8} style={{ paddingRight: 64 }} />
                <button type="button" onClick={() => setShowPw((v) => !v)} style={{ position: 'absolute', right: 8, top: 8, background: 'none', border: '1px solid #e8e8e8', fontSize: 12, fontWeight: 700, padding: '5px 8px', cursor: 'pointer' }}>{showPw ? 'Hide' : 'Show'}</button>
              </div>
            </div>
            {mode === 'register' && <PasswordGuide password={form.password} />}
            {mode === 'login' && <div style={{ textAlign: 'right' }}><button type="button" style={{ background: 'none', border: 'none', fontSize: 13, fontWeight: 700, textDecoration: 'underline', cursor: 'pointer' }}>Forgot password?</button></div>}
            {error && <div className="er-alert er-alert--err">{error}</div>}
            <button className="er-btn" type="submit" disabled={busy} style={{ justifyContent: 'center' }}>{busy ? 'Please wait…' : mode === 'login' ? 'Sign in →' : 'Create free account →'}</button>
          </form>

          <p style={{ textAlign: 'center', fontSize: 12, color: '#999', marginTop: 18 }}>Protected by secure cookies. By continuing you agree to the Terms and Privacy Policy.</p>
          <p style={{ textAlign: 'center', fontSize: 14, marginTop: 8 }}><Link to="/" style={{ color: '#111', fontWeight: 700 }}>← Back to home</Link></p>
        </div>
      </div>
    </div>
  );
}
