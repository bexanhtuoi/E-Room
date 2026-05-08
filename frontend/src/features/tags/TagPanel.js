import { useCallback } from 'react';
import { Card } from '../../components/ui/Card';
import { useAsyncResource } from '../../hooks/useAsyncResource';
import { fetchJson } from '../../lib/api';

export function TagPanel() {
  const loader = useCallback(() => fetchJson('/tags/popular'), []);
  const { data, isLoading, error } = useAsyncResource(loader, []);

  return (
    <Card title="Tags" subtitle="Popular and searchable topic layer">
      {isLoading ? <p>Loading tags...</p> : null}
      {error ? <p className="error-text">{error}</p> : null}
      {!isLoading && !error && data.length === 0 ? <p>No tags seeded yet.</p> : null}
      <div className="tag-cloud">
        {data.map((tag) => (
          <span key={tag.id} className="tag-pill">
            {tag.name}
          </span>
        ))}
      </div>
    </Card>
  );
}
