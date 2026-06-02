import { useState, useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchJson } from '../../lib/api';
import { TagBadge } from './TagBadge';
import { HiMagnifyingGlass } from 'react-icons/hi2';

export function TagSearch({ onSelect, placeholder = 'Search tags...', exclude = [] }) {
  const [query, setQuery] = useState('');
  const [showResults, setShowResults] = useState(false);
  const ref = useRef(null);

  const { data: results = [] } = useQuery({
    queryKey: ['tagSearch', query],
    queryFn: () => fetchJson(`/tags/search?q=${query}&limit=8`),
    enabled: query.length > 1,
  });

  const filtered = results.filter(
    (r) => !exclude.includes(r.id || r.name || r)
  );

  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) {
        setShowResults(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <HiMagnifyingGlass size={16} style={{ color: 'var(--color-text-muted)', flexShrink: 0 }} />
        <input
          type="text"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setShowResults(true); }}
          onFocus={() => setShowResults(true)}
          placeholder={placeholder}
          style={{
            flex: 1, padding: '8px 0', border: 'none',
            background: 'transparent', color: 'var(--color-text-primary)',
            fontFamily: 'inherit', fontSize: '0.9rem', outline: 'none',
          }}
        />
      </div>

      {showResults && query.length > 1 && filtered.length > 0 && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, right: 0,
          background: 'var(--color-bg-elevated)',
          border: '1px solid var(--color-border)',
          borderRadius: 12, marginTop: 4, zIndex: 10,
          boxShadow: 'var(--shadow-md)', overflow: 'hidden',
        }}>
          {filtered.map((tag) => {
            const id = tag.id || tag.name || tag;
            const name = tag.name || tag;
            return (
              <button
                key={id}
                type="button"
                onClick={() => { onSelect?.(id, name); setShowResults(false); setQuery(''); }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  width: '100%', padding: '10px 14px', border: 'none',
                  background: 'transparent', cursor: 'pointer',
                  color: 'var(--color-text-primary)', fontSize: '0.85rem',
                  fontFamily: 'inherit',
                }}
                onMouseOver={(e) => { e.currentTarget.style.background = 'var(--color-bg-hover)'; }}
                onMouseOut={(e) => { e.currentTarget.style.background = 'transparent'; }}
              >
                <TagBadge label={name} category={tag.category} />
                {tag.category && (
                  <span className="text-muted" style={{ fontSize: '0.72rem', marginLeft: 'auto' }}>{tag.category}</span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
