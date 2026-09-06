import { useState } from 'react';
import { Link } from 'react-router-dom';
import { HiMagnifyingGlass } from 'react-icons/hi2';
import { formatDateTime } from '../../lib/formatters';

export function ActivitySection({ messages, rooms, isLoading, isError, onRetry }) {
  const [search, setSearch] = useState('');
  const [roomId, setRoomId] = useState('all');

  const roomName = new Map((rooms || []).map((r) => [r.id, r.name]));
  const roomOptions = [...new Set(messages.map((m) => m.room_id))].map((id) => ({ id, name: roomName.get(id) || `Room ${id}` }));

  const q = search.trim().toLowerCase();
  const filtered = messages.filter((m) => {
    if (roomId !== 'all' && String(m.room_id) !== String(roomId)) return false;
    if (q && !(m.text || '').toLowerCase().includes(q)) return false;
    return true;
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
          {filtered.map((m) => (
            <Link key={m.id} to={`/rooms/${m.room_id}`} className="portal-row">
              <span className={`portal-badge${m.role === 'ai' ? ' is-ai' : ''}`}>{m.role === 'ai' ? 'AI' : 'YOU'}</span>
              <span className="portal-row__main">
                <span className="portal-row__text">{m.text}</span>
                <span className="portal-row__sub">{roomName.get(m.room_id) || `Room ${m.room_id}`}{m.created_at ? ` · ${formatDateTime(m.created_at)}` : ''}</span>
              </span>
              <span className="portal-row__go" aria-hidden="true">→</span>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
