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
    <Card title="System" subtitle="Backend first, AI follows">
      <div className="stat-row">
        <div className="stat">
          <span>API status</span>
          <strong>{isLoading ? 'Checking' : data.status}</strong>
        </div>
        <div className="stat">
          <span>Persistence</span>
          <strong>SQLModel</strong>
        </div>
        <div className="stat">
          <span>Mode</span>
          <strong>Clean scaffold</strong>
        </div>
        <div className="stat">
          <span>WebSocket</span>
          <strong>Ready</strong>
        </div>
      </div>
      {error ? <p style={{ marginTop: 12, color: '#f87171', fontSize: 13 }}>{error}</p> : null}
    </Card>
  );
}
