import { useState } from 'react';
import { Link } from 'react-router-dom';
import { HiCalendarDays, HiChatBubbleLeftRight, HiMagnifyingGlass } from 'react-icons/hi2';
import { formatDateTime } from '../../lib/formatters';

export function SessionsSection({ sessions, messagesByRoom, userId }) {
  const [search, setSearch] = useState('');
  const [expandedId, setExpandedId] = useState(null);

  const q = search.trim().toLowerCase();
  const filtered = sessions.filter((r) => {
    if (!q) return true;
    const topics = Array.isArray(r.topics) ? r.topics.join(' ') : '';
    return `${r.name || ''} ${topics}`.toLowerCase().includes(q);
  });
  const totalLines = filtered.reduce((s, r) => s + (messagesByRoom.get(r.id) || []).length, 0);

  return (
    <div className="portal-stack">
      {sessions.length > 0 && (
        <div className="portal-stats">
          <div className="portal-stat">
            <span className="portal-stat__tile"><HiCalendarDays size={20} /></span>
            <span className="portal-stat__body">
              <span className="portal-stat__value">{filtered.length}</span>
              <span className="portal-stat__label">Past sessions</span>
              <span className="portal-stat__sub">finished rooms</span>
            </span>
          </div>
          <div className="portal-stat">
            <span className="portal-stat__tile"><HiChatBubbleLeftRight size={20} /></span>
            <span className="portal-stat__body">
              <span className="portal-stat__value">{totalLines}</span>
              <span className="portal-stat__label">Lines you said</span>
              <span className="portal-stat__sub">across sessions</span>
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
        {filtered.length === 0 ? (
          <div className="portal-empty">
            {sessions.length === 0
              ? 'Finished rooms will land here as past sessions, with everything you said in each one.'
              : 'No session matches your search.'}
          </div>
        ) : (
          <div className="portal-table">
            <div className="portal-table__head">
              <span>Session</span><span>Date</span><span>Role</span><span>Lines</span><span />
            </div>
            {filtered.map((room) => {
              const mine = messagesByRoom.get(room.id) || [];
              const expanded = expandedId === room.id;
              const isHost = String(room.host_id) === String(userId);
              const topics = Array.isArray(room.topics) ? room.topics : [];
              return (
                <div key={room.id} className="portal-table__group">
                  <button
                    type="button"
                    className="portal-table__row"
                    aria-expanded={expanded}
                    onClick={() => setExpandedId(expanded ? null : room.id)}
                  >
                    <span>
                      <span className="portal-table__name">{room.name}</span>
                      {topics.length > 0 && <span className="portal-table__tags">{topics.join(' · ')}</span>}
                    </span>
                    <span className="portal-muted">{room.created_at ? formatDateTime(room.created_at) : '—'}</span>
                    <span>{isHost ? <span className="portal-flag is-solid">HOST</span> : <span className="portal-flag">GUEST</span>}</span>
                    <span className="portal-table__num">{mine.length}</span>
                    <span aria-hidden="true">{expanded ? '▾' : '▸'}</span>
                  </button>
                  {expanded && (
                    <div className="portal-table__detail">
                      {mine.length === 0 ? (
                        <p className="portal-muted">You listened in this one — nothing said.</p>
                      ) : (
                        <ul className="portal-lines">
                          {mine.map((m) => (
                            <li key={m.id}>
                              <span className="portal-muted">{m.created_at ? formatDateTime(m.created_at) : ''}</span>
                              <span>{m.text}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                      <div className="portal-actions">
                        <Link className="er-btn portal-mini-btn" style={{ textDecoration: 'none' }} to={`/rooms/${room.id}`}>Open room</Link>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
