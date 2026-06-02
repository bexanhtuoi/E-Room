import { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import { useChatState } from './useChatState';
import { HiPaperAirplane, HiSpeakerWave } from 'react-icons/hi2';
import '../../styles/ChatWindow.css';

function getItemTime(item) {
  return new Date(item.time || item.createdAt || item.timestamp || item.created_at || Date.now()).getTime();
}

export function ChatWindow({ roomId, visible, onToggle, wsSocket }) {
  const {
    transcripts, corrections, chatMessages,
    loadingHistory, input, setInput, inputRef, bottomRef,
    handleSend, handleTTS, currentUserId,
  } = useChatState(roomId, wsSocket, visible);

  const feedItems = useMemo(() => {
    const chat = chatMessages.map((message) => ({ type: 'chat', item: message, time: getItemTime(message) }));
    const speech = transcripts.map((message) => ({ type: 'speech', item: message, time: getItemTime(message) }));
    const correctionItems = corrections.map((correction) => ({ type: 'correction', item: correction, time: getItemTime(correction) }));

    return [...chat, ...speech, ...correctionItems].sort((a, b) => a.time - b.time);
  }, [chatMessages, transcripts, corrections]);

  if (!visible) return null;

  return (
    <aside className="chat-window" aria-label="Room conversation panel">
      <div className="chat-window__feed">
        {loadingHistory ? (
          <div className="chat-window__empty">Loading conversation...</div>
        ) : feedItems.length === 0 ? (
          <div className="chat-window__empty">
            <strong>Start the room conversation</strong>
            <span>Messages, live speech and feedback will appear in one timeline.</span>
          </div>
        ) : (
          feedItems.map(({ type, item }, index) => {
            if (type === 'correction') {
              const original = item.original || '';
              const pronunciationFeedback = item.pronunciation_feedback || '';
              const errors = item.errors || [];
              const ttsText = item.tts_text || item.corrected || '';
              const btnStyle = {
                marginTop: 8, padding: '4px 12px', borderRadius: 99,
                background: 'transparent',
                border: '1px solid var(--color-border)',
                color: 'var(--color-text-secondary)',
                cursor: 'pointer', fontSize: '0.75rem',
                fontFamily: 'inherit', fontWeight: 600,
                display: 'inline-flex', alignItems: 'center', gap: 4,
                transition: 'all 0.12s',
              };
              return (
                <div className="chat-window__message" key={item.id || `correction-${index}`}>
                  <span className="chat-window__sender">Assistant</span>
                  <div className="chat-window__bubble">
                    {original ? (
                      <div style={{
                        fontSize: '0.82rem', fontWeight: 600, marginBottom: 8,
                        color: 'var(--color-text-secondary)',
                        lineHeight: 1.4,
                      }}>
                        "{original}"
                      </div>
                    ) : null}
                    {pronunciationFeedback ? (
                      <div style={{ fontSize: '0.82rem', lineHeight: 1.5, marginBottom: 8, whiteSpace: 'pre-wrap' }}>
                        {pronunciationFeedback}
                      </div>
                    ) : null}
                    {errors.length > 0 ? (
                      <div style={{ marginTop: 8, borderTop: '1px solid var(--color-border)', paddingTop: 8 }}>
                        {handleTTS && ttsText ? (
                          <button
                            onClick={() => handleTTS(ttsText)}
                            style={{ ...btnStyle, marginTop: 0, marginBottom: 6, padding: '3px 12px', fontSize: '0.72rem' }}
                          >
                            <HiSpeakerWave size={12} /> Nghe cả câu
                          </button>
                        ) : null}
                        <div style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: 6 }}>
                          Phát âm từng từ:
                        </div>
                        {errors.map((e, ei) => (
                          <div key={ei} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                            <span style={{ fontSize: '0.82rem', fontWeight: 600 }}>{e.corrected}</span>
                            {handleTTS ? (
                              <button
                                onClick={(ev) => { ev.stopPropagation(); handleTTS(e.corrected); }}
                                style={{
                                  ...btnStyle, marginTop: 0, padding: '2px 10px',
                                }}
                                onMouseOver={(ev) => { ev.currentTarget.style.background = 'var(--color-bg-hover)'; }}
                                onMouseOut={(ev) => { ev.currentTarget.style.background = 'transparent'; }}
                              >
                                <HiSpeakerWave size={12} />
                              </button>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    ) : null}
                    {handleTTS && ttsText && errors.length === 0 ? (
                      <button
                        onClick={() => handleTTS(ttsText)}
                        style={btnStyle}
                        onMouseOver={(e) => { e.currentTarget.style.background = 'var(--color-bg-hover)'; }}
                        onMouseOut={(e) => { e.currentTarget.style.background = 'transparent'; }}
                      >
                        <HiSpeakerWave size={14} /> Hear correct pronunciation
                      </button>
                    ) : null}
                  </div>
                </div>
              );
            }
            if (type === 'speech') {
              return (
                <div className="chat-window__message is-mine" key={item.id || `speech-${index}`}>
                  <span className="chat-window__sender">You</span>
                  <div className="chat-window__bubble"><ReactMarkdown>{item.text || item.content || ''}</ReactMarkdown></div>
                </div>
              );
            }

            const isMine = item.senderId === currentUserId;
            return (
              <div className={`chat-window__message ${isMine ? 'is-mine' : ''}`} key={item.id || `chat-${index}`}>
                <span className="chat-window__sender">{isMine ? 'You' : (item.senderId === 'assistant' ? 'assistant' : item.sender)}</span>
                <div className="chat-window__bubble"><ReactMarkdown>{item.text || ''}</ReactMarkdown></div>
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>

      <form className="chat-window__composer" onSubmit={handleSend}>
        <input ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)}
          placeholder="Message the room..."
          aria-label="Message the room"
        />
        <button type="submit" disabled={!input.trim()} aria-label="Send message">
          <HiPaperAirplane size={15} />
        </button>
      </form>
    </aside>
  );
}
