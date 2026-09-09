import { Link } from 'react-router-dom';
import { HiClock, HiPlusCircle, HiSignal } from 'react-icons/hi2';
import { formatDateTime } from '../../lib/formatters';

const STATUS_LABEL = { idle: 'Open', active: 'Live', ended: 'Ended' };

function RoomLine({ room, mine }) {
  const live = room.status === 'active';
  const topics = Array.isArray(room.topics) ? room.topics : [];
  return (
    <div className="portal-row">
      <span className={`portal-badge${live ? ' is-live' : ''}`}>{live ? 'LIVE' : 'OPEN'}</span>
      <span className="portal-row__main">
        <span className="portal-row__text">{room.name}</span>
        <span className="portal-row__sub">
          {topics.length > 0 ? `${topics.join(' · ')} — ` : ''}
          {room.created_at ? `opened ${formatDateTime(room.created_at)}` : STATUS_LABEL[room.status]}
          {mine ? ' · you host' : ''}
        </span>
      </span>
      <Link className="er-btn portal-mini-btn" style={{ textDecoration: 'none' }} to={`/rooms/${room.id}`}>
        {live ? 'Join' : 'Open'}
      </Link>
    </div>
  );
}

export function ScheduleSection({ rooms, hostedRooms, onCreateRoom }) {
  const hostedIds = new Set(hostedRooms.map((r) => r.id));
  const live = rooms.filter((r) => r.status === 'active');
  const open = rooms
    .filter((r) => r.status === 'idle')
    .sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));

  return (
    <div className="portal-stack">
      {live.length > 0 && (
        <section className="portal-panel">
          <div className="portal-panel__head">
            <h2>Happening now</h2>
            <span className="portal-badge is-live"><HiSignal size={12} /> {live.length} ON AIR</span>
          </div>
          <div className="portal-list">
            {live.map((r) => <RoomLine key={r.id} room={r} mine={hostedIds.has(r.id)} />)}
          </div>
        </section>
      )}

      <section className="portal-panel">
        <div className="portal-panel__head">
          <h2>Open rooms <span className="portal-count">{open.length}</span></h2>
          <button className="er-btn er-btn--ghost portal-mini-btn" onClick={onCreateRoom}>
            <HiPlusCircle size={14} /> New room
          </button>
        </div>
        {open.length === 0 ? (
          <div className="portal-empty">
            <HiClock size={28} />
            <span>No open room right now. Create one and learners will join you.</span>
          </div>
        ) : (
          <div className="portal-list">
            {open.map((r) => <RoomLine key={r.id} room={r} mine={hostedIds.has(r.id)} />)}
          </div>
        )}
      </section>
    </div>
  );
}
