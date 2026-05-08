import { useCallback } from 'react';
import { Card } from '../../components/ui/Card';
import { useAsyncResource } from '../../hooks/useAsyncResource';
import { fetchJson } from '../../lib/api';

export function InfrastructurePanel() {
  const loader = useCallback(() => fetchJson('/infra/status'), []);
  const { data, isLoading, error } = useAsyncResource(loader, null);

  return (
    <Card title="Infrastructure" subtitle="Redis, Celery, MinIO, LiveKit, WebSocket">
      {isLoading ? <p className="empty-state">Checking infrastructure...</p> : null}
      {error ? <p className="empty-state" style={{ color: '#f87171' }}>{error}</p> : null}
      {data ? (
        <ul className="list-simple">
          <li>
            <strong>Redis</strong>
            <span className={data.redis ? 'pill pill-active' : 'pill pill-end'}>{data.redis ? 'reachable' : 'unreachable'}</span>
          </li>
          <li>
            <strong>MinIO</strong>
            <span>{data.minio.endpoint}</span>
          </li>
          <li>
            <strong>Celery</strong>
            <span>configured</span>
          </li>
          <li>
            <strong>LiveKit</strong>
            <span>{data.livekit.server}</span>
          </li>
          <li>
            <strong>WebSocket</strong>
            <span>{data.websocket.path}</span>
          </li>
        </ul>
      ) : null}
    </Card>
  );
}
