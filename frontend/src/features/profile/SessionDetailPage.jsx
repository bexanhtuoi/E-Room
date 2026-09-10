import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { HiArrowLeft, HiChatBubbleLeftRight, HiSparkles } from 'react-icons/hi2';
import { fetchJson } from '../../lib/api';
import { formatDateTime } from '../../lib/formatters';
import '../../styles/ProfilePage.css';

function Transcript({ text }) {
  const lines = String(text || '').split('\n').filter((line) => line.trim());
  if (lines.length === 0) {
    return <div className="portal-empty">No messages were said while you were inside.</div>;
  }
  return (
    <ul className="portal-lines">
      {lines.map((line, i) => {
        const cut = line.indexOf(':');
        const speaker = cut > 0 ? line.slice(0, cut) : null;
        const body = cut > 0 ? line.slice(cut + 1).trim() : line;
        return (
          <li key={i}>
            {speaker && <strong style={{ marginRight: 8 }}>{speaker}</strong>}
            <span>{body}</span>
          </li>
        );
      })}
    </ul>
  );
}

export function SessionDetailPage() {
  const { sessionId } = useParams();
  const [question, setQuestion] = useState('');
  const [chat, setChat] = useState([]);
  const [recap, setRecap] = useState(null);

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

  const summarizeMutation = useMutation({
    mutationFn: () => fetchJson(`/sessions/${sessionId}/summarize`, { method: 'POST' }),
    onSuccess: (data) => {
      setRecap(data.summary);
    },
  });

  const askMutation = useMutation({
    mutationFn: (text) => fetchJson(`/sessions/${sessionId}/ask`, {
      method: 'POST',
      body: JSON.stringify({ question: text }),
    }),
    onSuccess: (data, text) => {
      setChat((log) => [...log, { role: 'user', text }, { role: 'ai', text: data.answer }]);
      setQuestion('');
    },
  });

  function handleAsk(event) {
    event?.preventDefault();
    const text = question.trim();
    if (!text || askMutation.isPending) return;
    askMutation.mutate(text);
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
      <main className="portal-main pf-center">
        <div className="portal-pagehead">
          <div>
            <div className="pf-crumb"><Link to="/session">Sessions</Link> / #{session.id}</div>
            <h1>{room?.name || `Room ${session.room_id}`}</h1>
            <p>
              Joined {session.joined_at ? formatDateTime(session.joined_at) : '—'}
              {session.left_at ? ` · left ${formatDateTime(session.left_at)}` : ' · still inside'}
              {' · '}{detail.message_count} lines
            </p>
          </div>
          <div className="portal-pagehead__actions">
            {room && <Link className="er-btn" style={{ textDecoration: 'none' }} to={`/rooms/${room.id}`}>Open room</Link>}
          </div>
        </div>

        <div className="portal-stack">
          <section className="portal-panel">
            <div className="portal-panel__head">
              <h2><HiSparkles size={15} /> AI recap</h2>
              <button
                type="button" className="er-btn portal-mini-btn"
                disabled={summarizeMutation.isPending || detail.message_count === 0}
                onClick={() => summarizeMutation.mutate()}
              >
                {summarizeMutation.isPending ? 'Summarizing…' : 'Summarize this session'}
              </button>
            </div>
            {summarizeMutation.isError && (
              <div className="er-alert er-alert--err">Could not summarize. Try again later.</div>
            )}
            {recap ? (
              <div className="portal-block pf-markdown">{recap}</div>
            ) : (
              <div className="portal-empty">
                <HiSparkles size={28} />
                <span>One click turns this session into a recap — key points, new words, action items. Ready for Notion.</span>
              </div>
            )}
          </section>

          <section className="portal-panel">
            <div className="portal-panel__head">
              <h2>Ask about this session</h2>
            </div>
            {chat.length > 0 && (
              <div className="portal-list" style={{ marginBottom: 12 }}>
                {chat.map((turn, i) => (
                  <div key={i} className={`portal-row${turn.role === 'ai' ? ' is-unread' : ''}`}>
                    <span className="portal-badge">{turn.role === 'ai' ? 'AI' : 'YOU'}</span>
                    <span className="portal-row__main"><span className="portal-row__text pf-chattext">{turn.text}</span></span>
                  </div>
                ))}
              </div>
            )}
            <form onSubmit={handleAsk} style={{ display: 'flex', gap: 8 }}>
              <input
                className="er-input" value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="e.g. What did we decide about the trip?"
                aria-label="Ask about this session"
              />
              <button type="submit" className="er-btn" disabled={askMutation.isPending || !question.trim() || detail.message_count === 0}>
                {askMutation.isPending ? 'Asking…' : 'Ask'}
              </button>
            </form>
            {askMutation.isError && <div className="er-alert er-alert--err" style={{ marginTop: 8 }}>Could not answer. Try again later.</div>}
          </section>

          <section className="portal-panel">
            <div className="portal-panel__head">
              <h2><HiChatBubbleLeftRight size={15} /> Transcript</h2>
              <span className="portal-muted">{detail.message_count} lines while you were inside</span>
            </div>
            <Transcript text={messagesQuery.data?.transcript} />
          </section>
        </div>
      </main>
    </div>
  );
}
