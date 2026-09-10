import { useState } from 'react';
import { Link } from 'react-router-dom';
import { HiMagnifyingGlass } from 'react-icons/hi2';
import { formatDateTime } from '../../lib/formatters';

export function ActivitySection({ messages, rooms, sessions = [], isLoading, isError, onRetry }) {
  const [search, setSearch] = useState('');
  const [roomId, setRoomId] = useState('all');

  const roomName = new Map((rooms || []).map((r) => [r.id, r.name]));
  const roomOptions = [...new Set([...messages.map((m) => m.room_id), ...sessions.map((s) => s?.room?.id).filter(Boolean)])]
    .map((id) => ({ id, name: roomName.get(id) || `Room ${id}` }));

  const q = search.trim().toLowerCase();
  const messageRows = messages.map((m) => ({ kind: 'message', id: `m-${m.id}`, room_id: m.room_id, time: m.created_at, message: m }));
  const joinRows = sessions
    .filter((s) => s?.session?.joined_at)
    .map((s) => ({ kind: 'join', id: `j-${s.session.id}`, room_id: s.session.room_id, time: s.session.joined_at, session: s.session, room: s.room }));
  const rows = [...messageRows, ...joinRows].sort((a, b) => String(b.time || '').localeCompare(String(a.time || '')));

  const filtered = rows.filter((row) => {
    if (roomId !== 'all' && String(row.room_id) !== String(roomId)) return false;
    if (!q) return true;
    if (row.kind === 'message') return (row.message.text || '').toLowerCase().includes(q);
    return (row.room?.name || '').toLowerCase().includes(q);
  });

  return (
    <section className="portal-panel">
      <div className="portal-panel__head">
        <h2>Activity <span className="portal-count">{filtered.length}</span></h2>
        <div className="portal-toolbar" style={{ justifyContent: 'flex-end' }}>
          <div className="portal-search">
            <HiMagnifyingGlass size={14} />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search what you said…" aria-label="Search messages" />
          </div>
          <div className="portal-search">
            <select value={roomId} onChange={(e) => setRoomId(e.target.value)} aria-label="Filter by room">
              <option value="all">All rooms</option>
              {roomOptions.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </div>
        </div>
      </div>
      {isLoading && <div className="portal-skeleton"><span /><span /><span /></div>}
      {isError && (
        <div className="er-alert er-alert--err">
          Could not load activity. <button type="button" onClick={onRetry} className="portal-linkbtn">Try again</button>
        </div>
      )}
      {!isLoading && !isError && filtered.length === 0 && (
        <div className="portal-empty">
          {messages.length === 0 ? 'No messages yet. Join a room and everything you say will appear here.' : 'Nothing matches this filter.'}
        </div>
      )}
      {!isLoading && !isError && filtered.length > 0 && (
        <div className="portal-list">
          {filtered.map((row) => row.kind === 'join' ? (
            <Link key={row.id} to={`/session/${row.session.id}`} className="portal-row">
              <span className="portal-badge">JOINED</span>
              <span className="portal-row__main">
                <span className="portal-row__text">Joined {row.room?.name || `Room ${row.room_id}`}</span>
                <span className="portal-row__sub">{row.time ? formatDateTime(row.time) : ''}</span>
              </span>
              <span className="portal-row__go" aria-hidden="true">→</span>
            </Link>
          ) : (
            <Link key={row.id} to={`/rooms/${row.message.room_id}`} className="portal-row">
              <span className={`portal-badge${row.message.role === 'ai' ? ' is-ai' : ''}`}>{row.message.role === 'ai' ? 'AI' : 'CHAT'}</span>
              <span className="portal-row__main">
                <span className="portal-row__text">{row.message.text}</span>
                <span className="portal-row__sub">{roomName.get(row.message.room_id) || `Room ${row.message.room_id}`}{row.message.created_at ? ` · ${formatDateTime(row.message.created_at)}` : ''}</span>
              </span>
              <span className="portal-row__go" aria-hidden="true">→</span>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
