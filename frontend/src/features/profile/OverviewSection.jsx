import { Link } from 'react-router-dom';
import { HiArrowRight, HiCalendarDays, HiFire, HiSignal } from 'react-icons/hi2';
import { FaceStack } from '../../components/common/Faces';
import { useRoomMembers } from '../rooms/RoomRow';
import { ActivitySection } from './ActivitySection';
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

function greetingFor(hour) {
  if (hour < 5) return 'Up late';
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

function topTopicOf(rooms) {
  const counts = new Map();
  for (const room of rooms) {
    for (const topic of Array.isArray(room.topics) ? room.topics : []) {
      const key = String(topic).trim();
      if (key) counts.set(key, (counts.get(key) || 0) + 1);
    }
  }
  let best = null;
  for (const [topic, count] of counts) {
    if (!best || count > best.count) best = { topic, count };
  }
  return best;
}

export function OverviewSection({
  userName,
  hostedRooms,
  joinedRooms,
  liveRooms,
  messages,
  stats,
  rooms,
  activityLoading,
  activityError,
  activityRetry,
  onGo,
}) {
  const week = bucketByDay(messages, 7);
  const weekTotal = week.reduce((s, b) => s + b.count, 0);
  const myRooms = [...hostedRooms, ...joinedRooms];
  const resume = [...liveRooms, ...joinedRooms, ...hostedRooms].find((r) => r.status === 'active')
    || [...joinedRooms, ...hostedRooms].find((r) => r.status === 'idle');

  const delta = stats ? stats.week_delta : 0;
  const streak = stats?.streak_days ?? 0;
  const top = topTopicOf(myRooms);
  const upNext = (top && myRooms.find((r) => r.status === 'idle' && (r.topics || []).includes(top.topic)))
    || [...myRooms].reverse().find((r) => r.status === 'idle')
    || null;

  const today = new Date();
  const dateLine = today.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });

  return (
    <div className="portal-stack">
      <section className="pf-today">
        <div className="pf-today__date">{dateLine}</div>
        <div className="pf-today__title">{greetingFor(today.getHours())}{userName ? `, ${userName}` : ''}.</div>
        <div className="pf-today__sub">
          {resume
            ? <>Pick up <strong>“{resume.name}”</strong> {resume.status === 'active' ? '— it’s live right now.' : '— it’s waiting for voices.'}</>
            : 'No open room right now — find one on the Rooms page and say hi.'}
        </div>
        {resume && (
          <Link className="er-btn pf-today__cta" style={{ textDecoration: 'none' }} to={`/rooms/${resume.id}`}>
            {resume.status === 'active' ? 'Join live' : 'Open room'} <HiArrowRight size={14} />
          </Link>
        )}
      </section>

      {liveRooms.length > 0 && (
        <section className="portal-panel">
          <div className="portal-panel__head">
            <h2>Happening now</h2>
            <span className="portal-badge is-live"><HiSignal size={12} /> {liveRooms.length} ON AIR</span>
          </div>
          <div className="portal-list">
            {liveRooms.slice(0, 3).map((r) => <LiveRoomLine key={r.id} room={r} />)}
          </div>
        </section>
      )}

      <section className="portal-panel">
        <div className="portal-panel__head">
          <h2>Your week in rooms</h2>
          <span className="portal-muted">{weekTotal} lines said</span>
        </div>
        <div className="portal-block">
          <WeekBars data={week} height={140} />
        </div>
        <div className="pf-weekfacts">
          <span>
            <HiFire size={14} />
            {streak > 0 ? `${streak}-day speaking streak — keep it burning` : 'No streak yet — say one line today to start it'}
          </span>
          <span>
            <HiCalendarDays size={14} />
            {stats?.most_active_day
              ? `Peak day ${stats.most_active_day} with ${stats.most_active_day_count} lines`
              : 'Your peak day will show up here'}
          </span>
          <span className={delta > 0 ? 'is-up' : delta < 0 ? 'is-down' : ''}>
            {delta > 0 ? `▲ ${delta} lines vs last week` : delta < 0 ? `▼ ${Math.abs(delta)} lines vs last week` : 'Same pace as last week'}
          </span>
        </div>
        <div className="portal-block">
          <button type="button" className="portal-linkbtn" onClick={() => onGo?.('assessment')}>Review what you said <HiArrowRight size={13} /></button>
        </div>
      </section>

      {upNext && (
        <section className="portal-panel">
          <div className="portal-panel__head">
            <h2>Up next{top ? ` — more ${top.topic}` : ''}</h2>
          </div>
          <div className="portal-block">
            <div className="portal-resume">
              <div>
                <strong>{upNext.name}</strong>
                <span className="portal-muted">
                  {top ? `Your top topic is ${top.topic} — this open room fits right in.` : 'An open room from your list.'}
                </span>
              </div>
              <Link className="er-btn portal-mini-btn" style={{ textDecoration: 'none' }} to={`/rooms/${upNext.id}`}>Open</Link>
            </div>
          </div>
        </section>
      )}

      <ActivitySection messages={messages} rooms={rooms} isLoading={activityLoading} isError={activityError} onRetry={activityRetry} />
    </div>
  );
}
