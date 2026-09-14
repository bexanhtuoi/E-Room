import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { HiArrowLeft, HiChatBubbleLeftRight, HiClock, HiPaperAirplane, HiSparkles, HiUsers } from 'react-icons/hi2';
import { API_BASE_URL, fetchJson, getTokens } from '../../lib/api';
import { Face } from '../../components/common/Faces';
import '../../styles/ProfilePage.css';

const QUICK_PROMPTS = [
  'Recap it for Notion',
  'What did we decide?',
  'Which new words appeared?',
  'Give me feedback on my English',
  'What should I practice next?',
];

function parseTranscript(text) {
  return String(text || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, i) => {
      const cut = line.indexOf(':');
      return {
        id: i,
        speaker: cut > 0 ? line.slice(0, cut).trim() : null,
        body: cut > 0 ? line.slice(cut + 1).trim() : line,
      };
    });
}

function formatDuration(seconds) {
  if (seconds == null) return 'ongoing';
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  if (mins < 60) return `${mins}m`;
  return `${Math.floor(mins / 60)}h ${mins % 60}m`;
}

function formatShortDateTime(iso) {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';
  return `${date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}, ${date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}`;
}

async function* readSseEvents(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split('\n\n');
    buffer = frames.pop() || '';
    for (const frame of frames) {
      for (const line of frame.split('\n')) {
        const clean = line.trim();
        if (!clean.startsWith('data:')) continue;
        try {
          yield JSON.parse(clean.slice(5).trim());
        } catch {
          /* skip partial frame */
        }
      }
    }
  }
}

