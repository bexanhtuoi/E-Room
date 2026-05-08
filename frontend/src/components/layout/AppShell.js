import { useState } from 'react';
import { CreateRoomModal } from '../../features/rooms/CreateRoomModal';

export function AppShell({ children, onRoomCreated, user, onLogout }) {
  const [showCreateRoom, setShowCreateRoom] = useState(false);

  return (
    <main className="app-shell">
      <section className="shell-hero">
        <div className="hero-inner">
          <div>
            <div className="brand">
              <span className="dot" />
              <span className="eyebrow">E-Room</span>
              <span className="status-text">live</span>
            </div>
            <h1>Realtime English speaking rooms</h1>
            <p>Clean infrastructure first. AI features scaffolded until the backend is stable.</p>
          </div>
          <div className="hero-actions">
            {user && (
              <span style={{ color: '#94a3b8', fontSize: 13, marginRight: 8 }}>
                {user.display_name || user.email}
              </span>
            )}
            <button onClick={() => setShowCreateRoom(true)}>New Room</button>
            {onLogout && (
              <button className="outline" onClick={onLogout}>Logout</button>
            )}
          </div>
        </div>
      </section>

      <section className="content-grid">{children}</section>

      {showCreateRoom ? (
        <CreateRoomModal
          onClose={() => setShowCreateRoom(false)}
          onRoomCreated={(room) => {
            setShowCreateRoom(false);
            if (onRoomCreated) onRoomCreated(room);
          }}
        />
      ) : null}
    </main>
  );
}
