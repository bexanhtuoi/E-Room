import { useState } from 'react';
import { Link } from 'react-router-dom';
import { HiCalendarDays, HiChatBubbleLeftRight, HiClock, HiLockClosed, HiPlus, HiUserGroup } from 'react-icons/hi2';
import { FaceStack } from '../../components/common/Faces';
import { formatDate, formatDateTime } from '../../lib/formatters';
import { useRoomHost, useRoomMembers } from '../rooms/RoomRow';
import { CreateScheduleModal } from './CreateScheduleModal';

const STATUS_LABEL = { idle: 'Open', active: 'Live', ended: 'Ended' };

function countdownTo(iso) {
  if (!iso) return null;
  const ms = new Date(iso).getTime() - Date.now();
  if (Number.isNaN(ms)) return null;
  if (ms <= 0) return { text: 'Starting now', live: true };
  const mins = Math.floor(ms / 60000);
  if (mins < 60) return { text: `in ${mins}m`, live: false };
  const hours = Math.floor(mins / 60);
  if (hours < 48) {
    const rest = mins % 60;
    return { text: rest > 0 ? `in ${hours}h ${rest}m` : `in ${hours}h`, live: false };
  }
  const days = Math.floor(hours / 24);
  return { text: `in ${days}d`, live: false };
}

function Guests({ room }) {
  const { data: members } = useRoomMembers(room.status === 'active' ? room.id : null);
  const { data: host } = useRoomHost(room.host_id);
  const liveNames = (members || []).map((m) => m.full_name || m.email || `User ${m.id}`);
  const invited = Array.isArray(room.allowed_emails) ? room.allowed_emails : [];
  const hostName = host?.full_name || host?.email || null;

  const faces = liveNames.length > 0 ? liveNames : invited.length > 0 ? invited : hostName ? [hostName] : [];
  const caption = liveNames.length > 0
    ? `${liveNames.length} in the room`
    : invited.length > 0
      ? `${invited.length} invited${hostName ? ` · hosted by ${hostName}` : ''}`
      : hostName
        ? `hosted by ${hostName}`
        : null;

  if (faces.length === 0) return null;
  return (
    <span className="pf-event__guests">
      <FaceStack names={faces.slice(0, 5)} size={26} />
      {caption && <span>{caption}</span>}
    </span>
  );
}

function EventCard({ room, myLines }) {
  const live = room.status === 'active';
  const topics = Array.isArray(room.topics) ? room.topics : [];
  const countdown = countdownTo(room.scheduled_at);
  const fullDate = room.scheduled_at
    ? new Date(room.scheduled_at).toLocaleString(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : null;

  return (
    <article className="pf-event">
      {(() => {
        if (!room.scheduled_at || Number.isNaN(new Date(room.scheduled_at).getTime())) return null;
        const date = new Date(room.scheduled_at);
        return (
          <span className="pf-event__date" title={date.toLocaleString()}>
            <strong>{date.toLocaleDateString(undefined, { day: '2-digit' })}</strong>
            <span>{date.toLocaleDateString(undefined, { month: 'short' })}</span>
            <span className="pf-event__time">{date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}</span>
          </span>
        );
      })()}
      <div className="pf-event__body">
        <div className="pf-room__title">
          <strong>{room.name}</strong>
          {live
            ? <span className="portal-badge is-live">LIVE</span>
            : <span className={`portal-status is-${room.status}`}>{STATUS_LABEL[room.status] || room.status}</span>}
          {room.is_private && <span className="portal-flag" title="Invite only"><HiLockClosed size={11} /><span>PRIVATE</span></span>}
        </div>
        {room.description && <p className="pf-room__desc">{room.description}</p>}
        {topics.length > 0 && (
          <div className="portal-topics">{topics.slice(0, 5).map((t) => <span key={t} className="portal-topic">{t}</span>)}</div>
        )}
        <div className="pf-room__meta">
          {countdown && (
            <span className={countdown.live ? 'is-live-text' : ''}>
              <HiClock size={13} /> {countdown.text}{fullDate && !countdown.live ? ` · ${fullDate}` : ''}
            </span>
          )}
          <span><HiChatBubbleLeftRight size={13} /> {myLines} your lines</span>
          {room.created_at && <span><HiCalendarDays size={13} /> opened {formatDate(room.created_at)}</span>}
        </div>
        <Guests room={room} />
      </div>
      <Link className="er-btn portal-mini-btn pf-event__go" style={{ textDecoration: 'none' }} to={`/rooms/${room.id}`}>
        {live ? 'Join' : 'Open'}
      </Link>
    </article>
  );
}

export function ScheduleSection({ rooms, messagesByRoom, userId, userEmail }) {
  const [showSchedule, setShowSchedule] = useState(false);
  const now = Date.now();
  const dayAgo = now - 24 * 3600 * 1000;
  const myEmail = String(userEmail || '').trim().toLowerCase();

  const related = rooms.filter((r) => {
    // Chi phong lien quan toi minh: public, minh host, hoac duoc moi.
    // Ke ca admin cung khong thay private cua nguoi khac o day.
    if (!r.is_private) return true;
    if (String(r.host_id) === String(userId)) return true;
    return myEmail && (r.allowed_emails || []).some((e) => String(e).toLowerCase() === myEmail);
  });

  const scheduled = related
    .filter((r) => {
      if (!r.scheduled_at) return false;
      const time = new Date(r.scheduled_at).getTime();
      if (Number.isNaN(time)) return false;
      // Rooms qua lich qua 24h tu dong xoa o backend — day chi hien lich sap toi + vua qua
      return time > dayAgo;
    })
    .sort((a, b) => new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime());

  const upcoming = scheduled.filter((r) => new Date(r.scheduled_at).getTime() >= now);
  const recent = scheduled.filter((r) => {
    const time = new Date(r.scheduled_at).getTime();
    return time < now && time > dayAgo;
  });

  return (
    <div className="portal-stack">
      <section className="portal-panel">
        <div className="portal-panel__head portal-panel__head--split">
          <h2>Scheduled <span className="portal-count">{scheduled.length}</span></h2>
          <button className="er-btn portal-mini-btn" onClick={() => setShowSchedule(true)}>
            <HiPlus size={14} /> Schedule a room
          </button>
        </div>
        {scheduled.length === 0 ? (
          <div className="portal-empty">
            <HiCalendarDays size={28} />
            <span>Nothing scheduled yet. Book your next speaking session.</span>
          </div>
        ) : (
          <>
            {upcoming.length > 0 && (
              <div className="pf-events">
                {upcoming.map((room) => (
                  <EventCard key={room.id} room={room} myLines={(messagesByRoom.get(room.id) || []).length} />
                ))}
              </div>
            )}
            {recent.length > 0 && (
              <>
                <div className="portal-panel__head" style={{ marginTop: upcoming.length > 0 ? 16 : 0 }}>
                  <h2>Recently started</h2>
                </div>
                <div className="pf-events">
                  {recent.map((room) => (
                    <EventCard key={room.id} room={room} myLines={(messagesByRoom.get(room.id) || []).length} />
                  ))}
                </div>
              </>
            )}
          </>
        )}
        <p className="portal-muted" style={{ margin: '12px 0 0', display: 'flex', alignItems: 'center', gap: 6 }}>
          <HiUserGroup size={13} /> Rooms whose schedule passed over 24h ago are deleted automatically.
        </p>
      </section>

      {showSchedule && <CreateScheduleModal onClose={() => setShowSchedule(false)} />}
    </div>
  );
}
