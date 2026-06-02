export function Card({ title, subtitle, children, action, className = '' }) {
  return (
    <div className={`card shadow-sm border-0 ${className}`} style={{
      background: 'var(--color-bg-elevated)',
      border: '1px solid var(--color-border)',
      borderRadius: 16, overflow: 'hidden',
    }}>
      {(title || subtitle) && (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '16px 20px', borderBottom: '1px solid var(--color-border)',
          flexWrap: 'wrap', gap: 8,
        }}>
          <div>
            {title && <h5 style={{ margin: 0, fontWeight: 700, fontSize: '0.95rem', color: 'var(--color-text-primary)' }}>{title}</h5>}
            {subtitle && <p style={{ margin: '2px 0 0', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>{subtitle}</p>}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div style={{ padding: '16px 20px' }}>
        {children}
      </div>
    </div>
  );
}
