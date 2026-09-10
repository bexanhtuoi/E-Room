import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { HiCalendarDays, HiChatBubbleLeftRight, HiClock, HiMagnifyingGlass } from 'react-icons/hi2';
import { fetchJson } from '../../lib/api';
import { formatDateTime } from '../../lib/formatters';

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
  const totalLines = filtered.reduce((s, item) => s + (item.message_count || 0), 0);

  return (
    <div className="portal-stack">
      {items.length > 0 && (
        <div className="portal-stats">
          <div className="portal-stat">
            <span className="portal-stat__tile"><HiCalendarDays size={20} /></span>
            <span className="portal-stat__body">
              <span className="portal-stat__value">{filtered.length}</span>
              <span className="portal-stat__label">Sessions</span>
              <span className="portal-stat__sub">rooms you entered</span>
            </span>
          </div>
          <div className="portal-stat">
            <span className="portal-stat__tile"><HiChatBubbleLeftRight size={20} /></span>
            <span className="portal-stat__body">
              <span className="portal-stat__value">{totalLines}</span>
              <span className="portal-stat__label">Lines said</span>
              <span className="portal-stat__sub">while present</span>
            </span>
          </div>
        </div>
      )}

      <section className="portal-panel">
        <div className="portal-panel__head">
          <h2>Session history</h2>
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
          <div className="portal-table">
            <div className="portal-table__head">
              <span>Session</span><span>Joined</span><span>Time</span><span>Lines</span><span />
            </div>
            {filtered.map(({ session, room, message_count }) => {
              const topics = Array.isArray(room?.topics) ? room.topics : [];
              return (
                <div key={session.id} className="portal-table__group">
                  <Link
                    to={`/session/${session.id}`}
                    className="portal-table__row"
                    style={{ textDecoration: 'none', color: 'inherit' }}
                  >
                    <span>
                      <span className="portal-table__name">{room?.name || `Room ${session.room_id}`}</span>
                      {topics.length > 0 && <span className="portal-table__tags">{topics.join(' · ')}</span>}
                      {session.summary && <span className="portal-table__quote">Summarized ✓</span>}
                    </span>
                    <span className="portal-muted">{session.joined_at ? formatDateTime(session.joined_at) : '—'}</span>
                    <span className="portal-muted" style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                      <HiClock size={13} /> {formatDuration(session.duration_seconds)}
                    </span>
                    <span className="portal-table__num">{message_count}</span>
                    <span aria-hidden="true">▸</span>
                  </Link>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
