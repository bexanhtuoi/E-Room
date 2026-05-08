import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { LiveKitRoom, VideoConference } from '@livekit/components-react';
import '@livekit/components-styles';
import { useAuth } from '../../app/AuthContext';
import { fetchJson } from '../../lib/api';

export function RoomPage() {
  const { roomId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [token, setToken] = useState('');
  const [livekitUrl, setLivekitUrl] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function joinAndGetToken() {
      try {
        await fetchJson(`/rooms/${roomId}/join`, {
          method: 'POST',
          body: JSON.stringify({ user_id: user.id }),
        });
        if (cancelled) return;

        const tokenResult = await fetchJson(`/rooms/${roomId}/token`, { method: 'POST' });
        if (cancelled) return;

        setToken(tokenResult.livekit_token);
        setLivekitUrl(tokenResult.livekit_url.replace('ws://', 'wss://').replace('http://', 'https://'));
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    joinAndGetToken();
    return () => { cancelled = true; };
  }, [roomId, user.id]);

  function handleLeave() {
    fetchJson(`/rooms/${roomId}/leave`, {
      method: 'POST',
      body: JSON.stringify({ user_id: user.id }),
    }).catch(() => {});
    navigate('/dashboard');
  }

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: '#020617', color: '#94a3b8', fontSize: 16,
      }}>
        Joining room...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', background: '#020617', gap: 16, padding: 20,
      }}>
        <p style={{ color: '#f87171', fontSize: 16 }}>{error}</p>
        <button onClick={() => navigate('/dashboard')} style={{
          padding: '10px 18px', borderRadius: 10, border: '1px solid rgba(148,163,184,0.15)',
          background: 'rgba(255,255,255,0.06)', color: '#e2e8f0', cursor: 'pointer', fontSize: 14,
        }}>
          Back to dashboard
        </button>
      </div>
    );
  }

  return (
    <div style={{ height: '100vh', background: '#020617' }}>
      <LiveKitRoom
        token={token}
        serverUrl={livekitUrl}
        video={true}
        audio={true}
        onDisconnected={handleLeave}
        style={{ height: '100%' }}
      >
        <VideoConference />
      </LiveKitRoom>
    </div>
  );
}
