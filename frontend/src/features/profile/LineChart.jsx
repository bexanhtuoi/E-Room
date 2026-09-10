export const RHYTHM_RANGES = [
  { key: '24h', label: '24H' },
  { key: '3d', label: '3D' },
  { key: '7d', label: '7D' },
  { key: '30d', label: '30D' },
];

function startOfDay(date) {
  const day = new Date(date);
  day.setHours(0, 0, 0, 0);
  return day;
}

export function bucketByRange(messages, rangeKey) {
  const now = new Date();
  const buckets = [];

  if (rangeKey === '24h') {
    for (let i = 23; i >= 0; i -= 1) {
      const slot = new Date(now.getTime() - i * 3600 * 1000);
      buckets.push({
        key: slot.toISOString().slice(0, 13),
        label: `${String(slot.getHours()).padStart(2, '0')}:00`,
        start: new Date(slot.setMinutes(0, 0, 0)).getTime(),
        end: new Date(slot.setMinutes(0, 0, 0)).getTime() + 3600 * 1000,
        count: 0,
      });
    }
  } else {
    const days = rangeKey === '30d' ? 30 : rangeKey === '3d' ? 3 : 7;
    for (let i = days - 1; i >= 0; i -= 1) {
      const slot = startOfDay(new Date(now.getTime() - i * 86400 * 1000));
      buckets.push({
        key: slot.toISOString().slice(0, 10),
        label: slot.toLocaleDateString(undefined, { day: 'numeric', month: 'numeric' }),
        start: slot.getTime(),
        end: slot.getTime() + 86400 * 1000,
        count: 0,
      });
    }
  }

  for (const message of messages || []) {
    if (!message?.created_at) continue;
    const time = new Date(message.created_at).getTime();
    if (Number.isNaN(time)) continue;
    const bucket = buckets.find((b) => time >= b.start && time < b.end);
    if (bucket) bucket.count += 1;
  }

  return buckets;
}

export function LineChart({ data, height = 160 }) {
  const width = 640;
  const padLeft = 30;
  const padBottom = 22;
  const padTop = 10;
  const innerWidth = width - padLeft - 8;
  const innerHeight = height - padTop - padBottom;
  const max = Math.max(1, ...data.map((b) => b.count));
  const step = Math.max(1, Math.ceil(max / 3));

  const x = (i) => (data.length === 1 ? padLeft + innerWidth / 2 : padLeft + (i / (data.length - 1)) * innerWidth);
  const y = (count) => padTop + innerHeight - (count / max) * innerHeight;

  const line = data.map((b, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(b.count).toFixed(1)}`).join(' ');
  const area = `${line} L${x(data.length - 1).toFixed(1)},${(padTop + innerHeight).toFixed(1)} L${x(0).toFixed(1)},${(padTop + innerHeight).toFixed(1)} Z`;
  const gridLevels = [0, 1, 2, 3].map((g) => Math.min(max, g * step));
  const labelEvery = Math.max(1, Math.ceil(data.length / 8));

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="pf-linechart" role="img" aria-label="Messages over time chart">
      {gridLevels.map((level) => (
        <g key={level}>
          <line x1={padLeft} x2={width - 8} y1={y(level)} y2={y(level)} className="pf-linechart__grid" />
          <text x={padLeft - 6} y={y(level) + 4} textAnchor="end" className="pf-linechart__tick">{level}</text>
        </g>
      ))}
      <path d={area} className="pf-linechart__area" />
      <path d={line} className="pf-linechart__line" fill="none" />
      {data.map((b, i) => (
        <g key={b.key}>
          {b.count > 0 && <circle cx={x(i)} cy={y(b.count)} r={3.5} className="pf-linechart__dot"><title>{`${b.label}: ${b.count}`}</title></circle>}
          {i % labelEvery === 0 && (
            <text x={x(i)} y={height - 6} textAnchor="middle" className="pf-linechart__tick">{b.label}</text>
          )}
        </g>
      ))}
    </svg>
  );
}
