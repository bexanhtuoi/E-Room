import { useCallback } from 'react';
import { Card } from '../../components/ui/Card';
import { useAsyncResource } from '../../hooks/useAsyncResource';

async function loadHealth() {
  const response = await fetch('http://localhost:8000/health');
  if (!response.ok) {
    throw new Error('Backend health check failed');
  }
  return response.json();
}

export function DashboardOverview() {
  const loader = useCallback(() => loadHealth(), []);
  const { data, isLoading, error } = useAsyncResource(loader, { status: 'unknown' });

  return (
    <Card title="Infrastructure status" subtitle="Backend first, AI later">
      <div className="stats-row">
        <div className="stat-box">
          <span>Status</span>
          <strong>{isLoading ? 'Checking' : data.status}</strong>
        </div>
        <div className="stat-box">
          <span>Persistence</span>
          <strong>SQLModel</strong>
        </div>
        <div className="stat-box">
          <span>Frontend mode</span>
          <strong>Clean scaffold</strong>
        </div>
      </div>
      {error ? <p className="error-text">{error}</p> : null}
    </Card>
  );
}
