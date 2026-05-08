import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { LiveKitRoom, VideoConference } from '@livekit/components-react';
import '@livekit/components-styles';
import { fetchJson } from '../../lib/api';
import { ChatBox } from '../../components/ui/ChatBox';
import { Badge } from '../../components/ui/Badge';

export function RoomPage() {
  const { roomId } = useParams();
  const navigate = useNavigate();
  const [token, setToken] = useState('');
  const [livekitUrl, setLivekitUrl] = useState('');
  const [roomName, setRoomName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [chatOpen, setChatOpen] = useState(false);
  const [left, setLeft] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function joinAndGetToken() {
      try {
        const roomData = await fetchJson(`/rooms/${roomId}`);
        if (!cancelled) setRoomName(roomData?.name || roomData?.room_name || 'Room');

        await fetchJson(`/rooms/${roomId}/join`, { method: 'POST' });
        if (cancelled) return;

        const tokenResult = await fetchJson(`/rooms/${roomId}/token`, { method: 'POST' });
        if (cancelled) return;

        setToken(tokenResult.livekit_token);
        setLivekitUrl(
          (tokenResult.livekit_url || 'ws://localhost:7880')
            .replace('ws://', 'wss://')
            .replace('http://', 'https://')
        );
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    joinAndGetToken();
    return () => { cancelled = true; };
  }, [roomId]);

  function handleLeave() {
    fetchJson(`/rooms/${roomId}/leave`, { method: 'POST' }).catch(() => {});
    setLeft(true);
  }

  function handleDisconnected() {
    setLeft(true);
  }

  function goBack() {
    navigate('/dashboard');
  }

  if (loading) {
    return (
      <div className="room-loading" role="status">
        <div className="room-loading-spinner" />
        <p>Joining room...</p>
        <style>{`
          .room-loading {
            display: flex; flex-direction: column; align-items: center;
            justify-content: center; min-height: 100vh; gap: 16px;
            background: var(--color-bg); color: var(--color-text-secondary);
          }
          .room-loading-spinner {
            width: 32px; height: 32px; border: 3px solid var(--color-border-strong);
            border-top-color: var(--color-accent); border-radius: 50%;
            animation: spin 0.8s linear infinite;
          }
          @keyframes spin { to { transform: rotate(360deg); } }
        `}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div className="room-error" role="alert">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>
        <h2>Failed to join room</h2>
        <p>{error}</p>
        <div className="room-error-actions">
          <button className="room-btn-secondary" onClick={() => window.location.reload()}>Retry</button>
          <button className="room-btn-primary" onClick={goBack}>Back to dashboard</button>
        </div>
        <style>{`
          .room-error {
            display: flex; flex-direction: column; align-items: center;
            justify-content: center; min-height: 100vh; gap: 12px;
            background: var(--color-bg); color: var(--color-text-primary);
            text-align: center; padding: 20px;
          }
          .room-error h2 { font-family: var(--font-display); font-size: 20px; }
          .room-error p { color: var(--color-text-secondary); font-size: 14px; max-width: 400px; }
          .room-error svg { color: var(--color-danger); }
          .room-error-actions { display: flex; gap: 10px; margin-top: 8px; }
          .room-btn-primary {
            padding: 10px 18px; border-radius: var(--radius-md);
            background: var(--color-accent); color: #fff;
            font-size: 13px; font-weight: 600;
          }
          .room-btn-secondary {
            padding: 10px 18px; border-radius: var(--radius-md);
            background: var(--color-bg-surface); color: var(--color-text-primary);
            border: 1px solid var(--color-border); font-size: 13px; font-weight: 500;
          }
        `}</style>
      </div>
    );
  }

  if (left) {
    return (
      <div className="room-left">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
        <h2>You left the room</h2>
        <p>Thanks for participating in {roomName || 'the session'}!</p>
        <button className="room-btn-primary" onClick={goBack}>Back to dashboard</button>
        <style>{`
          .room-left {
            display: flex; flex-direction: column; align-items: center;
            justify-content: center; min-height: 100vh; gap: 12px;
            background: var(--color-bg); color: var(--color-text-primary);
            text-align: center; padding: 20px;
          }
          .room-left h2 { font-family: var(--font-display); font-size: 22px; }
          .room-left p { color: var(--color-text-secondary); font-size: 14px; }
          .room-left svg { color: var(--color-accent); }
        `}</style>
      </div>
    );
  }

  return (
    <div className="room-page">
      <header className="room-topbar">
        <div className="room-topbar-left">
          <button className="room-back-btn" onClick={goBack} title="Back to dashboard">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" /></svg>
          </button>
          <div>
            <h1 className="room-topbar-name">{roomName || 'Room'}</h1>
            <span className="room-topbar-status"><Badge label="Live" variant="live" withDot /></span>
          </div>
        </div>
        <div className="room-topbar-right">
          <button
            className={`room-chat-toggle ${chatOpen ? 'active' : ''}`}
            onClick={() => setChatOpen(!chatOpen)}
            title={chatOpen ? 'Hide chat' : 'Show chat'}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
            Chat
          </button>
          <button className="room-leave-btn" onClick={handleLeave}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="9" y1="9" x2="15" y2="15" /><line x1="15" y1="9" x2="9" y2="15" /></svg>
            Leave
          </button>
        </div>
      </header>

      <div className="room-main">
        <div className={`room-video-area ${!chatOpen ? 'expanded' : ''}`}>
          <LiveKitRoom
            token={token}
            serverUrl={livekitUrl}
            video={true}
            audio={true}
            onDisconnected={handleDisconnected}
            style={{ height: '100%' }}
          >
            <VideoConference />
          </LiveKitRoom>
        </div>
        {chatOpen && (
          <ChatBox
            roomId={roomId}
            visible={chatOpen}
            onToggle={() => setChatOpen(false)}
          />
        )}
      </div>

      <footer className="room-controls">
        <span className="room-controls-hint">Use the LiveKit controls above to manage your camera and mic</span>
      </footer>

      <style>{`
        .room-page {
          display: flex; flex-direction: column;
          height: 100vh; background: var(--color-bg);
          overflow: hidden;
        }
        .room-topbar {
          display: flex; align-items: center; justify-content: space-between;
          height: 52px; padding: 0 16px;
          background: var(--color-bg-elevated);
          border-bottom: 1px solid var(--color-border);
          flex-shrink: 0; z-index: 10;
        }
        .room-topbar-left { display: flex; align-items: center; gap: 10px; }
        .room-back-btn {
          display: flex; align-items: center; justify-content: center;
          width: 32px; height: 32px; border-radius: var(--radius-sm);
          color: var(--color-text-secondary); transition: all var(--transition-fast);
        }
        .room-back-btn:hover { color: var(--color-text-primary); background: var(--color-bg-hover); }
        .room-topbar-name {
          font-family: var(--font-display); font-size: 16px; font-weight: 600;
          color: var(--color-text-primary); line-height: 1.2;
        }
        .room-topbar-status { font-size: 11px; }
        .room-topbar-right { display: flex; align-items: center; gap: 8px; }
        .room-chat-toggle {
          display: flex; align-items: center; gap: 5px;
          padding: 6px 12px; border-radius: var(--radius-md);
          color: var(--color-text-secondary); font-size: 13px; font-weight: 500;
          transition: all var(--transition-fast);
        }
        .room-chat-toggle:hover, .room-chat-toggle.active {
          color: var(--color-accent); background: var(--color-accent-muted);
        }
        .room-leave-btn {
          display: flex; align-items: center; gap: 5px;
          padding: 6px 14px; border-radius: var(--radius-md);
          background: var(--color-danger); color: #fff;
          font-size: 13px; font-weight: 600;
          transition: all var(--transition-fast);
        }
        .room-leave-btn:hover { background: var(--color-danger-hover); }

        .room-main {
          display: flex; flex: 1; overflow: hidden;
        }
        .room-video-area {
          flex: 1; overflow: hidden; transition: all var(--transition-base);
        }
        .room-video-area.expanded { flex: 1; }

        .room-controls {
          display: flex; align-items: center; justify-content: center;
          height: 36px; padding: 0 16px;
          background: var(--color-bg-elevated);
          border-top: 1px solid var(--color-border);
          flex-shrink: 0;
        }
        .room-controls-hint {
          font-size: 11px; color: var(--color-text-muted);
        }
      `}</style>
    </div>
  );
}
