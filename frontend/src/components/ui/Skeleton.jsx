import '../../styles/Skeleton.css';
export function Skeleton({ width, height = 16, borderRadius = 'var(--radius-md)' }) {
  return (
    <>
      <div className="skeleton" style={{ width, height, borderRadius }} />
      
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
      
    </div>
  );
}
