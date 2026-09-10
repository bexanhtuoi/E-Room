import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { HiArrowRightOnRectangle, HiCalendarDays, HiChatBubbleLeftRight, HiCog6Tooth, HiLockClosed, HiMagnifyingGlass, HiTrash } from 'react-icons/hi2';
import { fetchJson } from '../../lib/api';
import { queryClient } from '../../lib/queryClient';
import { formatDate, formatDateTime } from '../../lib/formatters';
import { FaceStack } from '../../components/common/Faces';
import { useRoomMembers } from '../rooms/RoomRow';

const STATUS_LABEL = { idle: 'Open', active: 'Live', ended: 'Ended' };

function LiveFaces({ roomId }) {
  const { data: members } = useRoomMembers(roomId);
  const names = (members || []).map((m) => m.full_name || m.email || `User ${m.id}`);
  if (names.length === 0) return null;
  return <span className="portal-room__faces"><FaceStack names={names} size={26} /></span>;
}

function RoomCard({ room, myMessages, onDeleted }) {
  const live = room.status === 'active';
  const topics = Array.isArray(room.topics) ? room.topics : [];
  const delMutation = useMutation({
    mutationFn: () => fetchJson(`/rooms/${room.id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rooms', 'list'] });
      onDeleted?.();
    },
  });

  const countQuery = useQuery({
    queryKey: ['messages', 'count', room.id],
    queryFn: () => fetchJson(`/messages/count?room_id=${room.id}`).then((r) => r?.count ?? myMessages.length).catch(() => myMessages.length),
    staleTime: 30_000,
  });
  const total = typeof countQuery.data === 'number' ? countQuery.data : myMessages.length;

  return (
    <article className="pf-room">
      <div className="pf-room__main">
        <span className={`portal-room__tile pf-room__tile${live ? ' is-live' : ''}`}>{(room.name || '?').trim().charAt(0).toUpperCase()}</span>
        <div className="pf-room__body">
          <div className="pf-room__title">
            <strong>{room.name}</strong>
            <span className={`portal-status is-${room.status}`}>{STATUS_LABEL[room.status] || room.status}</span>
            {room.is_private && <span className="portal-flag" title="Only you and allowed emails can see this"><HiLockClosed size={11} /><span>PRIVATE</span></span>}
            {live && <LiveFaces roomId={room.id} />}
          </div>
          {room.description && <p className="pf-room__desc">{room.description}</p>}
          {topics.length > 0 && (
            <div className="portal-topics">{topics.map((t) => <span key={t} className="portal-topic">{t}</span>)}</div>
          )}
          <div className="pf-room__meta">
            <span><HiChatBubbleLeftRight size={13} /> {countQuery.isLoading ? 'Counting…' : `${total} messages · ${myMessages.length} yours`}</span>
            {room.created_at && <span><HiCalendarDays size={13} /> opened {formatDate(room.created_at)}</span>}
          </div>
        </div>
      </div>
      <div className="pf-room__actions">
        <Link to={`/rooms/${room.id}/config`} className="pf-action" title="Room settings" aria-label={`Configure ${room.name}`}>
          <HiCog6Tooth size={16} /><span>Config</span>
        </Link>
        <button
          type="button" className="pf-action is-danger" title="Delete room" aria-label={`Delete ${room.name}`}
          disabled={delMutation.isPending}
          onClick={() => { if (window.confirm(`Delete room "${room.name}" and everything in it?`)) delMutation.mutate(); }}
        >
          <HiTrash size={16} /><span>{delMutation.isPending ? 'Deleting…' : 'Delete'}</span>
        </button>
        <Link to={`/rooms/${room.id}`} className="pf-action is-enter" title="Enter room" aria-label={`Enter ${room.name}`}>
          <HiArrowRightOnRectangle size={16} /><span>Enter</span>
        </Link>
      </div>
      {delMutation.isError && <div className="er-alert er-alert--err">Could not delete this room.</div>}
    </article>
  );
}

export function RoomsSection({ hostedRooms, liveRooms, messagesByRoom, onRoomDeleted }) {
  const [tab, setTab] = useState('all');
  const [search, setSearch] = useState('');

  const q = search.trim().toLowerCase();
  const filtered = hostedRooms
    .filter((r) => {
      if (tab === 'live' && r.status !== 'active') return false;
      if (tab === 'open' && r.status !== 'idle') return false;
      if (tab === 'ended' && r.status !== 'ended') return false;
      if (!q) return true;
      const topics = Array.isArray(r.topics) ? r.topics.join(' ') : '';
      return `${r.name || ''} ${r.description || ''} ${topics}`.toLowerCase().includes(q);
    })
    .sort((a, b) => (b.created_at || '').localeCompare(a.created_at || '') || b.id - a.id);

  return (
    <section className="portal-panel">
      <div className="portal-panel__head portal-panel__head--split">
        <h2>Rooms <span className="portal-count">{filtered.length}</span></h2>
        <div className="portal-search">
          <HiMagnifyingGlass size={14} />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search rooms…" aria-label="Search rooms" />
        </div>
      </div>
      <div className="portal-toolbar">
        <div className="portal-tabs" role="tablist" aria-label="Room filter">
          {[{ key: 'all', label: 'All' }, { key: 'live', label: 'Live' }, { key: 'open', label: 'Open' }, { key: 'ended', label: 'Ended' }].map((t) => (
            <button key={t.key} type="button" role="tab" aria-selected={tab === t.key} onClick={() => setTab(t.key)} className={`portal-tab${tab === t.key ? ' is-active' : ''}`}>
              {t.label}{t.key === 'live' && liveRooms.length > 0 ? ` (${liveRooms.length})` : ''}
            </button>
          ))}
        </div>
      </div>
      {filtered.length === 0 ? (
        <div className="portal-empty">
          {hostedRooms.length === 0 ? 'You have not created any room yet.' : 'No room matches this filter.'}
        </div>
      ) : (
        <div className="pf-rooms">
          {filtered.map((room) => (
            <RoomCard
              key={room.id}
              room={room}
              myMessages={messagesByRoom.get(room.id) || []}
              onDeleted={onRoomDeleted}
            />
          ))}
        </div>
      )}
    </section>
  );
}
