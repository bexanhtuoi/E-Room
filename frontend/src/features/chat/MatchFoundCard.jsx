import { TagBadge } from '../../components/tags/TagBadge';

export function MatchFoundCard({ room, participants = [], onJoin, onDecline }) {
  if (!room) return null;

  const commonTags = room.tags || [];

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1050,
      background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 16,
    }}>
      <div style={{
        maxWidth: 420, width: '100%',
        background: 'var(--color-bg-elevated)',
        border: '1px solid var(--color-border-strong)',
        borderRadius: 20, padding: '28px 24px',
        boxShadow: '0 20px 60px rgba(0,0,0,0.45)',
        animation: 'scaleIn 0.25s ease',
        textAlign: 'center',
      }}>
        {/* Party icon */}
        <div style={{
          width: 56, height: 56, borderRadius: '50%',
          background: 'var(--color-success-muted)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 12px',
        }}>
          <span style={{ fontSize: '1.5rem' }}>🎉</span>
        </div>

        <h4 className="fw-extrabold mb-1" style={{ fontFamily: 'Nunito, sans-serif' }}>
          Match Found!
        </h4>
        <p className="text-muted small mb-3">
          {participants.length} people share your interests
        </p>

        {/* Common tags */}
        {commonTags.length > 0 && (
          <div style={{
            padding: '12px 14px', borderRadius: 12,
            background: 'var(--color-accent-muted)', marginBottom: 16,
          }}>
            <div className="text-muted fw-semibold small mb-2" style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Common Interests
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, justifyContent: 'center' }}>
              {commonTags.map((tag) => (
                <TagBadge key={typeof tag === 'string' ? tag : tag.id} label={typeof tag === 'string' ? tag : tag.name} />
              ))}
            </div>
          </div>
        )}

        {/* Participants */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: -8, marginBottom: 16 }}>
          {participants.slice(0, 5).map((p, i) => (
            <div key={p.id || i} style={{
              width: 36, height: 36, borderRadius: '50%',
              background: `hsl(${i * 72}, 70%, 55%)`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#fff', fontWeight: 700, fontSize: '0.75rem',
              border: '2px solid var(--color-bg-elevated)',
              marginLeft: i > 0 ? -10 : 0,
              zIndex: participants.length - i,
            }}>
              {(p.display_name || p.name || '?')[0].toUpperCase()}
            </div>
          ))}
          {participants.length > 5 && (
            <div style={{
              width: 36, height: 36, borderRadius: '50%',
              background: 'var(--color-bg-surface)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'var(--color-text-muted)', fontWeight: 600, fontSize: '0.7rem',
              border: '2px solid var(--color-bg-elevated)',
              marginLeft: -10,
            }}>
              +{participants.length - 5}
            </div>
          )}
        </div>

        {/* Room info */}
        <div style={{
          padding: '10px 14px', borderRadius: 12,
          background: 'var(--color-bg-surface)', marginBottom: 20,
        }}>
          <div className="fw-bold" style={{ fontSize: '0.92rem' }}>{room.topic || room.name}</div>
          <div className="text-muted" style={{ fontSize: '0.78rem' }}>{room.description || 'Start your conversation'}</div>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: 10 }}>
          {onDecline && (
            <button
              onClick={onDecline}
              style={{
                flex: 1, padding: '10px', borderRadius: 99,
                background: 'var(--color-bg-surface)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-text-secondary)', cursor: 'pointer',
                fontWeight: 600, fontSize: '0.85rem', fontFamily: 'inherit',
                transition: 'all 0.12s',
              }}
              onMouseOver={(e) => { e.currentTarget.style.background = 'var(--color-bg-hover)'; }}
              onMouseOut={(e) => { e.currentTarget.style.background = 'var(--color-bg-surface)'; }}
            >
              Skip
            </button>
          )}
          <button
            onClick={onJoin}
            style={{
              flex: 1, padding: '10px', borderRadius: 99,
              background: 'var(--color-accent-gradient)',
              border: 'none', color: '#fff', cursor: 'pointer',
              fontWeight: 700, fontSize: '0.85rem', fontFamily: 'inherit',
              transition: 'all 0.12s',
              boxShadow: '0 4px 16px var(--color-accent-glow)',
            }}
          >
            Join Room
          </button>
        </div>
      </div>
    </div>
  );
}
