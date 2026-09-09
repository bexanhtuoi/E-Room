import { Link } from 'react-router-dom';
import { HiArrowRight, HiCalendarDays, HiChatBubbleLeftRight, HiFire, HiUserGroup } from 'react-icons/hi2';
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
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

function deltaText(delta) {
  if (delta > 0) return { text: `+${delta} vs last week`, tone: 'is-up' };
  if (delta < 0) return { text: `${delta} vs last week`, tone: 'is-down' };
  return { text: 'Same as last week', tone: '' };
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
  onCreateRoom,
}) {
  const week = bucketByDay(messages, 7);
  const weekTotal = week.reduce((s, b) => s + b.count, 0);
  const resume = [...liveRooms, ...joinedRooms, ...hostedRooms].find((r) => r.status === 'active')
    || [...joinedRooms, ...hostedRooms].find((r) => r.status === 'idle');

  const delta = deltaText(stats?.week_delta ?? 0);
  const streakSub = stats && stats.streak_days > 0
    ? 'days speaking in a row'
    : 'speak today to start one';

  const kpis = [
    { icon: HiUserGroup, value: hostedRooms.length, label: 'Rooms hosted', sub: `${joinedRooms.length} joined`, tone: '' },
    { icon: HiChatBubbleLeftRight, value: stats?.messages_total ?? messages.length, label: 'Messages', sub: delta.text, tone: delta.tone },
    { icon: HiFire, value: stats?.streak_days ?? 0, label: 'Day streak', sub: streakSub, tone: '' },
  ];

  const heroAction = liveRooms.length > 0
    ? { text: `“${liveRooms[0].name}” is live now — jump in for a few minutes?`, cta: 'Join live', to: `/rooms/${liveRooms[0].id}` }
    : resume
      ? { text: `“${resume.name}” is waiting — pick up where you left off.`, cta: 'Open room', to: `/rooms/${resume.id}` }
      : { text: 'No open room right now — start one and learners will join you.', cta: 'New room', to: null };

  return (
    <div className="portal-stack">
      <section className="pf-hero">
        <div className="pf-hero__body">
          <div className="pf-hero__hello">{greetingFor(new Date().getHours())}{userName ? `, ${userName}` : ''}</div>
          <div className="pf-hero__title">What will you talk about today?</div>
          <div className="pf-hero__sub">{heroAction.text}</div>
        </div>
        {heroAction.to ? (
          <Link className="er-btn" style={{ textDecoration: 'none' }} to={heroAction.to}>{heroAction.cta}</Link>
        ) : (
          <button type="button" className="er-btn" onClick={onCreateRoom}>{heroAction.cta}</button>
        )}
      </section>

      <div className="pf-kpis">
        {kpis.map((k) => (
          <div key={k.label} className="pf-kpi">
            <span className="pf-kpi__tile"><k.icon size={20} /></span>
            <span className="pf-kpi__body">
              <span className="pf-kpi__value">{k.value}</span>
              <span className="pf-kpi__label">{k.label}</span>
              <span className={`pf-kpi__sub ${k.tone}`}>{k.sub}</span>
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
            <button type="button" className="portal-linkbtn" onClick={() => onGo?.('assessment')}>Check my English level <HiArrowRight size={13} /></button>
          </div>
        </section>

        <section className="portal-panel">
          <div className="portal-panel__head"><h2>Best day</h2><HiCalendarDays size={16} className="portal-muted" /></div>
          <div className="portal-block">
            {stats?.most_active_day ? (
              <div className="portal-resume">
                <div>
                  <strong>{stats.most_active_day}</strong>
                  <span className="portal-muted">{stats.most_active_day_count} messages — your peak in the last 7 days</span>
                </div>
              </div>
            ) : (
              <div className="portal-empty">Speak in a room and your best day will show up here.</div>
            )}
          </div>
        </section>
      </div>

      <ActivitySection messages={messages} rooms={rooms} isLoading={activityLoading} isError={activityError} onRetry={activityRetry} />
    </div>
  );
}
