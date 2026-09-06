import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { HiCalendarDays, HiPlusCircle } from 'react-icons/hi2';
import { fetchJson } from '../../lib/api';
import { queryClient } from '../../lib/queryClient';
import { formatDateTime } from '../../lib/formatters';

const STATUS_LABEL = { idle: 'Open', active: 'Live', ended: 'Ended' };

function RoomDetail({ room, myMessages }) {
  const topics = Array.isArray(room.topics) ? room.topics : [];
  return (
    <div className="portal-roomdetail">
      <div className="portal-roomdetail__meta">
        <span className={`portal-status is-${room.status}`}>● {STATUS_LABEL[room.status] || room.status}</span>
        {room.created_at && <span className="portal-muted"><HiCalendarDays size={13} /> {formatDateTime(room.created_at)}</span>}
      </div>
      {topics.length > 0 && (
        <div className="portal-topics">{topics.map((t) => <span key={t} className="portal-topic">{t}</span>)}</div>
      )}
      <div className="portal-roomdetail__label">Your messages in this room ({myMessages.length})</div>
      {myMessages.length === 0 ? (
        <p className="portal-muted">You have not said anything here yet.</p>
      ) : (
        <ul className="portal-lines">
          {myMessages.map((m) => (
            <li key={m.id}>
              <span className="portal-muted">{m.created_at ? formatDateTime(m.created_at) : ''}</span>
              <span>{m.text}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function RoomRow({ room, mine, myMessages, expandable, expanded, onToggle, onDeleted }) {
  const delMutation = useMutation({
    mutationFn: () => fetchJson(`/rooms/${room.id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rooms', 'list'] });
      onDeleted?.();
    },
  });

  return (
    <div className="portal-room">
      <button type="button" className="portal-room__head" onClick={onToggle} aria-expanded={expanded} disabled={!expandable}>
        <span className="portal-room__main">
          <strong>{room.name}</strong>
          <span className="portal-muted">{myMessages.length} of your messages</span>
        </span>
        <span className={`portal-status is-${room.status}`}>● {STATUS_LABEL[room.status] || room.status}</span>
        {expandable && <span aria-hidden="true">{expanded ? '▾' : '▸'}</span>}
      </button>
      {expanded && (
        <div className="portal-room__body">
          <RoomDetail room={room} myMessages={myMessages} />
          <div className="portal-actions">
            <Link className="er-btn" style={{ textDecoration: 'none' }} to={`/rooms/${room.id}`}>Open room</Link>
            {mine && (
              <button
                className="er-btn er-btn--ghost"
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

export function RoomsSection({ hostedRooms, joinedRooms, messagesByRoom, onCreateRoom, onRoomDeleted }) {
  const [expandedId, setExpandedId] = useState(null);

  function toggle(id) {
    setExpandedId((cur) => (cur === id ? null : id));
  }

  return (
    <div className="portal-stack">
      <section className="portal-panel">
        <div className="portal-panel__head">
          <h2>My rooms ({hostedRooms.length})</h2>
          <button className="er-btn er-btn--ghost" onClick={onCreateRoom}><HiPlusCircle size={15} /> New room</button>
        </div>
        {hostedRooms.length === 0 ? (
          <div className="portal-empty">You have not hosted a room yet. Open one in 30 seconds.</div>
        ) : (
          <div className="portal-list">
            {hostedRooms.map((room) => (
              <RoomRow
                key={room.id}
                room={room}
                mine
                myMessages={messagesByRoom.get(room.id) || []}
                expandable
                expanded={expandedId === room.id}
                onToggle={() => toggle(room.id)}
                onDeleted={onRoomDeleted}
              />
            ))}
          </div>
        )}
      </section>

      <section className="portal-panel">
        <div className="portal-panel__head"><h2>Rooms joined ({joinedRooms.length})</h2></div>
        {joinedRooms.length === 0 ? (
          <div className="portal-empty">Rooms you speak in will show up here.</div>
        ) : (
          <div className="portal-list">
            {joinedRooms.map((room) => (
              <RoomRow
                key={room.id}
                room={room}
                myMessages={messagesByRoom.get(room.id) || []}
                expandable
                expanded={expandedId === room.id}
                onToggle={() => toggle(room.id)}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
