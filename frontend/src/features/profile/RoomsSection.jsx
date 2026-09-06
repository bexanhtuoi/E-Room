import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { HiCalendarDays, HiMagnifyingGlass, HiPlusCircle } from 'react-icons/hi2';
import { fetchJson } from '../../lib/api';
import { queryClient } from '../../lib/queryClient';
import { formatDateTime } from '../../lib/formatters';
import { FaceStack } from '../../components/common/Faces';
import { useRoomMembers } from '../rooms/RoomRow';

const STATUS_LABEL = { idle: 'Open', active: 'Live', ended: 'Ended' };
const TABS = [
  { key: 'all', label: 'All' },
  { key: 'hosted', label: 'Hosted' },
  { key: 'joined', label: 'Joined' },
  { key: 'live', label: 'Live' },
];

function LiveFaces({ roomId }) {
  const { data: members } = useRoomMembers(roomId);
  const names = (members || []).map((m) => m.full_name || m.email || `User ${m.id}`);
  if (names.length === 0) return null;
  return <span className="portal-room__faces"><FaceStack names={names} size={26} /></span>;
}

function RoomDetail({ room, myMessages, expanded }) {
  const countQuery = useQuery({
    queryKey: ['messages', 'count', room.id],
    queryFn: () => fetchJson(`/messages/count?room_id=${room.id}`).then((r) => r?.count ?? myMessages.length).catch(() => myMessages.length),
    enabled: expanded,
    staleTime: 30_000,
  });
  const total = typeof countQuery.data === 'number' ? countQuery.data : myMessages.length;
  const topics = Array.isArray(room.topics) ? room.topics : [];

  return (
    <div className="portal-roomdetail">
      <div className="portal-roomdetail__meta">
        <span className={`portal-status is-${room.status}`}>{STATUS_LABEL[room.status] || room.status}</span>
        {room.created_at && <span className="portal-muted"><HiCalendarDays size={13} /> {formatDateTime(room.created_at)}</span>}
        <span className="portal-muted">{countQuery.isLoading ? 'Counting…' : `${total} messages total · ${myMessages.length} yours`}</span>
      </div>
      {topics.length > 0 && (
        <div className="portal-topics">{topics.map((t) => <span key={t} className="portal-topic">{t}</span>)}</div>
      )}
      <div className="portal-roomdetail__label">Your lines here</div>
      {myMessages.length === 0 ? (
        <p className="portal-muted">You have not said anything here yet.</p>
      ) : (
        <ul className="portal-lines">
          {myMessages.slice(0, 8).map((m) => (
            <li key={m.id}>
              <span className="portal-muted">{m.created_at ? formatDateTime(m.created_at) : ''}</span>
              <span>{m.text}</span>
            </li>
          ))}
        </ul>
      )}
      {myMessages.length > 8 && <span className="portal-muted">+ {myMessages.length - 8} more in Activity</span>}
    </div>
  );
}

function RoomCard({ room, mine, myMessages, expanded, onToggle, onDeleted }) {
  const live = room.status === 'active';
  const delMutation = useMutation({
    mutationFn: () => fetchJson(`/rooms/${room.id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rooms', 'list'] });
      onDeleted?.();
    },
  });

  return (
    <div className="portal-room">
      <button type="button" className="portal-room__head" onClick={onToggle} aria-expanded={expanded}>
        <span className={`portal-room__tile${live ? ' is-live' : ''}`}>{(room.name || '?').trim().charAt(0).toUpperCase()}</span>
        <span className="portal-room__main">
          <strong>{room.name}</strong>
          <span className="portal-room__meta">
            <span className={`portal-status is-${room.status}`}>{STATUS_LABEL[room.status] || room.status}</span>
            <span>{myMessages.length} your lines</span>
            {mine && <span className="portal-flag is-solid">HOST</span>}
          </span>
        </span>
        {live && <LiveFaces roomId={room.id} />}
        <span className="portal-room__chev" aria-hidden="true">{expanded ? '▾' : '▸'}</span>
      </button>
      {expanded && (
        <div className="portal-room__body">
          <RoomDetail room={room} myMessages={myMessages} expanded={expanded} />
          <div className="portal-actions">
            <Link className="er-btn portal-mini-btn" style={{ textDecoration: 'none' }} to={`/rooms/${room.id}`}>Open room</Link>
            {mine && (
              <button
                className="er-btn er-btn--ghost portal-mini-btn"
                disabled={delMutation.isPending}
                onClick={() => { if (window.confirm(`Delete room "${room.name}"?`)) delMutation.mutate(); }}
              >
                {delMutation.isPending ? 'Deleting…' : 'Delete'}
              </button>
            )}
          </div>
          {delMutation.isError && <div className="er-alert er-alert--err">Could not delete this room.</div>}
        </div>
      )}
    </div>
  );
}

export function RoomsSection({ hostedRooms, joinedRooms, liveRooms, messagesByRoom, onCreateRoom, onRoomDeleted }) {
  const [tab, setTab] = useState('all');
  const [search, setSearch] = useState('');
  const [expandedId, setExpandedId] = useState(null);

  const all = [...hostedRooms, ...joinedRooms];
  const hostedIds = new Set(hostedRooms.map((r) => r.id));
  const q = search.trim().toLowerCase();

  const filtered = all.filter((r) => {
    if (tab === 'hosted' && !hostedIds.has(r.id)) return false;
    if (tab === 'joined' && hostedIds.has(r.id)) return false;
    if (tab === 'live' && r.status !== 'active') return false;
    if (!q) return true;
    const topics = Array.isArray(r.topics) ? r.topics.join(' ') : '';
    return `${r.name || ''} ${topics}`.toLowerCase().includes(q);
  });

  return (
    <section className="portal-panel">
      <div className="portal-panel__head">
        <h2>Rooms <span className="portal-count">{filtered.length}</span></h2>
        <button className="er-btn er-btn--ghost portal-mini-btn" onClick={onCreateRoom}><HiPlusCircle size={14} /> New room</button>
      </div>
      <div className="portal-toolbar">
        <div className="portal-tabs" role="tablist" aria-label="Room filter">
          {TABS.map((t) => (
            <button key={t.key} type="button" role="tab" aria-selected={tab === t.key} onClick={() => setTab(t.key)} className={`portal-tab${tab === t.key ? ' is-active' : ''}`}>
              {t.label}{t.key === 'live' && liveRooms.length > 0 ? ` (${liveRooms.length})` : ''}
            </button>
          ))}
        </div>
        <div className="portal-search">
          <HiMagnifyingGlass size={14} />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search rooms…" aria-label="Search rooms" />
        </div>
      </div>
      {filtered.length === 0 ? (
        <div className="portal-empty">
          {all.length === 0 ? 'You have not hosted or joined any room yet.' : 'No room matches this filter.'}
        </div>
      ) : (
        <div className="portal-list">
          {filtered.map((room) => (
            <RoomCard
              key={room.id}
              room={room}
              mine={hostedIds.has(room.id)}
              myMessages={messagesByRoom.get(room.id) || []}
              expanded={expandedId === room.id}
              onToggle={() => setExpandedId((cur) => (cur === room.id ? null : room.id))}
              onDeleted={onRoomDeleted}
            />
          ))}
        </div>
      )}
    </section>
  );
}
