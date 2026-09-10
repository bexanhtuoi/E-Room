import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { HiChatBubbleLeftRight, HiClock, HiMagnifyingGlass } from 'react-icons/hi2';
import { fetchJson } from '../../lib/api';
function formatShortDateTime(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';
  const day = date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
  const time = date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  return `${day}, ${time}`;
}

function formatDuration(seconds) {
  if (seconds == null) return 'ongoing';
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  if (mins < 60) return `${mins}m`;
  return `${Math.floor(mins / 60)}h ${mins % 60}m`;
}

export function SessionsSection() {
  const [search, setSearch] = useState('');
  const sessionsQuery = useQuery({
    queryKey: ['sessions', 'mine'],
    queryFn: () => fetchJson('/sessions/mine').then((r) => r?.sessions ?? []),
  });
  const items = Array.isArray(sessionsQuery.data) ? sessionsQuery.data : [];

  const q = search.trim().toLowerCase();
  const filtered = items.filter(({ room }) => {
    if (!q) return true;
    const topics = Array.isArray(room?.topics) ? room.topics.join(' ') : '';
    return `${room?.name || ''} ${topics}`.toLowerCase().includes(q);
  });

  return (
    <div className="portal-stack">
      <section className="portal-panel">
        <div className="portal-panel__head">
          <h2>Sessions <span className="portal-count">{filtered.length}</span></h2>
          <div className="portal-search">
            <HiMagnifyingGlass size={14} />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search name or topic…" aria-label="Search sessions" />
          </div>
        </div>
        {sessionsQuery.isLoading && <div className="portal-skeleton"><span /><span /><span /></div>}
        {sessionsQuery.isError && (
          <div className="er-alert er-alert--err">
            Could not load sessions. <button type="button" onClick={() => sessionsQuery.refetch()} className="portal-linkbtn">Try again</button>
          </div>
        )}
        {!sessionsQuery.isLoading && !sessionsQuery.isError && filtered.length === 0 && (
          <div className="portal-empty">
            {items.length === 0
              ? 'Enter any room and it lands here as a session, with everything said while you were inside.'
              : 'No session matches your search.'}
          </div>
        )}
        {!sessionsQuery.isLoading && !sessionsQuery.isError && filtered.length > 0 && (
          <div className="pf-events">
            {filtered.map(({ session, room, message_count }) => {
              const topics = Array.isArray(room?.topics) ? room.topics : [];
              const joined = session.joined_at ? new Date(session.joined_at) : null;
              const validDate = joined && !Number.isNaN(joined.getTime()) ? joined : null;
              return (
                <article key={session.id} className="pf-event">
                  {validDate && (
                    <span className="pf-event__date" title={validDate.toLocaleString()}>
                      <strong>{validDate.toLocaleDateString(undefined, { day: '2-digit' })}</strong>
                      <span>{validDate.toLocaleDateString(undefined, { month: 'short' })}</span>
                      <span className="pf-event__time">{validDate.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}</span>
                    </span>
                  )}
                  <div className="pf-event__body">
                    <div className="pf-room__title">
                      <strong>{room?.name || `Room ${session.room_id}`}</strong>
                      {!session.left_at && <span className="portal-badge is-live">ONGOING</span>}
                    </div>
                    {topics.length > 0 && (
                      <div className="portal-topics">{topics.slice(0, 5).map((t) => <span key={t} className="portal-topic">{t}</span>)}</div>
                    )}
                    <div className="pf-room__meta">
                      <span><HiClock size={13} /> {formatDuration(session.duration_seconds)}</span>
                      <span><HiChatBubbleLeftRight size={13} /> {message_count} lines</span>
                      <span>
                        {session.joined_at ? formatShortDateTime(session.joined_at) : '—'}
                        {' - '}
                        {session.left_at ? formatShortDateTime(session.left_at) : 'now'}
                      </span>
                    </div>
                  </div>
                  <Link className="er-btn portal-mini-btn pf-event__go" style={{ textDecoration: 'none' }} to={`/session/${session.id}`}>
                    Open
                  </Link>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
