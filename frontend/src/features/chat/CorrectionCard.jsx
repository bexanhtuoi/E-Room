import { useState } from 'react';
import { HiSpeakerWave, HiCheckCircle, HiXCircle } from 'react-icons/hi2';

export function CorrectionCard({ correction, onTTS }) {
  const [showExplanation, setShowExplanation] = useState(false);

  if (!correction) return null;

  return (
    <div style={{
      padding: '12px 14px', borderRadius: 14,
      background: 'var(--color-bg-surface)',
      border: '1px solid var(--color-border)',
      marginBottom: 8,
      transition: 'all 0.15s',
    }}>
      <div className="d-flex align-items-start gap-2">
        <div style={{
          width: 24, height: 24, borderRadius: '50%',
          background: 'var(--color-accent-muted)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0, marginTop: 1,
        }}>
          <HiCheckCircle size={14} style={{ color: 'var(--color-accent)' }} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Original */}
          <div style={{ fontSize: '0.82rem', color: 'var(--color-danger)', marginBottom: 2 }}>
            <span style={{ textDecoration: 'line-through', textDecorationColor: 'var(--color-danger)' }}>
              {correction.original}
            </span>
          </div>
          {/* Corrected */}
          <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--color-success)', marginBottom: 4 }}>
            {correction.corrected}
            {correction.severity === 'major' && (
              <span style={{
                marginLeft: 6, fontSize: '0.6rem', padding: '1px 6px',
                borderRadius: 99, background: 'var(--color-danger-muted)',
                color: 'var(--color-danger)', fontWeight: 700,
              }}>
                IMPORTANT
              </span>
            )}
          </div>
          {/* Type badge */}
          <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 2 }}>
            <span style={{
              padding: '1px 8px', borderRadius: 99,
              background: 'var(--color-bg-hover)', color: 'var(--color-text-muted)',
              fontSize: '0.65rem', fontWeight: 600,
            }}>
              {correction.type}
            </span>
          </div>
          {/* Explanation toggle */}
          <div
            onClick={() => setShowExplanation(!showExplanation)}
            style={{ cursor: 'pointer', fontSize: '0.78rem', color: 'var(--color-accent)' }}
          >
            {showExplanation ? correction.explanation : 'Why? Tap to expand'}
          </div>
          {/* TTS button */}
          {onTTS && (
            <button
              onClick={() => onTTS(correction.corrected)}
              style={{
                marginTop: 6, padding: '4px 12px', borderRadius: 99,
                background: 'transparent',
                border: '1px solid var(--color-border)',
                color: 'var(--color-text-secondary)',
                cursor: 'pointer', fontSize: '0.75rem',
                fontFamily: 'inherit', fontWeight: 600,
                display: 'inline-flex', alignItems: 'center', gap: 4,
                transition: 'all 0.12s',
              }}
              onMouseOver={(e) => { e.currentTarget.style.background = 'var(--color-bg-hover)'; }}
              onMouseOut={(e) => { e.currentTarget.style.background = 'transparent'; }}
            >
              <HiSpeakerWave size={14} /> Hear correct pronunciation
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
