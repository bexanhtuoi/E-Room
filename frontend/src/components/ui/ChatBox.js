import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../../app/AuthContext';
import { HiPaperAirplane } from 'react-icons/hi2';

function getInitials(name) {
  if (!name) return '?';
  return name
    .split(' ')
    .map(w => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function formatTime(d) {
  const date = typeof d === 'string' ? new Date(d) : d;
  if (isNaN(date.getTime())) return '';
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

const COLOR_PALETTE = [
  '#6366f1', '#8b5cf6', '#ec4899', '#f59e0b',
  '#10b981', '#06b6d4', '#f43f5e', '#84cc16',
];

function hashColor(name) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return COLOR_PALETTE[Math.abs(hash) % COLOR_PALETTE.length];
}

export function ChatBox({ roomId, visible, onToggle }) {
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const inputRef = useRef(null);
  const bottomRef = useRef(null);
  const listRef = useRef(null);
  const storageKey = `eroom-chat-${roomId}`;

  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          setMessages(parsed.map(m => ({ ...m, time: new Date(m.time) })));
        }
      }
    } catch {  }
  }, [storageKey]);

  useEffect(() => {
    if (messages.length > 0) {
      try { localStorage.setItem(storageKey, JSON.stringify(messages)); } catch {  }
    }
  }, [messages, storageKey]);

  useEffect(() => {
    if (visible) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [visible]);

  useEffect(() => {
    const el = bottomRef.current;
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const currentUser = user?.display_name || 'You';
  const currentUserId = user?.id || 'me';

  function handleSend(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;
    setMessages(prev => [...prev, {
      id: Date.now(),
      senderId: currentUserId,
      sender: currentUser,
      text,
      time: new Date(),
    }]);
    setInput('');
    setTyping(false);
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(e);
    }
  }

  function handleInput(e) {
    setInput(e.target.value);
    if (e.target.value && !typing) setTyping(true);
    if (!e.target.value && typing) {
      const t = setTimeout(() => setTyping(false), 800);
      return () => clearTimeout(t);
    }
  }

  if (!visible) return null;

  return (
    <aside className="chatbox-v2">

      <header className="chat-v2-header">
        <div className="chat-v2-header-info">
          <div className="chat-v2-header-dot" />
          <h3 className="chat-v2-title">In-call Chat</h3>
          <span className="chat-v2-count">
            {messages.length > 0 ? `${messages.length} message${messages.length > 1 ? 's' : ''}` : 'No messages'}
          </span>
        </div>
        <button className="chat-v2-close" onClick={onToggle} aria-label="Close chat">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </header>

      <div className="chat-v2-messages" ref={listRef}>
        {messages.length === 0 ? (
          <div className="chat-v2-empty">
            <div className="chat-v2-empty-icon">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                <line x1="9" y1="10" x2="15" y2="10" /><line x1="12" y1="7" x2="12" y2="13" />
              </svg>
            </div>
            <p className="chat-v2-empty-title">Start the conversation</p>
            <p className="chat-v2-empty-sub">Say hello and break the ice!</p>
          </div>
        ) : (
          messages.map((m, i) => {
            const isMine = m.senderId === currentUserId;
            const showAvatar = i === 0 || messages[i - 1]?.senderId !== m.senderId;
            const showTime = i === messages.length - 1
              || messages[i + 1]?.senderId !== m.senderId
              || (m.time - messages[i + 1]?.time > 5 * 60 * 1000);

            return (
              <div
                key={m.id}
                className={`chat-v2-msg ${isMine ? 'mine' : ''} ${showAvatar ? 'first' : 'cont'}`}
              >
                {!isMine && showAvatar && (
                  <div
                    className="chat-v2-avatar"
                    style={{ background: hashColor(m.sender) }}
                  >
                    {getInitials(m.sender)}
                  </div>
                )}
                <div className={`chat-v2-bubble ${isMine ? 'mine' : ''} ${!showAvatar ? 'cont' : ''}`}>
                  {!isMine && showAvatar && (
                    <span className="chat-v2-sender" style={{ color: hashColor(m.sender) }}>
                      {m.sender}
                    </span>
                  )}
                  <span className="chat-v2-text">{m.text}</span>
                </div>
                {isMine && showAvatar && (
                  <div
                    className="chat-v2-avatar"
                    style={{ background: hashColor(m.sender) }}
                  >
                    {getInitials(m.sender)}
                  </div>
                )}
                {showTime && (
                  <span className="chat-v2-time">{formatTime(m.time)}</span>
                )}
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>

      {typing && (
        <div className="chat-v2-typing">
          <div className="chat-v2-typing-dots">
            <span /><span /><span />
          </div>
          <span>typing...</span>
        </div>
      )}

      <form className="chat-v2-input" onSubmit={handleSend}>
        <div className="chat-v2-input-wrapper">
          <input
            ref={inputRef}
            className="chat-v2-input-field"
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            aria-label="Chat message"
            autoComplete="off"
          />
          <button
            className={`chat-v2-send ${input.trim() ? 'active' : ''}`}
            type="submit"
            aria-label="Send message"
            disabled={!input.trim()}
          >
            <HiPaperAirplane size={17} />
          </button>
        </div>
      </form>

      <style>{`

        .chatbox-v2 {
          display: flex; flex-direction: column;
          width: 100%; height: 100%;
          background: var(--color-bg-elevated);
          font-family: 'Nunito', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        .chat-v2-header {
          display: flex; align-items: center; justify-content: space-between;
          padding: 14px 16px;
          border-bottom: 1px solid var(--color-border);
          flex-shrink: 0;
        }
        .chat-v2-header-info {
          display: flex; align-items: center; gap: 10px;
        }
        .chat-v2-header-dot {
          width: 8px; height: 8px; border-radius: 50%;
          background: var(--color-success);
          box-shadow: 0 0 6px var(--color-success);
          flex-shrink: 0;
        }
        .chat-v2-title {
          font-family: 'Nunito', sans-serif; font-size: 14px; font-weight: 700;
          color: var(--color-text-primary); margin: 0; line-height: 1;
        }
        .chat-v2-count {
          font-size: 11px; color: var(--color-text-muted);
          background: var(--color-bg-surface);
          padding: 2px 10px; border-radius: 99px;
          font-weight: 600;
        }
        .chat-v2-close {
          display: flex; align-items: center; justify-content: center;
          width: 30px; height: 30px; border-radius: 50%; border: none;
          background: transparent; color: var(--color-text-muted);
          cursor: pointer; transition: all 0.15s;
        }
        .chat-v2-close:hover {
          color: var(--color-danger);
          background: var(--color-danger-muted);
        }

        .chat-v2-messages {
          flex: 1; overflow-y: auto; padding: 14px 12px;
          display: flex; flex-direction: column;
          gap: 2px;
          scroll-behavior: smooth;
        }
        .chat-v2-messages::-webkit-scrollbar { width: 4px; }
        .chat-v2-messages::-webkit-scrollbar-track { background: transparent; }
        .chat-v2-messages::-webkit-scrollbar-thumb {
          background: var(--color-border-strong); border-radius: 4px;
        }

        .chat-v2-empty {
          display: flex; flex-direction: column; align-items: center;
          justify-content: center; flex: 1; text-align: center;
          gap: 8px; padding: 40px 20px;
        }
        .chat-v2-empty-icon {
          width: 64px; height: 64px; border-radius: 50%;
          background: var(--color-bg-surface);
          display: flex; align-items: center; justify-content: center;
          color: var(--color-text-muted); margin-bottom: 8px;
        }
        .chat-v2-empty-title {
          color: var(--color-text-primary); font-weight: 700;
          font-size: 14px; margin: 0;
        }
        .chat-v2-empty-sub {
          color: var(--color-text-muted); font-size: 12px; margin: 0;
        }

        .chat-v2-msg {
          display: flex; align-items: flex-end; gap: 8px;
          max-width: 92%; animation: msgIn 0.2s ease both;
        }
        .chat-v2-msg.mine { align-self: flex-end; flex-direction: row-reverse; }
        .chat-v2-msg.cont { margin-top: 0; }
        .chat-v2-msg.first { margin-top: 8px; }

        @keyframes msgIn {
          from { opacity: 0; transform: translateY(6px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .chat-v2-avatar {
          width: 28px; height: 28px; min-width: 28px;
          border-radius: 50%; display: flex; align-items: center;
          justify-content: center; font-size: 10px; font-weight: 800;
          color: #fff; letter-spacing: 0.5px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        }

        .chat-v2-bubble {
          display: flex; flex-direction: column;
          padding: 9px 13px; border-radius: 16px;
          background: var(--color-bg-surface);
          max-width: 100%; word-break: break-word;
          position: relative;
        }
        .chat-v2-bubble.mine {
          background: var(--color-accent-gradient);
          color: #fff;
          border-bottom-right-radius: 4px;
        }
        .chat-v2-bubble:not(.mine) {
          border-bottom-left-radius: 4px;
        }
        .chat-v2-bubble.cont {
          border-bottom-left-radius: 16px;
          border-bottom-right-radius: 16px;
        }
        .chat-v2-bubble.mine.cont {
          border-bottom-left-radius: 16px;
          border-bottom-right-radius: 4px;
        }

        .chat-v2-sender {
          font-size: 10px; font-weight: 700; margin-bottom: 2px;
          letter-spacing: 0.02em;
        }
        .chat-v2-text {
          font-size: 13px; line-height: 1.5;
        }
        .chat-v2-bubble.mine .chat-v2-text { color: #fff; }

        .chat-v2-time {
          font-size: 9px; color: var(--color-text-muted);
          align-self: flex-end; white-space: nowrap;
          margin-top: 1px; padding: 0 4px;
        }
        .chat-v2-msg.mine .chat-v2-time { margin-right: 36px; }

        .chat-v2-typing {
          display: flex; align-items: center; gap: 8px;
          padding: 6px 18px; font-size: 11px;
          color: var(--color-text-muted); font-style: italic;
          flex-shrink: 0;
        }
        .chat-v2-typing-dots {
          display: flex; gap: 3px;
        }
        .chat-v2-typing-dots span {
          width: 5px; height: 5px; border-radius: 50%;
          background: var(--color-text-muted);
          animation: typingBounce 1.4s ease-in-out infinite;
        }
        .chat-v2-typing-dots span:nth-child(2) { animation-delay: 0.2s; }
        .chat-v2-typing-dots span:nth-child(3) { animation-delay: 0.4s; }

        @keyframes typingBounce {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.3; }
          30% { transform: translateY(-5px); opacity: 1; }
        }

        .chat-v2-input {
          padding: 10px 12px 12px;
          border-top: 1px solid var(--color-border);
          flex-shrink: 0;
        }
        .chat-v2-input-wrapper {
          display: flex; align-items: center; gap: 8px;
          background: var(--color-bg-surface);
          border-radius: 99px; padding: 4px 4px 4px 16px;
          border: 1px solid var(--color-border);
          transition: border-color 0.2s, box-shadow 0.2s;
        }
        .chat-v2-input-wrapper:focus-within {
          border-color: var(--color-accent);
          box-shadow: 0 0 0 3px var(--color-accent-muted);
        }
        .chat-v2-input-field {
          flex: 1; border: none; background: transparent;
          padding: 8px 0; font-size: 13px; font-family: inherit;
          color: var(--color-text-primary); outline: none;
        }
        .chat-v2-input-field::placeholder {
          color: var(--color-text-muted);
        }
        .chat-v2-send {
          width: 36px; height: 36px; min-width: 36px;
          border-radius: 50%; border: none;
          background: var(--color-bg-hover); color: var(--color-text-muted);
          cursor: pointer; display: flex; align-items: center;
          justify-content: center; transition: all 0.2s;
          flex-shrink: 0;
        }
        .chat-v2-send.active {
          background: var(--color-accent-gradient); color: #fff;
          box-shadow: 0 3px 12px var(--color-accent-glow);
          transform: scale(1.05);
        }
        .chat-v2-send:disabled { cursor: not-allowed; }
        .chat-v2-send.active:hover { transform: scale(1.1); }
      `}</style>
    </aside>
  );
}
