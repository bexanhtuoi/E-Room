import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { HiArrowRight, HiFire, HiSignal } from 'react-icons/hi2';
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

export function OverviewSection({
  userName,
  englishLevel,
  hostedRooms,
  joinedRooms,
  liveRooms,
  messages,
  stats,
  rooms,
  sessions = [],
  activityLoading,
  activityError,
  activityRetry,
  onGo,
}) {
  const [rhythmRange, setRhythmRange] = useState('7d');
  const rhythm = useMemo(() => bucketByRange(messages, rhythmRange), [messages, rhythmRange]);
  const rhythmTotal = rhythm.reduce((s, b) => s + b.count, 0);

  const consistencyDays = useMemo(() => {
    const active = new Set();
    for (const message of messages || []) {
      if (!message?.created_at) continue;
      const date = new Date(message.created_at);
      if (Number.isNaN(date.getTime())) continue;
      active.add(date.toISOString().slice(0, 10));
    }
    const days = [];
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    for (let i = 13; i >= 0; i -= 1) {
      const day = new Date(today.getTime() - i * 86400 * 1000);
      const key = day.toISOString().slice(0, 10);
      days.push({ key, active: active.has(key), label: day.toLocaleDateString(undefined, { day: 'numeric', month: 'numeric' }) });
    }
    return days;
  }, [messages]);
  const consistencyCount = consistencyDays.filter((d) => d.active).length;

  const weekBars = useMemo(() => {
    const counts = new Array(7).fill(0);
    const labels = [];
    for (let i = 6; i >= 0; i -= 1) {
      const day = new Date();
      day.setHours(0, 0, 0, 0);
      labels.unshift(new Date(day.getTime() - i * 86400 * 1000));
    }
    for (const message of messages || []) {
      if (!message?.created_at) continue;
      const time = new Date(message.created_at).getTime();
      if (Number.isNaN(time)) continue;
      const idx = labels.findIndex((day) => time >= day.getTime() && time < day.getTime() + 86400 * 1000);
      if (idx >= 0) counts[idx] += 1;
    }
    const names = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
    return labels.map((day, i) => ({
      key: day.toISOString().slice(0, 10),
      label: names[(day.getDay() + 6) % 7],
      title: day.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' }),
      count: counts[i],
    }));
  }, [messages]);
  const weekMax = Math.max(1, ...weekBars.map((b) => b.count));

  const topTopics = useMemo(() => {
    const counts = new Map();
    for (const room of [...hostedRooms, ...joinedRooms]) {
      for (const topic of Array.isArray(room.topics) ? room.topics : []) {
        const key = String(topic).trim();
        if (key) counts.set(key, (counts.get(key) || 0) + 1);
      }
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);
  }, [hostedRooms, joinedRooms]);
  const levelIndex = Math.max(0, LEVELS.indexOf(englishLevel || ''));

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

      <section className="portal-panel pf-momentum">
        <div className="portal-panel__head">
          <h2>Momentum</h2>
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
        <div className="pf-momentum__grid">
          <div className="pf-momentum__main">
            <div className="portal-block__label">{rhythmTotal} lines</div>
            <LineChart data={rhythm} height={120} />
          </div>
          <div className="pf-momentum__side">
            <div className="portal-block__label">This week</div>
            <div className="pf-weekbars" role="img" aria-label="Lines spoken each day this week">
              {weekBars.map((bar) => (
                <span key={bar.key} className="pf-weekbar" title={`${bar.title} — ${bar.count} lines`}>
                  <span className="pf-weekbar__track">
                    <span className="pf-weekbar__fill" style={{ height: `${Math.round((bar.count / weekMax) * 100)}%` }} />
                  </span>
                  <span className="pf-weekbar__label">{bar.label}</span>
                </span>
              ))}
            </div>
          </div>
        </div>
        <div className="pf-momentum__facts">
          <span className="portal-muted"><HiFire size={12} /> {streak > 0 ? `${streak}-day streak` : 'No streak yet'}</span>
          <span className="portal-muted">{consistencyCount}/14 days</span>
          {topTopics.length > 0 && <span className="portal-topic">{topTopics[0][0]}</span>}
          <span className={`portal-muted${delta > 0 ? ' is-up' : ''}${delta < 0 ? ' is-down' : ''}`}>
            {delta > 0 ? `▲${delta} vs last week` : delta < 0 ? `▼${Math.abs(delta)} vs last week` : 'Same as last week'}
          </span>
        </div>
      </section>

      <ActivitySection messages={messages} rooms={rooms} sessions={sessions} isLoading={activityLoading} isError={activityError} onRetry={activityRetry} />
    </div>
  );
}
