export const MIN_SEATS = 2;
export const MAX_SEATS = 6;

export function SeatSlider({ value, onChange, id = 'room-seats' }) {
  const ticks = Array.from({ length: MAX_SEATS - MIN_SEATS + 1 }, (_, i) => MIN_SEATS + i);
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 2 }}>
        <label className="er-label" htmlFor={id} style={{ margin: 0 }}>Seats</label>
        <span style={{ fontSize: 26, fontWeight: 800, lineHeight: 1 }} aria-live="polite">{value}</span>
      </div>
      <input
        id={id}
        type="range"
        min={MIN_SEATS}
        max={MAX_SEATS}
        step={1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-valuetext={`${value} seats`}
        style={{ width: '100%', accentColor: '#111', cursor: 'pointer' }}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, fontWeight: 700, color: '#999' }} aria-hidden="true">
        {ticks.map((n) => <span key={n}>{n}</span>)}
      </div>
    </div>
  );
}
