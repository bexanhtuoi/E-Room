import { useEffect, useState } from 'react';
import { HiSparkles } from 'react-icons/hi2';

const HEARTBEAT_EMOJIS = ['🤖', '💡', '🗣️', '🎯', '💬'];

export function HeartbeatMessage({ message }) {
  const [emoji] = useState(() => HEARTBEAT_EMOJIS[Math.floor(Math.random() * HEARTBEAT_EMOJIS.length)]);

  if (!message) return null;

  return (
    <div style={{
      padding: '10px 14px', borderRadius: 14,
      background: 'var(--color-bg-surface)',
      border: '1px solid var(--color-border)',
      marginBottom: 8,
      animation: 'fadeIn 0.3s ease',
    }}>
      <div className="d-flex align-items-start gap-2">
        <div style={{
          width: 28, height: 28, borderRadius: '50%',
          background: 'rgba(255,255,255,0.08)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0, fontSize: '0.8rem',
        }}>
          {emoji}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--color-accent)', marginBottom: 2 }}>
            AI Coach
          </div>
          <div style={{ fontSize: '0.88rem', lineHeight: 1.5, color: 'var(--color-text-primary)' }}>
            {message.text}
          </div>
        </div>
      </div>
    </div>
  );
}
