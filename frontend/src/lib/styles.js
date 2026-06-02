

export const pill = {
  padding: '6px 14px',
  borderRadius: 99,
  cursor: 'pointer',
  fontWeight: 600,
  fontSize: '0.78rem',
  fontFamily: 'inherit',
  transition: 'all 0.12s',
};

export const card = {
  padding: '16px',
  borderRadius: 14,
  background: 'var(--color-bg-elevated)',
  border: '1px solid var(--color-border)',
};

export const cardSm = {
  padding: '12px 14px',
  borderRadius: 14,
  background: 'var(--color-bg-elevated)',
  border: '1px solid var(--color-border)',
};

export const chip = {
  padding: '2px 8px',
  borderRadius: 99,
  fontSize: '0.65rem',
  fontWeight: 600,
};

export const gradientBg = {
  background: 'var(--color-accent-gradient)',
};

export const flexCenter = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
};

export const flexBetween = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
};

export const glassNavbar = {
  background: 'var(--color-bg-glass)',
  backdropFilter: 'blur(16px)',
  WebkitBackdropFilter: 'blur(16px)',
  borderBottom: '1px solid var(--color-border)',
};

export const overlay = {
  position: 'fixed',
  inset: 0,
  zIndex: 1050,
  background: 'rgba(0,0,0,0.6)',
  backdropFilter: 'blur(8px)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 16,
};

export const modalContent = {
  maxWidth: 420,
  width: '100%',
  background: 'var(--color-bg-elevated)',
  border: '1px solid var(--color-border-strong)',
  borderRadius: 20,
  padding: '28px 24px',
  boxShadow: '0 20px 60px rgba(0,0,0,0.45)',
  animation: 'scaleIn 0.25s ease',
};

export const inputStyle = {
  width: '100%',
  padding: '10px 14px',
  borderRadius: 12,
  border: '1px solid var(--color-border)',
  background: 'var(--color-bg-surface)',
  color: 'var(--color-text-primary)',
  fontFamily: 'inherit',
  fontSize: '0.9rem',
  outline: 'none',
};

export const activePill = {
  ...pill,
  background: 'var(--color-accent-gradient)',
  color: '#fff',
  border: 'none',
};

export const inactivePill = {
  ...pill,
  background: 'var(--color-bg-surface)',
  color: 'var(--color-text-secondary)',
  border: '1px solid var(--color-border)',
};

export const iconCircle = (size = 44) => ({
  width: size,
  height: size,
  borderRadius: '50%',
  background: 'var(--color-accent-muted)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  flexShrink: 0,
});

export const scoreCircle = {
  width: 44,
  height: 44,
  borderRadius: '50%',
  flexShrink: 0,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontWeight: 800,
  fontSize: '0.9rem',
};
