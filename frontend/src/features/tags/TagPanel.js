import { useCallback, useState } from 'react';
import { Card } from '../../components/ui/Card';
import { useAsyncResource } from '../../hooks/useAsyncResource';
import { fetchJson } from '../../lib/api';

export function TagPanel() {
  const loader = useCallback(() => fetchJson('/tags/popular'), []);
  const { data, isLoading, error } = useAsyncResource(loader, []);
  const [selected, setSelected] = useState([]);

  function toggleTag(tagId) {
    setSelected((current) =>
      current.includes(tagId) ? current.filter((id) => id !== tagId) : [...current, tagId]
    );
  }

  return (
    <Card title="Tags" subtitle="Pick topics for matching" action={
      selected.length > 0 ? <span className="pill pill-active">{selected.length} selected</span> : null
    }>
      {isLoading ? <p className="empty-state">Loading tags...</p> : null}
      {error ? <p className="empty-state" style={{ color: '#f87171' }}>{error}</p> : null}
      {!isLoading && !error && data.length === 0 ? <p className="empty-state">No tags seeded yet</p> : null}
      <div className="tag-cloud">
        {data.map((tag) => (
          <span
            key={tag.id}
            className={`tag-chip${selected.includes(tag.id) ? ' selected' : ''}`}
            onClick={() => toggleTag(tag.id)}
          >
            {tag.name}
          </span>
        ))}
      </div>
    </Card>
  );
}
