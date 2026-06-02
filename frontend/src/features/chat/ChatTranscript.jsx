import { useEffect, useRef } from 'react';

export function ChatTranscript({ messages = [], loading }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (loading) {
    return <div className="text-muted text-center py-4" style={{ fontSize: '0.85rem' }}>Loading transcript...</div>;
  }

  if (messages.length === 0) {
    return (
      <div className="text-center py-5" style={{ color: 'var(--color-text-muted)' }}>
        <div style={{ fontSize: '2rem', marginBottom: 8 }}>🎙️</div>
        <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>No speech yet</div>
        <div style={{ fontSize: '0.78rem' }}>Start speaking — transcript appears here instantly</div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {messages.map((msg, i) => (
        <div key={msg.id || i} style={{
          display: 'flex', gap: 8, alignItems: 'flex-start',
          opacity: msg.status === 'interim' ? 0.7 : 1,
        }}>
          <span className="fw-bold" style={{
            fontSize: '0.75rem', color: msg.speakerColor || 'var(--color-accent)',
            whiteSpace: 'nowrap', flexShrink: 0, marginTop: 2, minWidth: 40,
          }}>
            {msg.speaker || 'You'}
          </span>
          <span style={{
            fontSize: '0.88rem', lineHeight: 1.5,
            color: msg.status === 'interim' ? 'var(--color-text-muted)' : 'var(--color-text-primary)',
            fontStyle: msg.status === 'interim' ? 'italic' : 'normal',
            transition: 'all 0.2s',
          }}>
            {msg.text}
            {msg.status === 'interim' && <span className="blink" style={{ marginLeft: 2 }}>▌</span>}
          </span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
