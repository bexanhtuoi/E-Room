import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Spinner from 'react-bootstrap/Spinner';
import { fetchJson } from '../../lib/api';
import { TagBadge } from '../../components/tags/TagBadge';
import { HiTag } from 'react-icons/hi2';

const FALLBACK_TAGS = [
  'Business', 'Technology', 'Travel', 'Education', 'IELTS',
  'Daily Life', 'Pronunciation', 'Interview', 'Culture', 'Science',
  'Food', 'Music', 'Gaming', 'Sports', 'Movies', 'Fashion',
  'Health', 'Startup', 'Marketing', 'Finance',
];

export function StepTagPicker({ form, updateField }) {
  const [search, setSearch] = useState('');
  const [customTag, setCustomTag] = useState('');

  const { data: popularTags = [], isLoading } = useQuery({
    queryKey: ['popularTags'],
    queryFn: () => fetchJson('/tags/popular'),
  });

  const { data: searchResults = [] } = useQuery({
    queryKey: ['tagSearch', search],
    queryFn: () => fetchJson(`/tags/search?q=${search}&limit=8`),
    enabled: search.length > 1,
  });

  const tags = popularTags.length > 0 ? popularTags : FALLBACK_TAGS;
  const selected = form.tagIds || [];

  function toggleTag(tag) {
    const id = typeof tag === 'string' ? tag : tag.id || tag.name || tag;
    const updated = selected.includes(id)
      ? selected.filter((t) => t !== id)
      : [...selected, id];
    updateField('tagIds', updated);
  }

  function addCustomTag() {
    const tag = customTag.trim();
    if (tag && !selected.includes(tag)) {
      updateField('tagIds', [...selected, tag]);
      setCustomTag('');
    }
  }

  return (
    <div>
      <div className="text-center mb-3">
        <HiTag size={36} style={{ color: 'var(--color-accent)' }} />
        <h4 className="fw-bold mt-2 mb-1">What topics interest you?</h4>
        <p className="text-muted small mb-0">
          Pick at least one tag so we can match you with learners who share your interests.
        </p>
        {selected.length === 0 && (
          <p className="small mt-1" style={{ color: 'var(--color-warning)' }}>
            ⚠️ You can skip, but auto-matching will be unavailable until you add tags.
          </p>
        )}
      </div>

      {/* Selected tags */}
      {selected.length > 0 && (
        <div style={{
          display: 'flex', flexWrap: 'wrap', gap: 6,
          padding: '12px', borderRadius: 12,
          background: 'var(--color-accent-muted)', marginBottom: 16,
        }}>
          {selected.map((tag) => (
            <TagBadge
              key={tag}
              label={tag}
              removable
              onRemove={() => toggleTag(tag)}
            />
          ))}
        </div>
      )}

      {/* Search */}
      <div style={{ position: 'relative', marginBottom: 16 }}>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search tags..."
          style={{
            width: '100%', padding: '10px 14px', borderRadius: 12,
            border: '1px solid var(--color-border)',
            background: 'var(--color-bg-surface)',
            color: 'var(--color-text-primary)',
            fontFamily: 'inherit', fontSize: '0.9rem',
            outline: 'none',
          }}
          onFocus={(e) => { e.target.style.borderColor = 'var(--color-accent)'; }}
          onBlur={(e) => { e.target.style.borderColor = 'var(--color-border)'; }}
        />
        {search.length > 1 && searchResults.length > 0 && (
          <div style={{
            position: 'absolute', top: '100%', left: 0, right: 0,
            background: 'var(--color-bg-elevated)',
            border: '1px solid var(--color-border)',
            borderRadius: 12, marginTop: 4, zIndex: 10,
            boxShadow: 'var(--shadow-md)', overflow: 'hidden',
          }}>
            {searchResults.map((tag) => (
              <button
                key={tag.id || tag}
                type="button"
                onClick={() => toggleTag(tag)}
                style={{
                  display: 'block', width: '100%', padding: '8px 14px',
                  border: 'none', background: 'transparent',
                  textAlign: 'left', cursor: 'pointer',
                  color: 'var(--color-text-primary)', fontSize: '0.85rem',
                  fontFamily: 'inherit',
                }}
                onMouseOver={(e) => { e.currentTarget.style.background = 'var(--color-bg-hover)'; }}
                onMouseOut={(e) => { e.currentTarget.style.background = 'transparent'; }}
              >
                {tag.name || tag}
                {tag.category && (
                  <span className="text-muted" style={{ fontSize: '0.75rem', marginLeft: 8 }}>
                    {tag.category}
                  </span>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Tag cloud */}
      {isLoading ? (
        <div className="text-center py-4"><Spinner animation="border" size="sm" /></div>
      ) : (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {tags.map((tag) => {
            const id = typeof tag === 'string' ? tag : tag.id || tag.name || tag;
            const name = typeof tag === 'string' ? tag : tag.name || tag;
            return (
              <button
                key={id}
                type="button"
                onClick={() => toggleTag(id)}
                style={{
                  padding: '6px 14px', borderRadius: 99,
                  background: selected.includes(id)
                    ? 'var(--color-accent-gradient)'
                    : 'var(--color-bg-surface)',
                  color: selected.includes(id) ? '#fff' : 'var(--color-text-secondary)',
                  border: selected.includes(id) ? 'none' : '1px solid var(--color-border)',
                  cursor: 'pointer', fontWeight: 600, fontSize: '0.8rem',
                  fontFamily: 'inherit', transition: 'all 0.12s',
                }}
              >
                {name}
              </button>
            );
          })}
        </div>
      )}

      {/* Custom tag input */}
      <div style={{ display: 'flex', gap: 8, marginTop: 16, alignItems: 'center' }}>
        <input
          type="text"
          value={customTag}
          onChange={(e) => setCustomTag(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addCustomTag(); } }}
          placeholder="Or type a custom tag..."
          style={{
            flex: 1, padding: '8px 12px', borderRadius: 99,
            border: '1px solid var(--color-border)',
            background: 'var(--color-bg-surface)',
            color: 'var(--color-text-primary)',
            fontFamily: 'inherit', fontSize: '0.82rem', outline: 'none',
          }}
        />
        <button
          type="button"
          onClick={addCustomTag}
          disabled={!customTag.trim()}
          style={{
            padding: '8px 16px', borderRadius: 99,
            background: customTag.trim() ? 'var(--color-accent-gradient)' : 'var(--color-bg-hover)',
            color: customTag.trim() ? '#fff' : 'var(--color-text-muted)',
            border: 'none', cursor: customTag.trim() ? 'pointer' : 'not-allowed',
            fontWeight: 600, fontSize: '0.8rem', fontFamily: 'inherit',
            transition: 'all 0.12s', opacity: customTag.trim() ? 1 : 0.5,
          }}
        >
          + Add
        </button>
      </div>
    </div>
  );
}