export function SessionDetailPage() {
  const { sessionId } = useParams();
  const [question, setQuestion] = useState('');
  const [chat, setChat] = useState([]);
  const [thinkingText, setThinkingText] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [askError, setAskError] = useState('');
  const chatEndRef = useRef(null);

  const detailQuery = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => fetchJson(`/sessions/${sessionId}`),
    enabled: Boolean(sessionId),
    retry: false,
  });
  const messagesQuery = useQuery({
    queryKey: ['session', sessionId, 'messages'],
    queryFn: () => fetchJson(`/sessions/${sessionId}/messages`),
    enabled: Boolean(sessionId),
    retry: false,
  });

  const detail = detailQuery.data ?? null;
  const session = detail?.session ?? null;
  const room = detail?.room ?? null;
  const savedChat = useMemo(() => {
    const turns = messagesQuery.data?.chat;
    return Array.isArray(turns) ? turns.filter((t) => t && typeof t.text === 'string') : [];
  }, [messagesQuery.data]);
  const lines = useMemo(() => {
    const structured = messagesQuery.data?.transcript_lines;
    if (Array.isArray(structured) && structured.length > 0) {
      return structured.map((line, i) => ({
        id: i,
        speaker: line?.speaker || null,
        body: line?.text ?? '',
      }));
    }
    return parseTranscript(messagesQuery.data?.transcript);
  }, [messagesQuery.data]);
  const speakers = useMemo(() => [...new Set(lines.map((l) => l.speaker).filter(Boolean))], [lines]);
  const lineCount = detail?.message_count ?? 0;
  const emptySession = !messagesQuery.isLoading && lineCount === 0;

  useEffect(() => {
    if (savedChat.length > 0) {
      setChat((log) => (log.length === 0 ? savedChat.map((t) => ({ role: t.role, text: t.text })) : log));
    }
  }, [savedChat]);

  async function ask(text) {
    const clean = String(text || '').trim();
    if (!clean || streaming || emptySession) return;
    setStreaming(true);
    setAskError('');
    setThinkingText('');
    setChat((log) => [...log, { role: 'user', text: clean }]);
    setQuestion('');

    let aiIndex = -1;
    setChat((log) => {
      aiIndex = log.length;
      return [...log, { role: 'ai', text: '' }];
    });

    try {
      const { access } = getTokens();
      const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/chat/stream`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...(access ? { Authorization: `Bearer ${access}` } : {}) },
        body: JSON.stringify({ question: clean }),
      });
      if (!response.ok || !response.body) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed with status ${response.status}`);
      }

      for await (const event of readSseEvents(response)) {
        if (event.kind === 'thinking' && event.text) {
          const piece = event.text;
          setThinkingText((prev) => (prev + piece).slice(-500));
        } else if (event.kind === 'token' && event.text) {
          const piece = event.text;
          setChat((log) => log.map((turn, i) => (i === aiIndex ? { ...turn, text: turn.text + piece } : turn)));
        } else if (event.kind === 'error') {
          throw new Error(event.text || 'AI could not answer right now');
        }
      }
    } catch (error) {
      setAskError(error?.message || 'AI could not answer right now');
      setChat((log) => log.filter((_, i) => i !== aiIndex));
    } finally {
      setStreaming(false);
      setThinkingText('');
      if (typeof chatEndRef.current?.scrollIntoView === 'function') {
        chatEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  }

  if (detailQuery.isLoading || messagesQuery.isLoading) {
    return (
      <div className="portal-app portal-app--page"><main className="portal-main pf-center--wide"><div className="portal-skeleton"><span /><span /><span /></div></main></div>
    );
  }

  if (detailQuery.isError || !session) {
    return (
      <div className="portal-app portal-app--page">
        <main className="portal-main pf-center--wide">
          <div className="er-alert er-alert--err">Session not found or you have no access.</div>
          <Link className="er-btn" style={{ textDecoration: 'none', marginTop: 12 }} to="/session"><HiArrowLeft size={14} /> Sessions</Link>
        </main>
      </div>
    );
  }

  const roomName = room?.name || `Room ${session.room_id}`;
  const topics = Array.isArray(room?.topics) ? room.topics : [];

  return (
    <div className="portal-app portal-app--page">
      <main className="portal-main pf-center--wide">
        <div className="portal-pagehead">
          <div>
            <div className="pf-crumb"><Link to="/session">Sessions</Link> / #{session.id}</div>
          </div>
        </div>

        <section className="portal-panel pf-sesscard">
          <div className="pf-sesscard__top">
            <span className="portal-room__tile pf-room__tile--lg">{roomName.trim().charAt(0).toUpperCase()}</span>
            <div className="pf-sesscard__title">
              <h1>{roomName}</h1>
              {topics.length > 0 && (
                <div className="portal-topics">{topics.slice(0, 5).map((t) => <span key={t} className="portal-topic">{t}</span>)}</div>
              )}
            </div>
          </div>
          <div className="portal-grid2 pf-sesscard__facts">
            <div className="portal-block">
              <div className="portal-block__label"><HiClock size={12} /> Duration</div>
              <div className="portal-block__value">{formatDuration(session.duration_seconds)}</div>
            </div>
            <div className="portal-block">
              <div className="portal-block__label"><HiChatBubbleLeftRight size={12} /> Lines said</div>
              <div className="portal-block__value">{lineCount}</div>
            </div>
            <div className="portal-block">
              <div className="portal-block__label"><HiUsers size={12} /> Speakers</div>
              <div className="portal-block__value">{speakers.length > 0 ? speakers.join(', ') : '—'}</div>
            </div>
            <div className="portal-block">
              <div className="portal-block__label">When</div>
              <div className="portal-block__value portal-muted">
                {formatShortDateTime(session.joined_at)} - {session.left_at ? formatShortDateTime(session.left_at) : 'now'}
              </div>
            </div>
          </div>
          {room?.description && <p className="portal-muted pf-sesscard__desc">{room.description}</p>}
        </section>

        <div className="portal-stack" style={{ marginTop: 16 }}>
          <section className="portal-panel pf-aichat">
            <div className="portal-panel__head">
              <h2><HiSparkles size={15} /> Ask AI about this session</h2>
              <span className="portal-muted">{lineCount} lines of context</span>
            </div>
            {emptySession ? (
              <div className="portal-empty">No transcript in this session — nothing was said while you were inside, so AI has nothing to read.</div>
            ) : (
              <>
                <div className="pf-chatlog pf-chatlog--roomy pf-chatlog--tall">
                  {chat.length === 0 && (
                    <div className="pf-greet">
                      <span className="portal-badge">AI</span>
                      <p className="pf-greet__title">I’ve read every line of this session.</p>
                      <p className="portal-muted">Pick a starter below, or ask anything in your own words.</p>
                    </div>
                  )}
                  {chat.map((turn, i) => {
                    const isLive = streaming && i === chat.length - 1;
                    const showThinking = turn.role === 'ai' && isLive && !turn.text;
                    return (
                      <div key={i} className={`pf-chatlog__turn is-${turn.role}`}>
                        <span className="portal-badge">{turn.role === 'ai' ? 'AI' : 'YOU'}</span>
                        <span className={`pf-chattext${showThinking ? ' portal-muted' : ''}`}>
                          {showThinking ? (thinkingText || 'Thinking…') : turn.text}
                          {turn.role === 'ai' && isLive && !showThinking && <span className="pf-caret" aria-hidden="true" />}
                        </span>
                      </div>
                    );
                  })}
                  <div ref={chatEndRef} />
                </div>
                {chat.length === 0 && (
                  <div className="pf-chips pf-chips--starters">
                    {QUICK_PROMPTS.map((prompt) => (
                      <button key={prompt} type="button" className="portal-topic pf-chipbtn" disabled={streaming} onClick={() => ask(prompt)}>
                        {prompt}
                      </button>
                    ))}
                  </div>
                )}
                <form onSubmit={(e) => { e.preventDefault(); ask(question); }} className="pf-askrow">
                  <input
                    className="er-input" value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Ask about this session…"
                    aria-label="Ask about this session"
                    disabled={streaming}
                  />
                  <button type="submit" className="er-btn" aria-label="Ask" title="Ask" disabled={streaming || !question.trim()}>
                    {streaming ? '…' : <HiPaperAirplane size={16} />}
                  </button>
                </form>
                {askError && <div className="er-alert er-alert--err">{askError}</div>}
              </>
            )}
          </section>

          <section className="portal-panel">
            <div className="portal-panel__head">
              <h2>What was said</h2>
              <span className="portal-muted">{lines.length} lines</span>
            </div>
            {lines.length === 0 ? (
              <div className="portal-empty">No messages were said while you were inside.</div>
            ) : (
              <div className="portal-list">
                {lines.map((line) => (
                  <div key={line.id} className="portal-row">
                    <Face name={line.speaker || '?'} size={30} />
                    <span className="portal-row__main">
                      {line.speaker && <span className="portal-row__text">{line.speaker}</span>}
                      <span className={line.speaker ? 'portal-row__sub pf-chattext' : 'portal-row__text pf-chattext'}>{line.body}</span>
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
