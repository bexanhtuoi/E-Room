function dayKey(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export function bucketByDay(messages, days) {
  const buckets = [];
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    buckets.push({ key: dayKey(d), label: `${d.getDate()}/${d.getMonth() + 1}`, count: 0, today: i === 0 });
  }
  const map = new Map(buckets.map((b) => [b.key, b]));
  for (const m of messages) {
    if (!m?.created_at) continue;
    const day = new Date(m.created_at);
    if (Number.isNaN(day.getTime())) continue;
    const b = map.get(dayKey(day));
    if (b) b.count += 1;
  }
  return buckets;
}

export function WeekBars({ data, height = 96 }) {
  const max = Math.max(0, ...data.map((b) => b.count));
  if (max === 0) {
    return <div className="bars bars--empty">No activity in this period yet.</div>;
  }
  return (
    <div className="bars" style={{ height }} role="img" aria-label="Messages per day chart">
      {data.map((b) => (
        <div key={b.key} className="bars__col" title={`${b.label}: ${b.count} messages`}>
          <div className="bars__track">
            <div className={`bars__fill${b.today ? ' is-today' : ''}`} style={{ height: `${Math.round((b.count / max) * 100)}%` }} />
          </div>
          <span className="bars__label">{b.label}</span>
        </div>
      ))}
    </div>
  );
}
