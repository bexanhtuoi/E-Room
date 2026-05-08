export function Skeleton({ width, height = 16, borderRadius = 'var(--radius-md)' }) {
  return (
    <>
      <div className="skeleton" style={{ width, height, borderRadius }} />
      <style>{`
        .skeleton {
          background: linear-gradient(90deg,
            var(--color-bg-surface) 25%,
            var(--color-bg-hover) 50%,
            var(--color-bg-surface) 75%
          );
          background-size: 200% 100%;
          animation: shimmer 1.5s infinite;
        }
        @keyframes shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </>
  );
}

export function CardSkeleton() {
  return (
    <div className="card-skeleton">
      <Skeleton width="60%" height={18} />
      <Skeleton width="40%" height={14} borderRadius="var(--radius-sm)" />
      <div className="card-skeleton-row">
        <Skeleton width="70px" height={20} borderRadius="var(--radius-full)" />
        <Skeleton width="70px" height={20} borderRadius="var(--radius-full)" />
      </div>
      <Skeleton width="100%" height={36} borderRadius="var(--radius-md)" />
      <style>{`
        .card-skeleton {
          padding: 20px; border-radius: var(--radius-lg);
          background: var(--color-bg-surface);
          border: 1px solid var(--color-border);
          display: grid; gap: 12px;
        }
        .card-skeleton-row { display: flex; gap: 8px; }
      `}</style>
    </div>
  );
}
