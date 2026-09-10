import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { HiArrowLeft, HiChatBubbleLeftRight, HiClock, HiSparkles } from 'react-icons/hi2';
import { fetchJson } from '../../lib/api';
import { formatDateTime } from '../../lib/formatters';
import { Face } from '../../components/common/Faces';
import '../../styles/ProfilePage.css';

const QUICK_PROMPTS = ['Recap it for Notion', 'What did we decide?', 'Which new words appeared?'];

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

export function SessionDetailPage() {
  const { sessionId } = useParams();
  const [question, setQuestion] = useState('');
  const [chat, setChat] = useState([]);

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
  const lines = useMemo(() => parseTranscript(messagesQuery.data?.transcript), [messagesQuery.data]);
  const speakers = useMemo(() => [...new Set(lines.map((l) => l.speaker).filter(Boolean))], [lines]);
  const joinedDate = session?.joined_at ? new Date(session.joined_at) : null;
  const validDate = joinedDate && !Number.isNaN(joinedDate.getTime()) ? joinedDate : null;

  const askMutation = useMutation({
    mutationFn: (text) => fetchJson(`/sessions/${sessionId}/chat`, {
      method: 'POST',
      body: JSON.stringify({ question: text }),
    }),
    onSuccess: (data, text) => {
      setChat((log) => [...log, { role: 'user', text }, { role: 'ai', text: data.answer }]);
      setQuestion('');
    },
  });

  function ask(text) {
    const clean = String(text || '').trim();
    if (!clean || askMutation.isPending) return;
    askMutation.mutate(clean);
  }

  if (detailQuery.isLoading || messagesQuery.isLoading) {
    return (
      <div className="portal-app portal-app--page"><main className="portal-main"><div className="portal-skeleton"><span /><span /><span /></div></main></div>
    );
  }

  if (detailQuery.isError || !session) {
    return (
      <div className="portal-app portal-app--page">
        <main className="portal-main">
          <div className="er-alert er-alert--err">Session not found or you have no access.</div>
          <Link className="er-btn" style={{ textDecoration: 'none', marginTop: 12 }} to="/session"><HiArrowLeft size={14} /> Sessions</Link>
        </main>
      </div>
    );
  }

  return (
    <div className="portal-app portal-app--page">
      <main className="portal-main pf-wide">
        <div className="portal-pagehead">
          <div>
            <div className="pf-crumb"><Link to="/session">Sessions</Link> / #{session.id}</div>
          </div>
          <div className="portal-pagehead__actions">
            {room && <Link className="er-btn" style={{ textDecoration: 'none' }} to={`/rooms/${room.id}`}>Open room</Link>}
          </div>
        </div>

        <header className="pf-sesshero">
          {validDate && (
            <span className="pf-event__date pf-sesshero__date" title={validDate.toLocaleString()}>
              <strong>{validDate.toLocaleDateString(undefined, { day: '2-digit' })}</strong>
              <span>{validDate.toLocaleDateString(undefined, { month: 'short' })}</span>
              <span className="pf-event__time">{validDate.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}</span>
            </span>
          )}
          <div className="pf-sesshero__id">
            <h1>{room?.name || `Room ${session.room_id}`}</h1>
            {Array.isArray(room?.topics) && room.topics.length > 0 && (
              <div className="portal-topics">{room.topics.slice(0, 5).map((t) => <span key={t} className="portal-topic">{t}</span>)}</div>
            )}
            <div className="pf-resume__facts">
              <span><HiClock size={13} /> {formatDuration(session.duration_seconds)}</span>
              <span><HiChatBubbleLeftRight size={13} /> {detail.message_count} lines</span>
              <span>{speakers.length} speaker{speakers.length === 1 ? '' : 's'}</span>
              <span className="portal-muted">
                {formatShortDateTime(session.joined_at)} - {session.left_at ? formatShortDateTime(session.left_at) : 'now'}
              </span>
            </div>
            {room?.description && <p className="pf-sesshero__desc">{room.description}</p>}
          </div>
        </header>

        <div className="portal-stack" style={{ marginTop: 16 }}>
          <section className="portal-panel pf-aichat">
            <div className="portal-panel__head">
              <h2><HiSparkles size={15} /> Ask AI about this session</h2>
            </div>
            <div className="pf-chatlog pf-chatlog--roomy">
              {chat.length === 0 && (
                <div className="pf-chatlog__turn is-ai">
                  <span className="portal-badge">AI</span>
                  <span className="pf-chattext">I’ve read every line of this session. Ask me to recap it, explain a decision, or pull out new words.</span>
                </div>
              )}
              {chat.map((turn, i) => (
                <div key={i} className={`pf-chatlog__turn is-${turn.role}`}>
                  <span className="portal-badge">{turn.role === 'ai' ? 'AI' : 'YOU'}</span>
                  <span className="pf-chattext">{turn.text}</span>
                </div>
              ))}
              {askMutation.isPending && (
                <div className="pf-chatlog__turn is-ai">
                  <span className="portal-badge">AI</span>
                  <span className="pf-chattext"><span className="pf-typing" aria-label="AI is typing"><span /><span /><span /></span></span>
                </div>
              )}
            </div>
            <div className="pf-chips">
              {QUICK_PROMPTS.map((prompt) => (
                <button key={prompt} type="button" className="portal-topic pf-chipbtn" onClick={() => ask(prompt)}>
                  {prompt}
                </button>
              ))}
            </div>
            <form onSubmit={(e) => { e.preventDefault(); ask(question); }} className="pf-askrow">
              <input
                className="er-input" value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask about this session…"
                aria-label="Ask about this session"
              />
              <button type="submit" className="er-btn" disabled={askMutation.isPending || !question.trim() || detail.message_count === 0}>
                {askMutation.isPending ? '…' : 'Ask'}
              </button>
            </form>
            {askMutation.isError && <div className="er-alert er-alert--err">Could not answer. Try again later.</div>}
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
