import { HiXMark } from 'react-icons/hi2';

const CATEGORY_COLORS = {
  technology: { bg: '#ffffff20', fg: '#ffffff' },
  business:   { bg: '#ffffff20', fg: '#ffffff' },
  science:    { bg: '#ffffff20', fg: '#ffffff' },
  creative:   { bg: '#f472b620', fg: '#f472b6' },
  lifestyle:  { bg: '#fbbf2420', fg: '#fbbf24' },
  default:    { bg: 'var(--color-accent-muted)', fg: 'var(--color-accent)' },
};

function getColor(category) {
  return CATEGORY_COLORS[category?.toLowerCase()] || CATEGORY_COLORS.default;
}

export function TagBadge({ label, category, removable, onRemove, onClick }) {
  const { bg, fg } = getColor(category);

  return (
    <span
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 4,
        padding: '4px 10px', borderRadius: 99,
        background: bg, color: fg,
        fontSize: '0.78rem', fontWeight: 600,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.12s',
        userSelect: 'none', whiteSpace: 'nowrap',
      }}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => { if (onClick && e.key === 'Enter') onClick(); }}
    >
      {label}
      {removable && (
        <HiXMark
          size={14}
          style={{ cursor: 'pointer', opacity: 0.7, flexShrink: 0 }}
          onClick={(e) => { e.stopPropagation(); onRemove?.(); }}
        />
      )}
    </span>
  );
}
