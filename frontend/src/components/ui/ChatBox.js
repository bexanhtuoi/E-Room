import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../../app/AuthContext';

export function ChatBox({ roomId, visible, onToggle }) {
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const bottomRef = useRef(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  function handleSend(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;
    setMessages((prev) => [...prev, { id: Date.now(), sender: user?.display_name || 'You', text, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
    setInput('');
  }

  if (!visible) return null;

  return (
    <aside className="chatbox">
      <div className="chatbox-header">
        <h3 className="chatbox-title">Chat</h3>
        <button className="chatbox-close" onClick={onToggle} aria-label="Close chat">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
        </button>
      </div>
      <div className="chatbox-messages scrollbar-thin">
        {messages.length === 0 && (
          <p className="chatbox-empty">No messages yet. Say hello!</p>
        )}
        {messages.map((m) => (
          <div key={m.id} className="chat-msg">
            <span className="chat-msg-sender">{m.sender}</span>
            <span className="chat-msg-text">{m.text}</span>
            <span className="chat-msg-time">{m.time}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <form className="chatbox-input-area" onSubmit={handleSend}>
        <input
          className="chatbox-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          aria-label="Chat message"
        />
        <button className="chatbox-send" type="submit" aria-label="Send message" disabled={!input.trim()}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
        </button>
      </form>
      <style>{`
        .chatbox {
          display: flex; flex-direction: column;
          width: 280px; height: 100%;
          background: var(--color-bg-elevated);
          border-left: 1px solid var(--color-border);
        }
        .chatbox-header {
          display: flex; align-items: center; justify-content: space-between;
          padding: 12px 14px; border-bottom: 1px solid var(--color-border);
        }
        .chatbox-title {
          font-family: var(--font-display); font-size: 15px; font-weight: 600;
          color: var(--color-text-primary);
        }
        .chatbox-close {
          display: flex; align-items: center; justify-content: center;
          width: 28px; height: 28px; border-radius: var(--radius-sm);
          color: var(--color-text-secondary); transition: all var(--transition-fast);
        }
        .chatbox-close:hover { color: var(--color-danger); background: var(--color-danger-muted); }
        .chatbox-messages {
          flex: 1; overflow-y: auto; padding: 12px;
          display: flex; flex-direction: column; gap: 8px;
        }
        .chatbox-empty {
          text-align: center; color: var(--color-text-muted);
          font-size: 13px; padding: 24px 0;
        }
        .chat-msg {
          display: flex; flex-direction: column; gap: 2px;
          padding: 6px 8px; border-radius: var(--radius-sm);
          background: var(--color-bg-surface);
        }
        .chat-msg-sender { font-size: 11px; font-weight: 600; color: var(--color-accent); }
        .chat-msg-text { font-size: 13px; color: var(--color-text-primary); word-break: break-word; }
        .chat-msg-time { font-size: 10px; color: var(--color-text-muted); align-self: flex-end; }
        .chatbox-input-area {
          display: flex; gap: 6px; padding: 10px 12px;
          border-top: 1px solid var(--color-border);
        }
        .chatbox-input {
          flex: 1; padding: 8px 12px; border-radius: var(--radius-md);
          border: 1px solid var(--color-border);
          background: var(--color-bg-surface);
          color: var(--color-text-primary);
          font-size: 13px; outline: none;
          transition: border var(--transition-fast);
        }
        .chatbox-input:focus { border-color: var(--color-accent); }
        .chatbox-send {
          display: flex; align-items: center; justify-content: center;
          width: 34px; height: 34px; border-radius: var(--radius-md);
          background: var(--color-accent); color: #fff;
          transition: all var(--transition-fast); flex-shrink: 0;
        }
        .chatbox-send:disabled { opacity: 0.4; cursor: not-allowed; }
        .chatbox-send:hover:not(:disabled) { background: var(--color-accent-hover); }
      `}</style>
    </aside>
  );
}
