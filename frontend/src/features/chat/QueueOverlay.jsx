import { useState, useEffect } from 'react';
import Spinner from 'react-bootstrap/Spinner';

export function QueueOverlay({ visible, tags = [], onCancel }) {
  const [dots, setDots] = useState('');
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!visible) return;
    const dotInterval = setInterval(() => {
      setDots((prev) => (prev.length >= 3 ? '' : prev + '.'));
    }, 500);
    const timerInterval = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);
    return () => {
      clearInterval(dotInterval);
      clearInterval(timerInterval);
      setElapsed(0);
    };
  }, [visible]);

  if (!visible) return null;

  const remaining = Math.max(0, 30 - elapsed);
  const showFallback = elapsed > 25;

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1050,
      background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 16,
    }}>
      <div style={{
        textAlign: 'center', maxWidth: 400, animation: 'scaleIn 0.3s ease',
      }}>
        {/* Animated search icon */}
        <div style={{
          width: 80, height: 80, borderRadius: '50%',
          background: 'var(--color-accent-muted)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 20px',
          animation: 'pulse-glow 2s ease-in-out infinite',
          position: 'relative',
        }}>
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="var(--color-accent)" strokeWidth="2" strokeLinecap="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          {/* Rotating ring */}
          <Spinner animation="border" variant="primary" size="sm" style={{
            position: 'absolute', width: 90, height: 90,
            borderWidth: 2,
          }} />
        </div>

        <h4 className="fw-extrabold mb-2" style={{ fontFamily: 'Nunito, sans-serif', color: '#fff' }}>
          Finding your match{dots}
        </h4>

        {tags.length > 0 && (
          <p className="mb-2" style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>
            Looking for people interested in
            <span style={{ color: 'var(--color-accent)', fontWeight: 600 }}>
              {' '}{tags.join(', ')}
            </span>
          </p>
        )}

        <p style={{ color: 'var(--color-text-muted)', fontSize: '0.78rem' }}>
          {showFallback
            ? 'No matches found yet. Expanding search...'
            : `Est. wait: ~${remaining}s`}
        </p>

        {/* Fallback options */}
        {showFallback && (
          <div style={{
            marginTop: 16, padding: '12px 16px', borderRadius: 12,
            background: 'rgba(251,191,36,0.1)',
            border: '1px solid rgba(251,191,36,0.2)',
          }}>
            <p className="small mb-2" style={{ color: 'var(--color-warning)', fontWeight: 600 }}>
              💡 Taking longer than expected
            </p>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
              <span style={{
                padding: '6px 14px', borderRadius: 99,
                background: 'var(--color-bg-hover)', color: 'var(--color-text-muted)',
                fontSize: '0.78rem', fontWeight: 600,
              }}>
                🔄 Expand tags
              </span>
              <span style={{
                padding: '6px 14px', borderRadius: 99,
                background: 'var(--color-accent-muted)', color: 'var(--color-accent)',
                fontSize: '0.78rem', fontWeight: 600,
              }}>
                🤖 Practice with AI
              </span>
            </div>
          </div>
        )}

        <button
          onClick={onCancel}
          style={{
            marginTop: 20, padding: '8px 24px', borderRadius: 99,
            background: 'transparent',
            border: '1px solid rgba(255,255,255,0.2)',
            color: 'var(--color-text-muted)', cursor: 'pointer',
            fontFamily: 'inherit', fontSize: '0.82rem', fontWeight: 600,
            transition: 'all 0.12s',
          }}
          onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; }}
          onMouseOut={(e) => { e.currentTarget.style.background = 'transparent'; }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
