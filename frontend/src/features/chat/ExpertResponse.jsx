import { HiSparkles } from 'react-icons/hi2';

export function ExpertResponse({ response }) {
  if (!response) return null;

  return (
    <div style={{
      padding: '12px 14px', borderRadius: 14,
      background: 'var(--color-warning-muted)',
      border: '1px solid rgba(251,191,36,0.2)',
      marginBottom: 8,
    }}>
      <div className="d-flex align-items-start gap-2">
        <div style={{
          width: 24, height: 24, borderRadius: '50%',
          background: 'linear-gradient(135deg, #f59e0b, #d97706)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0, marginTop: 1,
        }}>
          <HiSparkles size={14} color="#fff" />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--color-warning)', marginBottom: 4 }}>
            🧠 Expert Answer
          </div>
          <div style={{ fontSize: '0.88rem', lineHeight: 1.5, color: 'var(--color-text-primary)', marginBottom: 6 }}>
            {response.text}
          </div>
          {response.sources && response.sources.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {response.sources.map((src, i) => (
                <span key={i} style={{
                  padding: '2px 8px', borderRadius: 99,
                  background: 'rgba(251,191,36,0.1)',
                  color: 'var(--color-warning)', fontSize: '0.65rem',
                  fontWeight: 600,
                }}>
                  🔗 {src.title || src}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
