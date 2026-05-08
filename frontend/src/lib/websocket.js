export function createRoomSocket(roomId, onMessage) {
  const baseUrl = process.env.REACT_APP_WS_BASE_URL || 'ws://localhost:8000';
  const socket = new WebSocket(`${baseUrl}/api/v1/ws/rooms/${roomId}`);

  socket.addEventListener('message', (event) => {
    const data = JSON.parse(event.data);
    onMessage(data);
  });

  return socket;
}
