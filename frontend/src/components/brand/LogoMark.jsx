export function LogoMark({ size = 30 }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
      <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
        <rect x="1" y="1" width="30" height="30" fill="#111111" />
        <rect x="7" y="9" width="11" height="4" fill="#ffffff" />
        <rect x="7" y="14" width="18" height="4" fill="#ffffff" />
        <rect x="7" y="19" width="8" height="4" fill="#ffffff" />
        <rect x="21" y="21" width="4" height="4" fill="#ffffff" />
      </svg>
      <span style={{ fontWeight: 800, fontSize: 20, letterSpacing: '-0.02em', color: '#111' }}>E-Room</span>
    </span>
  );
}
