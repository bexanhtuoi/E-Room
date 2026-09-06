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

export function UsageSection({ messages, hostedRooms, joinedRooms }) {
  const fortnight = bucketByDay(messages, 14);
  const activeDays = fortnight.filter((b) => b.count > 0).length;
  const streak = dayStreak(messages);
  const statusCount = { idle: 0, active: 0, ended: 0 };
  for (const r of [...hostedRooms, ...joinedRooms]) {
    if (statusCount[r.status] != null) statusCount[r.status] += 1;
  }

  const topicCount = new Map();
  for (const r of [...hostedRooms, ...joinedRooms]) {
    for (const t of Array.isArray(r.topics) ? r.topics : []) {
      topicCount.set(t, (topicCount.get(t) || 0) + 1);
    }
  }
  const topTopics = [...topicCount.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);
  const topMax = Math.max(1, ...topTopics.map(([, c]) => c));

  const kpis = [
    { value: messages.length, label: 'messages spoken', sub: `${activeDays}/14 active days` },
    { value: `${streak}d`, label: 'day streak', sub: streak > 0 ? 'keep it going' : 'say hi today' },
    { value: hostedRooms.length + joinedRooms.length, label: 'rooms touched', sub: `${hostedRooms.length} hosted` },
    { value: statusCount.ended, label: 'sessions finished', sub: `${statusCount.active} live now` },
  ];

  return (
    <div className="portal-stack">
      <section className="portal-panel">
        <div className="portal-panel__head"><h2>Usage</h2><span className="portal-muted">Last 14 days</span></div>
        <div className="portal-stats is-4">
          {kpis.map((k) => (
            <div key={k.label} className="portal-stat">
              <div className="portal-stat__value">{k.value}</div>
              <div className="portal-stat__label">{k.label}</div>
              <div className="portal-stat__sub">{k.sub}</div>
            </div>
          ))}
        </div>
        <div className="portal-block">
          <div className="portal-block__label">Messages per day</div>
          <WeekBars data={fortnight} height={120} />
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
  );
}
