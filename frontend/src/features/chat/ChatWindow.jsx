import { useEffect, useMemo, useRef, useState } from 'react';
import { HiChatBubbleLeftRight, HiPaperAirplane } from 'react-icons/hi2';
import { useRoomContext } from '@livekit/components-react';
import { RoomEvent } from 'livekit-client';

function ThinkingDots() {
  return (
    <span className="er-thinking-dots" aria-hidden="true">
      <span>.</span>
      <span>.</span>
      <span>.</span>
    </span>
  );
}

function Row({ item, mine, quote }) {
  if (item.kind === 'transcript') {
    return (
      <div style={{ border: '1px solid #e8e8e8', padding: '10px 12px', background: '#fff' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 12, fontWeight: 800 }}>{mine ? 'You (voice)' : item.sender || 'Someone'}</span>
          {item.confidence != null && (
            <span style={{ fontSize: 10, fontWeight: 800, border: '1px solid #111', padding: '2px 6px' }}>
              {item.confidence >= 0.85 ? 'CLEAR' : 'REVIEW'}
            </span>
          )}
        </div>
        <div style={{ fontSize: 14, color: '#333', marginTop: 4 }}>{item.text}</div>
      </div>
    );
  }

  if (item.kind === 'ai') {
    const thinking = item.thinking && !item.text;
    return (
      <div style={{ border: '1px solid #111', borderLeftWidth: 4, padding: '10px 12px', background: '#f7f7f7' }}>
        <div style={{ fontSize: 12, fontWeight: 800 }}>AI {item.streaming ? '• typing…' : ''}</div>
        {item.thinkingText ? (
          <details open={!!item.streaming} style={{ margin: '6px 0', background: '#fff', border: '1px solid #ddd', padding: '6px 8px' }}>
            <summary style={{ cursor: 'pointer', fontSize: 12, fontWeight: 700 }}>💭 Thinking</summary>
            <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, color: '#555', marginTop: 4 }}>{item.thinkingText}</div>
          </details>
        ) : null}
        {quote && (
          <div style={{ borderLeft: '3px solid #000', padding: '4px 8px', margin: '6px 0', background: '#fff', fontSize: 12, color: '#555' }}>
            <div style={{ fontWeight: 700, color: '#111' }}>{quote.sender || 'You'}</div>
            <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 280 }}>{quote.text}</div>
          </div>
        )}
        <div style={{ fontSize: 14, color: '#111', marginTop: 4, whiteSpace: 'pre-wrap' }}>
          {thinking ? (<span style={{ color: '#666' }}>AI is thinking<ThinkingDots /></span>) : item.text}
        </div>
      </div>
    );
  }

  return (
    <div style={{ border: '1px solid #e8e8e8', padding: '10px 12px', background: mine ? '#111' : '#fff', color: mine ? '#fff' : '#111', alignSelf: mine ? 'flex-end' : 'flex-start', maxWidth: '88%' }}>
      <div style={{ fontSize: 11, fontWeight: 800, color: mine ? '#bbb' : '#666' }}>{mine ? 'You' : item.sender || `User ${item.userId ?? ''}`}</div>
      <div style={{ fontSize: 14, marginTop: 2, whiteSpace: 'pre-wrap' }}>{item.text}</div>
    </div>
  );
}

export function ChatWindow({ chat, visible, onClose, currentUserId }) {
  const { items, loading, sending, error, send } = chat;
  const [input, setInput] = useState('');
  const bottomRef = useRef(null);
  const byId = useMemo(() => new Map(items.map((it) => [it.id, it])), [items]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [items, visible]);

  async function handleSend(e) {
    e?.preventDefault();
    if (!input.trim() || sending) return;
    const ok = await send(input);
    if (ok) setInput('');
  }

  if (!visible) return null;

  return (
    <aside style={{ width: 340, maxWidth: '90vw', background: '#fff', borderLeft: '2px solid #111', display: 'flex', flexDirection: 'column', minHeight: 0 }} aria-label="Room chat">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', borderBottom: '2px solid #111' }}>
        <strong style={{ fontSize: 14, display: 'inline-flex', alignItems: 'center', gap: 8 }}><HiChatBubbleLeftRight size={16} /> Room chat</strong>
        <button onClick={onClose} aria-label="Close chat" style={{ background: '#fff', border: '1px solid #111', width: 30, height: 30, fontWeight: 800, cursor: 'pointer' }}>✕</button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 10, minHeight: 0 }}>
        {loading && <p style={{ color: '#666', fontSize: 13 }}>Loading conversation…</p>}
        {!loading && items.length === 0 && (
          <div style={{ border: '1px dashed #bbb', padding: 18, textAlign: 'center', color: '#666', fontSize: 13 }}>
            No messages yet. Say hi — or type <strong style={{ color: '#111' }}>@ai</strong> to ask the AI.
          </div>
        )}
        {items.map((item) => (
          <Row
            key={item.id}
            item={item}
            mine={item.userId != null && currentUserId != null && String(item.userId) === String(currentUserId)}
            quote={item.kind === 'ai' && item.sourceId != null ? byId.get(item.sourceId) || null : null}
          />
        ))}
        <div ref={bottomRef} />
      </div>

      {error && <div style={{ margin: '0 12px', fontSize: 12, color: '#b45309' }}>{error}</div>}

      <form onSubmit={handleSend} style={{ display: 'flex', gap: 8, padding: 12, borderTop: '2px solid #111' }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message… (@ai to ask AI)"
          aria-label="Message the room"
          style={{ flex: 1, border: '1px solid #111', padding: '11px 12px', fontSize: 14, minWidth: 0 }}
        />
        <button type="submit" disabled={!input.trim() || sending} aria-label="Send message" style={{ background: '#111', color: '#fff', border: '1px solid #111', width: 44, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', opacity: !input.trim() || sending ? 0.5 : 1 }}>
          <HiPaperAirplane size={16} />
        </button>
      </form>
    </aside>
  );
}

export function RoomDataBridge({ onData }) {
  // Gắn vào trong <LiveKitRoom>: chuyển DataReceived thành callback
  const room = useRoomContext();
  const cbRef = useRef(onData);
  cbRef.current = onData;

  useEffect(() => {
    if (!room) return;
    const handler = (payload, participant) => {
      try {
        const text = new TextDecoder().decode(payload);
        cbRef.current?.(JSON.parse(text));
      } catch {}
    };
    room.on(RoomEvent.DataReceived, handler);
    return () => room.off(RoomEvent.DataReceived, handler);
  }, [room]);

  return null;
}
