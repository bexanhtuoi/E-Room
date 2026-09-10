import { useState } from 'react';
import { Link } from 'react-router-dom';
import { HiCalendarDays, HiClock, HiLockClosed, HiPlus, HiSignal } from 'react-icons/hi2';
import { Face, FaceStack } from '../../components/common/Faces';
import { useRoomHost, useRoomMembers } from '../rooms/RoomRow';
import { CreateScheduleModal } from './CreateScheduleModal';

function countdownTo(iso) {
  if (!iso) return null;
  const ms = new Date(iso).getTime() - Date.now();
  if (Number.isNaN(ms)) return null;
  if (ms <= 0) return { text: 'Time to start', live: true };
  const mins = Math.floor(ms / 60000);
  if (mins < 60) return { text: `in ${mins}m`, live: false };
  const hours = Math.floor(mins / 60);
  if (hours < 48) {
    const rest = mins % 60;
    return { text: rest > 0 ? `in ${hours}h ${rest}m` : `in ${hours}h`, live: false };
  }
  return { text: `in ${Math.floor(hours / 24)}d`, live: false };
}

function dateBlock(iso) {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  const day = date.toLocaleDateString(undefined, { day: '2-digit' });
  const month = date.toLocaleDateString(undefined, { month: 'short' });
  const time = date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  return (
    <span className="pf-event__date" title={date.toLocaleString()}>
      <strong>{day}</strong>
      <span>{month}</span>
      <span className="pf-event__time">{time}</span>
    </span>
  );
}

function Guests({ room }) {
  const { data: members } = useRoomMembers(room.status === 'active' ? room.id : null);
  const { data: host } = useRoomHost(room.host_id);
  const liveNames = (members || []).map((m) => m.full_name || m.email || `User ${m.id}`);
  const invited = Array.isArray(room.allowed_emails) ? room.allowed_emails : [];

  if (liveNames.length > 0) {
    return (
      <span className="pf-event__guests">
        <FaceStack names={liveNames} size={26} />
        <span>{liveNames.length} in the room</span>
      </span>
    );
  }
  if (invited.length > 0) {
    return (
      <span className="pf-event__guests">
        <FaceStack names={invited} size={26} />
        <span>{invited.length} invited</span>
      </span>
    );
  }
  if (host) {
    return (
      <span className="pf-event__guests">
        <Face name={host.full_name || host.email} size={26} />
        <span>hosted by {host.full_name || host.email}</span>
      </span>
    );
  }
  return null;
}

function EventCard({ room }) {
  const live = room.status === 'active';
  const topics = Array.isArray(room.topics) ? room.topics : [];
  const countdown = countdownTo(room.scheduled_at);
  const fullDate = room.scheduled_at
    ? new Date(room.scheduled_at).toLocaleString(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : null;

  return (
    <article className="pf-event">
      {dateBlock(room.scheduled_at)}
      <div className="pf-event__body">
        <div className="pf-room__title">
          <strong>{room.name}</strong>
          {live
            ? <span className="portal-badge is-live">LIVE</span>
            : <span className={`portal-status is-${room.status}`}>{room.status === 'idle' ? 'Open' : room.status}</span>}
          {room.is_private && <span className="portal-flag" title="Invite only"><HiLockClosed size={11} /><span>PRIVATE</span></span>}
        </div>
        {topics.length > 0 && (
          <div className="portal-topics">{topics.slice(0, 3).map((t) => <span key={t} className="portal-topic">{t}</span>)}</div>
        )}
        <div className="pf-room__meta">
          {countdown && (
            <span className={countdown.live ? 'is-live-text' : ''}>
              <HiClock size={13} /> {countdown.text}{fullDate && !countdown.live ? ` · ${fullDate}` : ''}
            </span>
          )}
          {!countdown && fullDate && <span><HiCalendarDays size={13} /> {fullDate}</span>}
        </div>
        <Guests room={room} />
      </div>
      <Link className="er-btn portal-mini-btn pf-event__go" style={{ textDecoration: 'none' }} to={`/rooms/${room.id}`}>
        {live ? 'Join' : 'Open'}
      </Link>
    </article>
  );
}

export function ScheduleSection({ rooms, hostedRooms }) {
  const [showSchedule, setShowSchedule] = useState(false);
  const now = Date.now();

  const upcoming = rooms
    .filter((r) => r.status !== 'ended' && r.scheduled_at && new Date(r.scheduled_at).getTime() > now - 3600 * 1000)
    .sort((a, b) => new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime());
  const live = rooms.filter((r) => r.status === 'active' && !upcoming.some((u) => u.id === r.id));
  const open = rooms
    .filter((r) => r.status === 'idle' && !r.scheduled_at)
    .sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));

  return (
    <div className="portal-stack">
      <section className="portal-panel">
        <div className="portal-panel__head portal-panel__head--split">
          <h2>Upcoming <span className="portal-count">{upcoming.length}</span></h2>
          <button className="er-btn portal-mini-btn" onClick={() => setShowSchedule(true)}>
            <HiPlus size={14} /> Schedule a room
          </button>
        </div>
        {upcoming.length === 0 ? (
          <div className="portal-empty">
            <HiCalendarDays size={28} />
            <span>Nothing scheduled yet. Book your next speaking session.</span>
          </div>
        ) : (
          <div className="pf-events">
            {upcoming.map((room) => <EventCard key={room.id} room={room} />)}
          </div>
        )}
      </section>

      {live.length > 0 && (
        <section className="portal-panel">
          <div className="portal-panel__head">
            <h2>Live now</h2>
            <span className="portal-badge is-live"><HiSignal size={12} /> {live.length} ON AIR</span>
          </div>
          <div className="pf-events">
            {live.map((room) => <EventCard key={room.id} room={room} />)}
          </div>
        </section>
      )}

      <section className="portal-panel">
        <div className="portal-panel__head"><h2>Open rooms <span className="portal-count">{open.length}</span></h2></div>
        {open.length === 0 ? (
          <div className="portal-empty">
            <HiClock size={28} />
            <span>Nothing open — schedule one above and people will come.</span>
          </div>
        ) : (
          <div className="pf-events">
            {open.slice(0, 12).map((room) => <EventCard key={room.id} room={room} />)}
          </div>
        )}
      </section>

      {showSchedule && <CreateScheduleModal onClose={() => setShowSchedule(false)} />}
    </div>
  );
}
