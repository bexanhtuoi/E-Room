import { useSubscriptionStore } from '../../stores/subscriptionStore';

export function QuotaIndicator({ type = 'corrections', used = 0, total = 3 }) {
  const { tier } = useSubscriptionStore();
  const pct = total === Infinity ? 100 : Math.min(Math.round((used / total) * 100), 100);
  const isUnlimited = total === Infinity;
  const isLow = !isUnlimited && pct >= 80;
  const isExhausted = !isUnlimited && used >= total;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{
        flex: 1, height: 6, borderRadius: 99,
        background: 'var(--color-bg-surface)',
        overflow: 'hidden',
        maxWidth: 80,
      }}>
        <div style={{
          height: '100%', width: isUnlimited ? 100 : `${pct}%`,
          borderRadius: 99,
          background: isExhausted ? 'var(--color-danger)' : isLow ? 'var(--color-warning)' : 'var(--color-accent-gradient)',
          transition: 'width 0.3s ease',
        }} />
      </div>
      <span style={{
        fontSize: '0.7rem', fontWeight: 600, whiteSpace: 'nowrap',
        color: isExhausted ? 'var(--color-danger)' : isLow ? 'var(--color-warning)' : 'var(--color-text-muted)',
      }}>
        {isUnlimited ? `${used} ♾️` : `${used}/${total}`}
      </span>
    </div>
  );
}

export function QuotaRow({ label, type, used, total }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '6px 0', fontSize: '0.78rem',
    }}>
      <span style={{ color: 'var(--color-text-secondary)', fontWeight: 600 }}>{label}</span>
      <QuotaIndicator type={type} used={used} total={total} />
    </div>
  );
}
