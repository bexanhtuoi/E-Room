const STATUS_VARS = {
  live: { bg: 'var(--color-success-muted)', fg: 'var(--color-success)', dot: 'var(--color-live)' },
  ended: { bg: 'rgba(100,116,139,0.12)', fg: 'var(--color-ended)', dot: 'var(--color-ended)' },
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
      <style>{`
        .badge {
          display: inline-flex; align-items: center; gap: 5px;
          padding: 2px 8px; border-radius: var(--radius-full);
          background: var(--badge-bg); color: var(--badge-fg);
          font-size: 11px; font-weight: 600; line-height: 1.5;
          white-space: nowrap;
        }
        .badge-dot {
          width: 6px; height: 6px; border-radius: 50%;
          background: var(--dot-color);
          box-shadow: 0 0 6px var(--dot-color);
        }
      `}</style>
    </>
  );
}
