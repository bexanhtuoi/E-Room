import { Link } from 'react-router-dom';
import { HiPlusCircle } from 'react-icons/hi2';
import { formatDateTime } from '../../lib/formatters';

export function OverviewSection({ user, hostedRooms, joinedRooms, messages, documents, tierLabel, onCreateRoom }) {
  const stats = [
    { value: hostedRooms.length, label: 'rooms hosted' },
    { value: joinedRooms.length, label: 'rooms joined' },
    { value: messages.length, label: 'messages sent' },
    { value: documents.length, label: 'documents' },
  ];
  const recent = messages.slice(0, 6);

  return (
    <div className="portal-stack">
      <section className="portal-panel">
        <div className="portal-panel__head"><h2>Dashboard</h2></div>
        <div className="portal-stats">
          {stats.map((s) => (
            <div key={s.label} className="portal-stat">
              <div className="portal-stat__value">{s.value}</div>
              <div className="portal-stat__label">{s.label}</div>
            </div>
          ))}
        </div>
        <div className="portal-actions">
          <button className="er-btn" onClick={onCreateRoom}><HiPlusCircle size={16} /> New room</button>
          <Link className="er-btn er-btn--ghost" style={{ textDecoration: 'none' }} to="/rooms">Find a room</Link>
          <span className="portal-plan">Plan: <strong>{tierLabel}</strong></span>
        </div>
      </section>

      <section className="portal-panel">
        <div className="portal-panel__head">
          <h2>Recent activity</h2>
          <span className="portal-muted">{user?.english_level ? `Level ${user.english_level}` : 'Level not set'} · joined {user?.created_at ? formatDateTime(user.created_at) : '—'}</span>
        </div>
        {recent.length === 0 ? (
          <div className="portal-empty">No messages yet. Join a room and everything you say will appear here.</div>
        ) : (
          <div className="portal-list">
            {recent.map((m) => (
              <Link key={m.id} to={`/rooms/${m.room_id}`} className="portal-row">
                <span className={`portal-badge${m.role === 'ai' ? ' is-ai' : ''}`}>{m.role === 'ai' ? 'AI' : 'YOU'}</span>
                <span className="portal-row__main">
                  <span className="portal-row__text">{m.text}</span>
                  <span className="portal-row__sub">{m.created_at ? formatDateTime(m.created_at) : ''}</span>
                </span>
                <span className="portal-row__go" aria-hidden="true">→</span>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
