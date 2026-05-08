import { useEffect, useState } from 'react';
import { Card } from '../../components/ui/Card';
import { createRoomSocket } from '../../lib/websocket';

export function RealtimeRoomPanel() {
  const [roomId, setRoomId] = useState('demo-room');
  const [events, setEvents] = useState([]);

  useEffect(() => {
    const socket = createRoomSocket(roomId, (message) => {
      setEvents((current) => [message, ...current].slice(0, 8));
    });

    socket.addEventListener('open', () => {
      socket.send(JSON.stringify({ type: 'heartbeat_probe', roomId }));
    });

    return () => { socket.close(); };
  }, [roomId]);

  return (
    <Card title="Realtime events" subtitle="Room WebSocket event feed">
      <div className="form-row" style={{ marginBottom: 12 }}>
        <input value={roomId} onChange={(event) => setRoomId(event.target.value)} placeholder="Room id" />
      </div>
      {events.length === 0 ? <p className="empty-state">Waiting for room events...</p> : null}
      <ul className="list-simple">
        {events.map((event, index) => (
          <li key={`${event.type}-${index}`}>
            <strong>{event.type}</strong>
            <span>{event.roomId || roomId}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
