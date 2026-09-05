import { TagBadge } from '../../components/tags/TagBadge';
import './MatchFoundCard.css';

export function MatchFoundCard({ room, participants = [], onJoin, onDecline }) {
  if (!room) return null;

  const commonTags = room.tags || [];

  return (
    <div className="match-found-overlay">
      <div className="match-found-card">
        {/* Party icon */}
        <div className="match-found-icon">
          <span className="match-found-icon-emoji">🎉</span>
        </div>

        <h4 className="fw-extrabold mb-1 match-found-heading">
          Match Found!
        </h4>
        <p className="text-muted small mb-3">
          {participants.length} people share your interests
        </p>

        {/* Common tags */}
        {commonTags.length > 0 && (
          <div className="match-found-common-tags">
            <div className="text-muted fw-semibold small mb-2 match-found-common-label">
              Common Interests
            </div>
            <div className="match-found-tags-flex">
              {commonTags.map((tag) => (
                <TagBadge key={typeof tag === 'string' ? tag : tag.id} label={typeof tag === 'string' ? tag : tag.name} />
              ))}
            </div>
          </div>
        )}

        {/* Participants */}
        <div className="match-found-participants">
          {participants.slice(0, 5).map((p, i) => (
            <div key={p.id || i} className="match-found-participant" style={{
              background: `hsl(${i * 72}, 70%, 55%)`,
              marginLeft: i > 0 ? -10 : 0,
              zIndex: participants.length - i,
            }}>
              {(p.display_name || p.name || '?')[0].toUpperCase()}
            </div>
          ))}
          {participants.length > 5 && (
            <div className="match-found-participant-more">
              +{participants.length - 5}
            </div>
          )}
        </div>

        {/* Room info */}
        <div className="match-found-room-info">
          <div className="fw-bold match-found-room-topic">{room.name}</div>
          <div className="text-muted match-found-room-desc">{room.description || 'Start your conversation'}</div>
        </div>

        {/* Actions */}
        <div className="match-found-actions">
          {onDecline && (
            <button
              onClick={onDecline}
              className="match-found-btn-skip"
              onMouseOver={(e) => { e.currentTarget.style.background = 'var(--color-bg-hover)'; }}
              onMouseOut={(e) => { e.currentTarget.style.background = 'var(--color-bg-surface)'; }}
            >
              Skip
            </button>
          )}
          <button
            onClick={onJoin}
            className="match-found-btn-join"
          >
            Join Room
          </button>
        </div>
      </div>
    </div>
  );
}
