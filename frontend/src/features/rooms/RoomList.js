import { useCallback } from 'react';
import { Card } from '../../components/ui/Card';
import { useAsyncResource } from '../../hooks/useAsyncResource';
import { fetchJson } from '../../lib/api';

export function RoomList() {
  const loader = useCallback(() => fetchJson('/rooms'), []);
  const { data, isLoading, error } = useAsyncResource(loader, []);

  return (
    <Card title="Rooms" subtitle="Core room resource wired to backend">
      {isLoading ? <p>Loading rooms...</p> : null}
      {error ? <p className="error-text">{error}</p> : null}
      {!isLoading && !error && data.length === 0 ? <p>No rooms yet.</p> : null}
      <ul className="simple-list">
        {data.map((room) => (
          <li key={room.id}>
            <strong>{room.topic || room.livekit_room_name}</strong>
            <span>{room.status}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
