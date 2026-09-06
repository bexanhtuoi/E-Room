import { HiCalendarDays, HiChatBubbleLeftRight, HiClock, HiFire } from 'react-icons/hi2';
import { bucketByDay, WeekBars } from './WeekBars';

function dayStreak(messages) {
  const days = new Set();
  for (const m of messages) {
    if (!m?.created_at) continue;
    const d = new Date(m.created_at);
    if (Number.isNaN(d.getTime())) continue;
    days.add(`${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`);
  }
  let streak = 0;
  const cursor = new Date();
  const key = (d) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
  if (!days.has(key(cursor))) cursor.setDate(cursor.getDate() - 1);
  while (days.has(key(cursor))) {
    streak += 1;
    cursor.setDate(cursor.getDate() - 1);
  }
  return streak;
}

function bucketByHour(messages) {
  const hours = Array.from({ length: 24 }, (_, h) => ({ h, count: 0 }));
  for (const m of messages) {
    if (!m?.created_at) continue;
    const d = new Date(m.created_at);
    if (Number.isNaN(d.getTime())) continue;
    hours[d.getHours()].count += 1;
  }
  return hours;
}

export function UsageSection({ messages, messagesTotal, hostedRooms, joinedRooms, pastSessions }) {
  const fortnight = bucketByDay(messages, 14);
  const activeDays = fortnight.filter((b) => b.count > 0).length;
  const streak = dayStreak(messages);
  const hours = bucketByHour(messages);
  const hourMax = Math.max(1, ...hours.map((x) => x.count));
  const peak = hours.reduce((a, b) => (b.count > a.count ? b : a), hours[0]);

  const statusCount = { idle: 0, active: 0, ended: 0 };
  for (const r of [...hostedRooms, ...joinedRooms]) {
    if (statusCount[r.status] != null) statusCount[r.status] += 1;
  }
  const roomsTotal = statusCount.idle + statusCount.active + statusCount.ended;
  const donutBg = roomsTotal === 0
    ? '#f0f0f0'
    : `conic-gradient(#15803d 0 ${(statusCount.active / roomsTotal) * 100}%, #111 ${(statusCount.active / roomsTotal) * 100}% ${((statusCount.active + statusCount.idle) / roomsTotal) * 100}%, #d6d6d6 ${((statusCount.active + statusCount.idle) / roomsTotal) * 100}% 100%)`;

  const topicCount = new Map();
  for (const r of [...hostedRooms, ...joinedRooms]) {
    for (const t of Array.isArray(r.topics) ? r.topics : []) {
      topicCount.set(t, (topicCount.get(t) || 0) + 1);
    }
  }
  const topTopics = [...topicCount.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6);
  const topMax = Math.max(1, ...topTopics.map(([, c]) => c));

  const kpis = [
    { icon: HiChatBubbleLeftRight, value: messagesTotal, label: 'Messages', sub: `${activeDays}/14 active days` },
    { icon: HiFire, value: `${streak}d`, label: 'Day streak', sub: streak > 0 ? 'keep it going' : 'say hi today' },
    { icon: HiClock, value: `${String(peak.h).padStart(2, '0')}:00`, label: 'Peak hour', sub: `${peak.count} messages` },
    { icon: HiCalendarDays, value: pastSessions.length, label: 'Sessions done', sub: `${statusCount.active} live now` },
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

      <section className="portal-panel">
        <div className="portal-panel__head"><h2>Rhythm</h2><span className="portal-muted">Last 14 days · by hour of day</span></div>
        <div className="portal-block">
          <div className="portal-block__label">Messages per day</div>
          <WeekBars data={fortnight} height={120} />
        </div>
        <div className="portal-block">
          <div className="portal-block__label">Active hours (00 – 23)</div>
          <div className="portal-heat" role="img" aria-label="Messages by hour chart">
            {hours.map((x) => {
              const ratio = x.count / hourMax;
              const level = x.count === 0 ? '' : ratio > 0.66 ? 'is-l4' : ratio > 0.4 ? 'is-l3' : ratio > 0.15 ? 'is-l2' : 'is-l1';
              return <span key={x.h} title={`${String(x.h).padStart(2, '0')}:00 — ${x.count}`} className={`portal-heat__cell ${level}`} />;
            })}
          </div>
        </div>
      </section>

      <div className="portal-grid2">
        <section className="portal-panel">
          <div className="portal-panel__head"><h2>Rooms by status</h2></div>
          <div className="portal-block">
            <div className="portal-donutrow">
              <div className="portal-donut" style={{ background: donutBg }}>
                <div className="portal-donut__center"><strong>{roomsTotal}</strong><span>ROOMS</span></div>
              </div>
              <div className="portal-legend">
                <span><span className="portal-legend__dot" style={{ background: '#15803d' }} />Live — {statusCount.active}</span>
                <span><span className="portal-legend__dot" style={{ background: '#111' }} />Open — {statusCount.idle}</span>
                <span><span className="portal-legend__dot" style={{ background: '#d6d6d6' }} />Ended — {statusCount.ended}</span>
              </div>
            </div>
          </div>
        </section>

        <section className="portal-panel">
          <div className="portal-panel__head"><h2>Top topics</h2></div>
          {topTopics.length === 0 ? (
            <div className="portal-empty">Join rooms with topics and your taste profile builds here.</div>
          ) : (
            <div className="portal-meters">
              {topTopics.map(([topic, count]) => (
                <div key={topic} className="portal-meter">
                  <span className="portal-meter__label">{topic}</span>
                  <span className="portal-meter__track"><span className="portal-meter__fill" style={{ width: `${Math.round((count / topMax) * 100)}%` }} /></span>
                  <span className="portal-meter__num">{count}</span>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
