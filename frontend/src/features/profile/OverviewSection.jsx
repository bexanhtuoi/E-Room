import { Link } from 'react-router-dom';
import { HiArrowRight, HiCalendarDays, HiChatBubbleLeftRight, HiDocumentText, HiUserGroup } from 'react-icons/hi2';
import { formatDateTime } from '../../lib/formatters';
import { FaceStack } from '../../components/common/Faces';
import { useRoomMembers } from '../rooms/RoomRow';
import { bucketByDay, WeekBars } from './WeekBars';

function LiveRoomLine({ room }) {
  const { data: members } = useRoomMembers(room.id);
  const names = (members || []).map((m) => m.full_name || m.email || `User ${m.id}`);
  return (
    <div className="portal-row">
      <span className="portal-badge is-live">LIVE</span>
      <span className="portal-row__main">
        <span className="portal-row__text">{room.name}</span>
        <span className="portal-row__sub">{names.length > 0 ? `${names.length} speaking now` : 'On air — be the first voice'}</span>
      </span>
      {names.length > 0 && <span className="portal-room__faces"><FaceStack names={names} size={26} /></span>}
      <Link className="er-btn portal-mini-btn" style={{ textDecoration: 'none' }} to={`/rooms/${room.id}`}>Join</Link>
    </div>
  );
}

export function OverviewSection({ hostedRooms, joinedRooms, liveRooms, messages, messagesTotal, documentsCount, onGo }) {
  const week = bucketByDay(messages, 7);
  const weekTotal = week.reduce((s, b) => s + b.count, 0);
  const recent = messages.slice(0, 5);

  const kpis = [
    { icon: HiUserGroup, value: hostedRooms.length, label: 'Rooms hosted', sub: `${joinedRooms.length} joined` },
    { icon: HiChatBubbleLeftRight, value: messagesTotal, label: 'Messages', sub: `${weekTotal} this week` },
    { icon: HiCalendarDays, value: liveRooms.length, label: 'Live now', sub: 'in your rooms' },
    { icon: HiDocumentText, value: documentsCount, label: 'Documents', sub: 'attached files' },
  ];

  return (
    <div className="portal-stack">
      <div className="portal-stats">
        {kpis.map((k) => (
          <div key={k.label} className="portal-stat">
            <span className="portal-stat__tile"><k.icon size={20} /></span>
            <span className="portal-stat__body">
              <span className="portal-stat__value">{k.value}</span>
              <span className="portal-stat__label">{k.label}</span>
              <span className="portal-stat__sub">{k.sub}</span>
            </span>
          </div>
        ))}
      </div>

      {liveRooms.length > 0 && (
        <section className="portal-panel">
          <div className="portal-panel__head"><h2>Live now</h2><span className="portal-badge is-live">{liveRooms.length} ON AIR</span></div>
          <div className="portal-list">
            {liveRooms.slice(0, 3).map((r) => <LiveRoomLine key={r.id} room={r} />)}
          </div>
        </section>
      )}

      <div className="portal-grid2">
        <section className="portal-panel">
          <div className="portal-panel__head"><h2>This week</h2><span className="portal-muted">{weekTotal} messages</span></div>
          <div className="portal-block">
            <WeekBars data={week} />
          </div>
          <div className="portal-block">
            <button type="button" className="portal-linkbtn" onClick={() => onGo?.('usage')}>Full usage report <HiArrowRight size={13} /></button>
          </div>
        </section>

        <section className="portal-panel">
          <div className="portal-panel__head">
            <h2>Latest messages</h2>
            <button type="button" className="portal-linkbtn" onClick={() => onGo?.('activity')}>View all <HiArrowRight size={13} /></button>
          </div>
          {recent.length === 0 ? (
            <div className="portal-empty">Nothing yet — your voice lands here.</div>
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
    </div>
  );
}
