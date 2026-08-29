import '../../styles/Logo.css';

export function Logo({ size = 32, showText = true }) {
  return (
    <span className="d-inline-flex align-items-center gap-2 logo-wrapper">
      <svg width={size} height={size} viewBox="0 0 32 32" fill="none" className="logo-icon">
        <g stroke="var(--color-accent)" strokeWidth="1.3" fill="none" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="7" cy="12" r="3" />
          <path d="M3.5 15.5 C3.5 22, 10.5 22, 10.5 15.5" />
          <circle cx="16" cy="11" r="3.2" />
          <path d="M12 14.5 C12 22, 20 22, 20 14.5" />
          <circle cx="25" cy="12" r="3" />
          <path d="M21.5 15.5 C21.5 22, 28.5 22, 28.5 15.5" />
        </g>
      </svg>
      {showText && (
        <span className="logo-text">
          E-Room
        </span>
      )}
    </span>
  );
}
