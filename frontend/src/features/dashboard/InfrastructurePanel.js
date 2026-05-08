import { useCallback } from 'react';
import { Card } from '../../components/ui/Card';
import { useAsyncResource } from '../../hooks/useAsyncResource';
import { fetchJson } from '../../lib/api';

export function InfrastructurePanel() {
  const loader = useCallback(() => fetchJson('/infra/status'), []);
  const { data, isLoading, error } = useAsyncResource(loader, null);

  return (
    <Card title="Infrastructure services" subtitle="Redis, Celery, MinIO, video, websocket scaffolds">
      {isLoading ? <p>Checking infrastructure...</p> : null}
      {error ? <p className="error-text">{error}</p> : null}
      {data ? (
        <ul className="simple-list">
          <li>
            <strong>Redis</strong>
            <span>{data.redis ? 'reachable' : 'unreachable'}</span>
          </li>
          <li>
            <strong>MinIO</strong>
            <span>{data.minio.endpoint}</span>
          </li>
          <li>
            <strong>Celery</strong>
            <span>broker configured</span>
          </li>
          <li>
            <strong>Video server</strong>
            <span>{data.video.videoServer}</span>
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
