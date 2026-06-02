import '../../styles/Badge.css';
const STATUS_VARS = {
  live: { bg: 'var(--color-success-muted)', fg: 'var(--color-success)', dot: 'var(--color-live)' },
  ended: { bg: 'rgba(255,255,255,0.06)', fg: 'var(--color-ended)', dot: 'var(--color-ended)' },
  tag: { bg: 'var(--color-accent-muted)', fg: 'var(--color-accent)', dot: null },
};

export function Badge({ label, variant = 'tag', withDot = false, className = '' }) {
  const v = STATUS_VARS[variant] ?? STATUS_VARS.tag;

  return (
    <>
      <span className={`badge ${className}`} style={{ '--badge-bg': v.bg, '--badge-fg': v.fg }}>
        {withDot && v.dot && (
          <span className="badge-dot" style={{ '--dot-color': v.dot }} />
        )}
        {label}
      </span>
      
    </>
  );
}
