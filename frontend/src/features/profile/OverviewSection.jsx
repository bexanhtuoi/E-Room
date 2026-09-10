import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { HiArrowRight, HiCalendarDays, HiFire, HiSignal, HiSparkles } from 'react-icons/hi2';
import { FaceStack } from '../../components/common/Faces';
import { useRoomMembers } from '../rooms/RoomRow';
import { ActivitySection } from './ActivitySection';
import { LineChart, RHYTHM_RANGES, bucketByRange } from './LineChart';

const LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];

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

function peakHourOf(messages) {
  const hours = new Array(24).fill(0);
  for (const message of messages) {
    if (!message?.created_at) continue;
    const date = new Date(message.created_at);
    if (Number.isNaN(date.getTime())) continue;
    hours[date.getHours()] += 1;
  }
  let best = 0;
  for (let h = 1; h < 24; h += 1) {
    if (hours[h] > hours[best]) best = h;
  }
  return { hour: best, count: hours[best] };
}

export function OverviewSection({
  userName,
  englishLevel,
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
  const [rhythmRange, setRhythmRange] = useState('7d');
  const rhythm = useMemo(() => bucketByRange(messages, rhythmRange), [messages, rhythmRange]);
  const rhythmTotal = rhythm.reduce((s, b) => s + b.count, 0);
  const levelIndex = Math.max(0, LEVELS.indexOf(englishLevel || ''));
  const peak = peakHourOf(messages);

  const today = new Date();
  const dateLine = today.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
  const streak = stats?.streak_days ?? 0;
  const delta = stats ? stats.week_delta : 0;

  return (
    <div className="portal-stack">
      <section className="pf-today">
        <div className="pf-today__date">{dateLine}</div>
        <div className="pf-today__title">{greetingFor(today.getHours())}{userName ? `, ${userName}` : ''}.</div>
        <div className="pf-today__facts">
          {englishLevel && <span className="portal-flag is-solid">Level {englishLevel}</span>}
          <span className="pf-today__streak">
            <HiFire size={15} />
            {streak > 0 ? `${streak}-day streak` : 'Start your streak today'}
          </span>
        </div>
      </section>

      <section className="portal-panel">
        <div className="portal-panel__head"><h2>Level journey</h2><span className="portal-muted">CEFR</span></div>
        <div className="portal-block">
          <div className="pf-leveltrack" role="img" aria-label={`English level ${englishLevel || 'not set'}`}>
            {LEVELS.map((level, i) => (
              <span key={level} className={`pf-leveltrack__stop${i < levelIndex ? ' is-past' : ''}${i === levelIndex && englishLevel ? ' is-here' : ''}`}>
                {level}
              </span>
            ))}
          </div>
          <p className="portal-muted" style={{ margin: '10px 0 0' }}>
            {englishLevel
              ? `You are at ${englishLevel} — ${LEVELS.length - 1 - levelIndex} step${LEVELS.length - 1 - levelIndex === 1 ? '' : 's'} to C2. Review your lines to climb faster.`
              : 'Set your English level in Profile and watch the journey begin.'}
          </p>
          <div className="portal-block" style={{ marginTop: 8 }}>
            <button type="button" className="portal-linkbtn" onClick={() => onGo?.('assessment')}>Review what you said <HiArrowRight size={13} /></button>
          </div>
        </div>
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
          <h2>Your rhythm</h2>
          <div className="portal-tabs" role="tablist" aria-label="Rhythm range">
            {RHYTHM_RANGES.map((range) => (
              <button
                key={range.key}
                type="button"
                role="tab"
                aria-selected={rhythmRange === range.key}
                onClick={() => setRhythmRange(range.key)}
                className={`portal-tab${rhythmRange === range.key ? ' is-active' : ''}`}
              >
                {range.label}
              </button>
            ))}
          </div>
        </div>
        <div className="portal-panel__sub">
          <span className="portal-muted">{rhythmTotal} lines in the last {rhythmRange === '24h' ? '24 hours' : rhythmRange === '3d' ? '3 days' : rhythmRange === '7d' ? '7 days' : '30 days'}</span>
        </div>
        <div className="portal-block">
          <LineChart data={rhythm} height={170} />
        </div>
        <div className="pf-weekfacts">
          <span>
            <HiSparkles size={14} />
            {peak.count > 0
              ? `Your prime time is around ${String(peak.hour).padStart(2, '0')}:00 — book rooms then`
              : 'Speak once and I’ll learn your prime time'}
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
      </section>

      <ActivitySection messages={messages} rooms={rooms} isLoading={activityLoading} isError={activityError} onRetry={activityRetry} />
    </div>
  );
}
