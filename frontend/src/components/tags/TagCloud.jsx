import { TagBadge } from './TagBadge';

export function TagCloud({ tags = [], selected = [], onToggle }) {

  const grouped = {};
  tags.forEach((tag) => {
    const cat = tag.category || 'Other';
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(tag);
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {Object.entries(grouped).map(([category, categoryTags]) => (
        <div key={category}>
          <div className="text-muted fw-semibold small mb-2" style={{ textTransform: 'uppercase', letterSpacing: '0.05em', fontSize: '0.7rem' }}>
            {category}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {categoryTags.map((tag) => {
              const id = tag.id || tag.name || tag;
              const name = tag.name || tag;
              const isSelected = selected.includes(id);
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => onToggle?.(id)}
                  style={{
                    padding: '6px 14px', borderRadius: 99,
                    background: isSelected ? 'var(--color-accent-gradient)' : 'var(--color-bg-surface)',
                    color: isSelected ? '#fff' : 'var(--color-text-secondary)',
                    border: isSelected ? 'none' : '1px solid var(--color-border)',
                    cursor: 'pointer', fontWeight: 600, fontSize: '0.78rem',
                    fontFamily: 'inherit', transition: 'all 0.12s',
                  }}
                >
                  {name}
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
