import { useEffect, useState } from 'react';
import { Card } from '../../components/ui/Card';
import { createRoomSocket } from '../../lib/websocket';

export function RoomSocketPreview() {
  const [events, setEvents] = useState([]);

  useEffect(() => {
    const socket = createRoomSocket('demo-room', (message) => {
      setEvents((current) => [message, ...current].slice(0, 5));
    });

    socket.addEventListener('open', () => {
      socket.send(JSON.stringify({ type: 'client_ready', source: 'frontend-preview' }));
    });

    return () => {
      socket.close();
    };
  }, []);

  return (
    <Card title="WebSocket room preview" subtitle="Contract-first realtime event channel">
      {events.length === 0 ? <p>Waiting for room events...</p> : null}
      <ul className="simple-list">
        {events.map((event, index) => (
          <li key={`${event.type}-${index}`}>
            <strong>{event.type}</strong>
            <span>{event.roomId || 'system'}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
