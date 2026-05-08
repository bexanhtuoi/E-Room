import { Badge } from './Badge';
import { Avatar } from './Avatar';

const STATUS_LABELS = {
  active: 'Live',
  matching: 'Matching',
  ended: 'Ended',
};

export function RoomCard({ room, onClick }) {
  const status = room?.status || 'matching';
  const participantCount = room?.participants?.length || room?.participant_count || 0;
  const tags = room?.tags || [];

  return (
    <>
      <article className="room-card fade-in" onClick={() => onClick?.(room)} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter') onClick?.(room); }}>
        <div className="room-card-top">
          <Badge label={STATUS_LABELS[status] || status} variant={status} withDot />
          <span className="room-card-participants">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>
            {participantCount}
          </span>
        </div>
        <h3 className="room-card-name">{room?.name || room?.room_name || 'Untitled Room'}</h3>
        <div className="room-card-tags">
          {tags.slice(0, 3).map((t, i) => (
            <Badge key={i} label={typeof t === 'string' ? t : t.name} variant="tag" />
          ))}
        </div>
        <div className="room-card-avatars">
          {(room?.participants || []).slice(0, 4).map((p, i) => (
            <Avatar key={i} name={p.display_name || p.name || ''} size={28} />
          ))}
          {participantCount > 4 && (
            <span className="room-card-extra">+{participantCount - 4}</span>
          )}
        </div>
        <button className="room-card-join-btn">Join Room</button>
      </article>
      <style>{`
        .room-card {
          display: flex; flex-direction: column; gap: 10px;
          padding: 20px; border-radius: var(--radius-lg);
          background: var(--color-bg-surface);
          border: 1px solid var(--color-border);
          cursor: pointer;
          transition: all var(--transition-base);
          position: relative; overflow: hidden;
        }
        .room-card::before {
          content: ''; position: absolute; inset: 0;
          border-radius: var(--radius-lg);
          background: radial-gradient(600px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), var(--color-accent-muted), transparent 40%);
          opacity: 0; transition: opacity var(--transition-base);
        }
        .room-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); border-color: var(--color-border-strong); }
        .room-card:hover::before { opacity: 1; }
        .room-card-top { display: flex; align-items: center; justify-content: space-between; position: relative; z-index: 1; }
        .room-card-participants { display: flex; align-items: center; gap: 4px; font-size: 12px; color: var(--color-text-muted); }
        .room-card-name {
          font-family: var(--font-display); font-size: 17px; font-weight: 600;
          color: var(--color-text-primary); line-height: 1.3;
          position: relative; z-index: 1;
        }
        .room-card-tags { display: flex; gap: 6px; flex-wrap: wrap; position: relative; z-index: 1; }
        .room-card-avatars { display: flex; align-items: center; gap: -6px; position: relative; z-index: 1; }
        .room-card-avatars > * { margin-left: -6px; border: 2px solid var(--color-bg-surface); border-radius: var(--radius-full); }
        .room-card-avatars > *:first-child { margin-left: 0; }
        .room-card-extra {
          display: inline-flex; align-items: center; justify-content: center;
          width: 28px; height: 28px; border-radius: var(--radius-full);
          background: var(--color-bg-hover); color: var(--color-text-muted);
          font-size: 11px; font-weight: 600; margin-left: -6px;
          border: 2px solid var(--color-bg-surface);
        }
        .room-card-join-btn {
          padding: 9px 16px; border-radius: var(--radius-md);
          background: var(--color-accent); color: #fff;
          font-size: 13px; font-weight: 600;
          transition: all var(--transition-fast);
          position: relative; z-index: 1; align-self: flex-start;
        }
        .room-card-join-btn:hover { background: var(--color-accent-hover); transform: scale(1.03); }
      `}</style>
    </>
  );
}
