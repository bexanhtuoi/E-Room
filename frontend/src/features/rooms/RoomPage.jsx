import { useEffect, useState, useCallback, useRef, forwardRef, useImperativeHandle } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { LiveKitRoom, GridLayout, ParticipantTile, useLocalParticipant, useRemoteParticipants, useRoomContext, useTracks } from '@livekit/components-react';
import '@livekit/components-styles';
import { Track } from 'livekit-client';
import { fetchJson, ApiClient, API_BASE_URL, getTokens } from '../../lib/api';
import { createAudioCapture } from '../../lib/audioCapture';
import { ChatWindow } from '../chat/ChatWindow';
import { useAuth } from '../../app/AuthContext';
import '../../styles/RoomPage.css';
import {
  HiArrowLeft, HiMicrophone, HiVideoCamera, HiVideoCameraSlash,
  HiMicrophone as HiMicOff, HiPhoneXMark, HiChatBubbleLeftRight,
  HiUserGroup, HiShieldExclamation, HiClock, HiCheckCircle, HiArrowRight,
  HiHandRaised, HiFaceSmile, HiComputerDesktop,
  HiUserPlus, HiUser, HiEllipsisVertical,
} from 'react-icons/hi2';

const SIZES = { topbar: 56, controls: 68 };
const COLOR = {
  danger: 'var(--color-danger)',
  muted: 'var(--color-text-muted)',
  accent: 'var(--color-accent)',
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
};
const EMOJIS = ['👋', '👍', '❤️', '😂', '🔥', '👏', '🎉', '💯', '✨', '🙌'];

function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function formatParticipantName(name, identity, isLocal) {
  if (isLocal) return 'You';
  if (name && !/^[0-9a-f]{8}-[0-9a-f]{4}-/i.test(name)) return name;
  if (name) return 'P' + name.replace(/-/g, '').slice(0, 5);
  if (identity && !/^[0-9a-f]{8}-[0-9a-f]{4}-/i.test(identity)) return identity;
  return 'Participant';
}

function getInitials(name) {
  if (!name) return '?';
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
}

function hashColor(name) {
  const PALETTE = ['#ffffff','#e0e0e0','#ec4899','#f59e0b','#c0c0c0','#a0a0a0','#f43f5e','#d0d0d0'];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return PALETTE[Math.abs(hash) % PALETTE.length];
}

function ControlBtn({ icon: Icon, active, onClick, label, danger, className = '' }) {
  return (
    <button
      className={`ctrl-btn ${danger ? 'ctrl-btn--danger' : ''} ${active ? 'ctrl-btn--active' : ''} ${className}`}
      onClick={onClick} aria-label={label} title={label}
    >
      <Icon size={20} />
    </button>
  );
}

function MeetControls({ onLeave, togglePanel, activePanel, handRaised, setHandRaised,
  showEmojiPicker, setShowEmojiPicker, sendEmoji, screenShareOn, setScreenShareOn }) {
  const { localParticipant } = useLocalParticipant();
  const room = useRoomContext();
  const [micOn, setMicOn] = useState(true);
  const [camOn, setCamOn] = useState(true);

  useEffect(() => {
    if (localParticipant) {
      setMicOn(localParticipant.isMicrophoneEnabled ?? true);
      setCamOn(localParticipant.isCameraEnabled ?? true);
      setScreenShareOn(localParticipant.isScreenShareEnabled ?? false);
    }
  }, [localParticipant]);

  const toggleMic = useCallback(async () => {
    if (!localParticipant) { setMicOn(p => !p); return; }
    try {
      const newState = !localParticipant.isMicrophoneEnabled;
      await localParticipant.setMicrophoneEnabled(newState);
      setMicOn(newState);
    } catch (e) { console.warn('toggleMic:', e); }
  }, [localParticipant]);

  const toggleCam = useCallback(async () => {
    if (!localParticipant) { setCamOn(p => !p); return; }
    try {
      const newState = !localParticipant.isCameraEnabled;
      await localParticipant.setCameraEnabled(newState);
      setCamOn(newState);
    } catch (e) { console.warn('toggleCam:', e); }
  }, [localParticipant]);

  const toggleScreenShare = useCallback(async () => {
    if (!localParticipant) { setScreenShareOn(p => !p); return; }
    try {
      const newState = !localParticipant.isScreenShareEnabled;
      await localParticipant.setScreenShareEnabled(newState);
      setScreenShareOn(newState);
    } catch (e) { console.warn('toggleScreenShare:', e); }
  }, [localParticipant, setScreenShareOn]);

  const toggleHandRaise = useCallback(() => {
    setHandRaised(prev => {
      const newState = !prev;
      if (localParticipant) {
        try {
          const data = JSON.stringify({ type: 'hand_raise', state: newState });
          localParticipant.publishData(new TextEncoder().encode(data), { reliable: true });
        } catch {}
      }
      return newState;
    });
  }, [localParticipant, setHandRaised]);

  useEffect(() => {
    if (!room) return;
    const handler = (payload, participant) => {
      if (!participant || participant.identity === localParticipant?.identity) return;
      try {
        const msg = JSON.parse(new TextDecoder().decode(payload));
        if (msg.type === 'hand_raise') {
          window.dispatchEvent(new CustomEvent('hand-raise-notif', {
            detail: { identity: participant.identity, name: participant.name || 'Participant', state: msg.state, id: Date.now() + Math.random() }
          }));
        }
      } catch {}
    };
    room.on('dataReceived', handler);
    return () => room.off('dataReceived', handler);
  }, [room, localParticipant]);

  return (
    <footer className="meet-controls">
      <div className="meet-controls-center">
        <ControlBtn icon={HiComputerDesktop} active={screenShareOn}
          onClick={toggleScreenShare}
          label={screenShareOn ? 'Stop sharing' : 'Share screen'}
        />
        <ControlBtn icon={micOn ? HiMicrophone : HiMicOff} active={micOn}
          onClick={toggleMic}
          label={micOn ? 'Mute microphone' : 'Unmute microphone'}
        />
        <ControlBtn icon={camOn ? HiVideoCamera : HiVideoCameraSlash} active={camOn}
          onClick={toggleCam}
          label={camOn ? 'Turn off camera' : 'Turn on camera'}
        />
        <ControlBtn icon={HiHandRaised} active={handRaised}
          onClick={toggleHandRaise}
          label={handRaised ? 'Lower hand' : 'Raise hand'}
        />
        <div style={{ position: 'relative' }}>
          <ControlBtn icon={HiFaceSmile} active={showEmojiPicker}
            onClick={() => setShowEmojiPicker(prev => !prev)}
            label="Send reaction"
          />
          {showEmojiPicker && (
            <div style={{ position: 'absolute', bottom: 54, left: '50%', transform: 'translateX(-50%)', display: 'flex', gap: 4, padding: '6px 10px', borderRadius: 99, background: 'rgba(30,30,50,0.96)', border: '1px solid rgba(255,255,255,0.1)', boxShadow: '0 8px 32px rgba(0,0,0,0.5)', zIndex: 50 }}>
              {EMOJIS.map(emoji => (
                <button key={emoji} onClick={() => sendEmoji(emoji)} style={{ fontSize: '1.3rem', background: 'transparent', border: 'none', cursor: 'pointer', padding: '4px 6px', borderRadius: 8, transition: 'all 0.12s', lineHeight: 1 }}
                  onMouseOver={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.1)'; e.currentTarget.style.transform = 'scale(1.3)'; }}
                  onMouseOut={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.transform = 'scale(1)'; }}
                >{emoji}</button>
              ))}
            </div>
          )}
        </div>
        <button className="ctrl-hangup" onClick={onLeave} title="Leave call">
          <HiPhoneXMark size={24} color="#fff" />
        </button>
        <ControlBtn icon={HiChatBubbleLeftRight} active={activePanel === 'chat'}
          onClick={() => togglePanel('chat')}
          label={activePanel === 'chat' ? 'Hide chat' : 'Show chat'}
        />
      </div>
    </footer>
  );
}

function ParticipantTracker({ onUpdate }) {
  const remoteParticipants = useRemoteParticipants();
  const { localParticipant } = useLocalParticipant();
  const callbackRef = useRef(onUpdate);
  callbackRef.current = onUpdate;
  useEffect(() => {
    const all = [];
    if (localParticipant) {
      all.push({
        identity: localParticipant.identity || 'local',
        name: formatParticipantName(localParticipant.name, localParticipant.identity, true),
        isLocal: true, micOn: localParticipant.isMicrophoneEnabled,
        camOn: localParticipant.isCameraEnabled, screenOn: localParticipant.isScreenShareEnabled,
      });
    }
    (remoteParticipants || []).forEach(p => {
      all.push({
        identity: p.identity || 'unknown',
        name: formatParticipantName(p.name, p.identity, false),
        isLocal: false, micOn: p.isMicrophoneEnabled,
        camOn: p.isCameraEnabled, screenOn: p.isScreenShareEnabled,
      });
    });
    callbackRef.current(all);
  }, [localParticipant, remoteParticipants]);
  return null;
}

function EmojiFly({ emojis }) {
  return (
    <>
      {emojis.map(e => (
        <div key={e.id} style={{
          position: 'absolute', top: e.y, left: e.x,
          fontSize: '2.5rem', pointerEvents: 'none', zIndex: 100,
          animation: 'emojiFloat 2s ease-out forwards',
        }}>{e.emoji}</div>
      ))}
      
    </>
  );
}

function SelfPreview() {
  const [expanded, setExpanded] = useState(false);
  const tracks = useTracks([{ source: Track.Source.Camera, withPlaceholder: true }]);
  const localTrack = tracks.find(track => track?.participant?.isLocal);

  return (
    <div className={`self-preview ${expanded ? 'is-expanded' : ''}`}>
      <div className="self-preview-badge">You</div>
      <button className="self-preview-expand" onClick={() => setExpanded(prev => !prev)}>
        {expanded ? 'Minimize' : 'Expand'}
      </button>
      <div className="self-preview-feed">
        {localTrack ? <ParticipantTile trackRef={localTrack} /> : (
          <div className="self-avatar">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>
          </div>
        )}
      </div>
    </div>
  );
}

function WaitingForOthers() {
  return (
    <div className="waiting-card">
      <div className="waiting-icon"><HiUserGroup size={40} color={COLOR.muted} /></div>
      <h3 className="waiting-title">Waiting for others to join</h3>
      <p className="waiting-sub">Share the room link to invite participants. This room is live.</p>
      
    </div>
  );
}

function getTrackKey(trackRef) {
  return `${trackRef?.participant?.identity || 'unknown'}:${trackRef?.source || 'camera'}`;
}

function VideoArea({ isSharing, isHandRaised }) {
  const tracks = useTracks([
    { source: Track.Source.Camera, withPlaceholder: true },
    { source: Track.Source.ScreenShare, withPlaceholder: false },
  ]);
  const roomTracks = tracks.filter(track => !track?.participant?.isLocal || track?.source === Track.Source.ScreenShare);
  const screenTracks = roomTracks.filter(track => track?.source === Track.Source.ScreenShare);
  const cameraTracks = roomTracks.filter(track => track?.source !== Track.Source.ScreenShare);
  const orderedTracks = [...screenTracks, ...cameraTracks];
  const [pinnedKey, setPinnedKey] = useState(null);
  const pinnedTrack = orderedTracks.find(track => getTrackKey(track) === pinnedKey) || screenTracks[0];
  const sideTracks = pinnedTrack ? orderedTracks.filter(track => getTrackKey(track) !== getTrackKey(pinnedTrack)) : orderedTracks;

  function renderTile(track, pinned = false) {
    const key = getTrackKey(track);
    return (
      <div className={`meet-video-tile ${pinned ? 'is-pinned' : ''}`} key={key}>
        <ParticipantTile trackRef={track} />
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', height: '100%' }}>
      {pinnedTrack ? (
        <div className="meet-focus-layout">
          <div className="meet-focus-main">
            {renderTile(pinnedTrack, true)}
            <button className="meet-focus-clear" onClick={() => setPinnedKey(null)}>Back to grid</button>
          </div>
          <div className="meet-focus-strip">
            {sideTracks.length > 0 ? sideTracks.map(track => renderTile(track)) : (!isSharing && <WaitingForOthers />)}
          </div>
        </div>
      ) : (
        <div className="meet-adaptive-grid">
          {orderedTracks.length > 0 ? orderedTracks.map(track => renderTile(track)) : (!isSharing && <WaitingForOthers />)}
        </div>
      )}
      {isSharing && (
        <div className="meet-room-notice meet-room-notice--share">
          <HiComputerDesktop size={16} /> Screen sharing is on
        </div>
      )}
      {isHandRaised && (
        <div className="meet-room-notice meet-room-notice--hand">
          <HiHandRaised size={16} /> Hand raised
        </div>
      )}
    </div>
  );
}

function ConnectingGate() {
  return (
    <div style={{ display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',minHeight:'60vh',gap:14,color:'#888' }}>
      <div style={{ width:36,height:36,border:'3px solid rgba(255,255,255,0.1)',borderTopColor:COLOR.accent,borderRadius:'50%',animation:'gs 0.7s linear infinite' }} />
      <p style={{ fontSize:14,margin:0 }}>Connecting to room...</p>
      
    </div>
  );
}

function getFriends() { try { return JSON.parse(localStorage.getItem('eroom-friends')||'[]'); } catch { return []; } }
function addFriend(identity, name) { const f=getFriends(); if(!f.find(x=>x.id===identity)){f.push({id:identity,name,addedAt:Date.now()});localStorage.setItem('eroom-friends',JSON.stringify(f));} }
function removeFriend(identity) { const f=getFriends().filter(x=>x.id!==identity); localStorage.setItem('eroom-friends',JSON.stringify(f)); }
function isFriend(identity) { return getFriends().some(x=>x.id===identity); }

function ParticipantsPanel({ participants, onClose }) {
  const friends = getFriends();
  return (
    <aside style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--color-bg-elevated)' }}>
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 16px', borderBottom: '1px solid rgba(255,255,255,0.06)', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <HiUserGroup size={18} style={{ color: 'var(--color-accent)' }} />
          <h3 style={{ fontFamily: "'Nunito',sans-serif", fontSize: 14, fontWeight: 700, color: 'var(--color-text-primary)', margin: 0 }}>Participants</h3>
          <span style={{ fontSize: 11, color: 'var(--color-text-muted)', background: 'var(--color-bg-surface)', padding: '2px 10px', borderRadius: 99, fontWeight: 600 }}>{participants?.length ?? 0}</span>
        </div>
        <button onClick={onClose} aria-label="Close" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: 30, height: 30, borderRadius: '50%', border: 'none', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', transition: 'all 0.15s' }}
          onMouseOver={e => { e.currentTarget.style.color = 'var(--color-danger)'; e.currentTarget.style.background = 'rgba(239,68,68,0.1)'; }}
          onMouseOut={e => { e.currentTarget.style.color = 'var(--color-text-muted)'; e.currentTarget.style.background = 'transparent'; }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
        </button>
      </header>
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 12px' }}>
        {participants.map((p, i) => {
          const alreadyFriend = isFriend(p.identity);
          return (
            <div key={p.identity || i} style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '10px 8px', borderRadius: 12, transition: 'background 0.15s',
            }}
              onMouseOver={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
              onMouseOut={e => { e.currentTarget.style.background = 'transparent'; }}
            >
              <div style={{
                width: 38, height: 38, borderRadius: '50%', flexShrink: 0,
                background: hashColor(p.name), color: '#fff',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 12, fontWeight: 800, position: 'relative',
              }}>
                {getInitials(p.name)}
                <div style={{
                  position: 'absolute', bottom: -1, right: -1,
                  width: 12, height: 12, borderRadius: '50%',
                  background: p.camOn ? 'var(--color-success)' : 'var(--color-text-muted)',
                  border: '2px solid var(--color-bg-elevated)',
                }} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)',
                  display: 'flex', alignItems: 'center', gap: 5,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {p.name}
                  {p.isLocal && <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 99, background: 'rgba(255,255,255,0.12)', color: 'var(--color-accent)', fontWeight: 600 }}>You</span>}
                </div>
                <div style={{ display: 'flex', gap: 10, marginTop: 3 }}>
                  <span style={{ fontSize: 10, display: 'flex', alignItems: 'center', gap: 3, color: p.micOn ? 'var(--color-success)' : 'var(--color-danger)' }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: p.micOn ? 'var(--color-success)' : 'var(--color-danger)' }} />
                    {p.micOn ? 'Mic on' : 'Muted'}
                  </span>
                  <span style={{ fontSize: 10, display: 'flex', alignItems: 'center', gap: 3, color: p.camOn ? 'var(--color-success)' : 'var(--color-danger)' }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: p.camOn ? 'var(--color-success)' : 'var(--color-danger)' }} />
                    {p.camOn ? 'Cam on' : 'Cam off'}
                  </span>
                </div>
              </div>
              {!p.isLocal && (
                alreadyFriend ? (
                  <button onClick={() => removeFriend(p.identity)}
                    style={{
                      padding: '5px 10px', borderRadius: 99, flexShrink: 0,
                      background: 'rgba(255,255,255,0.08)', color: '#ffffff',
                      border: '1px solid rgba(255,255,255,0.15)', cursor: 'pointer',
                      fontSize: 10, fontWeight: 700, fontFamily: 'inherit',
                      display: 'flex', alignItems: 'center', gap: 3, transition: 'all 0.15s',
                    }}
                    onMouseOver={e => { e.currentTarget.style.background = 'var(--color-danger-muted)'; e.currentTarget.style.color = 'var(--color-danger)'; e.currentTarget.style.borderColor = 'rgba(239,68,68,0.2)'; }}
                    onMouseOut={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; e.currentTarget.style.color = '#ffffff'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)'; }}
                  ><HiUser size={11} /> Friends</button>
                ) : (
                  <button onClick={() => addFriend(p.identity, p.name)}
                    style={{
                      padding: '5px 10px', borderRadius: 99, flexShrink: 0,
                      background: 'rgba(255,255,255,0.06)', color: '#ffffff',
                      border: '1px solid rgba(255,255,255,0.1)', cursor: 'pointer',
                      fontSize: 10, fontWeight: 700, fontFamily: 'inherit',
                      display: 'flex', alignItems: 'center', gap: 3, transition: 'all 0.15s',
                    }}
                    onMouseOver={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.12)'; }}
                    onMouseOut={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; }}
                  ><HiUserPlus size={11} /> Add Friend</button>
                ))}
            </div>
          );
        })}
      </div>
      {friends.length > 0 && (
        <div style={{ padding: '10px 16px', borderTop: '1px solid rgba(255,255,255,0.06)', flexShrink: 0 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--color-text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Friends ({friends.length})</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {friends.map(f => (
              <span key={f.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '3px 8px', borderRadius: 99, background: 'rgba(255,255,255,0.06)', color: '#ffffff', fontSize: 10, fontWeight: 600, border: '1px solid rgba(255,255,255,0.1)' }}>
                <div style={{ width: 14, height: 14, borderRadius: '50%', background: hashColor(f.name), display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 7, fontWeight: 800, color: '#fff' }}>{getInitials(f.name)}</div>
                {f.name}
              </span>
            ))}
          </div>
        </div>
      )}
    </aside>
  );
}

export function RoomPage() {
  const api = new ApiClient();
  const { roomId } = useParams();
  const navigate = useNavigate();
  const hasLeftRef = useRef(false);
  const [token, setToken] = useState('');
  const [livekitUrl, setLivekitUrl] = useState('');
  const [roomName, setRoomName] = useState('');
  const [error, setError] = useState('');
  const [phase, setPhase] = useState('loading');
  const [activePanel, setActivePanel] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const [screenShareOn, setScreenShareOn] = useState(false);
  const [handRaised, setHandRaised] = useState(false);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [savedElapsed, setSavedElapsed] = useState(0);
  const [participantsList, setParticipantsList] = useState([]);
  const [floatingEmojis, setFloatingEmojis] = useState([]);
  const [handRaiseNotifs, setHandRaiseNotifs] = useState([]);
  const wsRef = useRef(null);
  const [wsSocket, setWsSocket] = useState(null);
  const audioWsRef = useRef(null);
  const audioCaptureRef = useRef(null);
  const [wsParticipants, setWsParticipants] = useState(0);
  const [retrySignal, setRetrySignal] = useState(0);
  const joinedRef = useRef(false);

  const handleDisconnected = useCallback(() => {
    if (!hasLeftRef.current) {

      setError('Connection to room was lost. Please try again.');
      setPhase('error');
    } else {
      setPhase('left');
    }
  }, []);

  const handleRetry = useCallback(() => {
    setPhase('loading');
    setRetrySignal(s => s + 1);
  }, []);
  const handleLeave = useCallback(() => {
    hasLeftRef.current = true;
    api.post(`/rooms/${roomId}/leave`, {}).catch(() => {});
    setPhase('left');
  }, [roomId]);
  const goBack = useCallback(() => { navigate('/learning'); }, [navigate]);

  useEffect(() => {
    return () => {
      if (hasLeftRef.current) return;
      api.post(`/rooms/${roomId}/leave`, {}).catch(() => {});
    };
  }, [roomId]);

  useEffect(() => {
    if (phase !== 'connected') return;
    const iv = setInterval(() => setElapsed(prev => prev + 1), 1000);
    return () => clearInterval(iv);
  }, [phase]);

  useEffect(() => {
    if (floatingEmojis.length === 0) return;
    const timeout = setTimeout(() => {
      setFloatingEmojis(prev => prev.filter(e => Date.now() - e.id < 2000));
    }, 2000);
    return () => clearTimeout(timeout);
  }, [floatingEmojis]);

  useEffect(() => {
    const handler = (e) => {
      setHandRaiseNotifs(prev => {
        const exists = prev.some(n => n.identity === e.detail.identity);
        if (exists) return prev;
        return [...prev, { ...e.detail }].slice(-3);
      });
    };
    window.addEventListener('hand-raise-notif', handler);
    return () => window.removeEventListener('hand-raise-notif', handler);
  }, []);

  useEffect(() => {
    if (handRaiseNotifs.length === 0) return;
    const timeout = setTimeout(() => {
      setHandRaiseNotifs(prev => prev.filter(n => Date.now() - n.id < 6000));
    }, 6000);
    return () => clearTimeout(timeout);
  }, [handRaiseNotifs]);

  useEffect(() => {
    let cancelled = false;
    async function joinAndGetToken() {
      try {
        const roomData = await fetchJson(`/rooms/${roomId}`);
        if (cancelled) return;
        setRoomName(roomData?.topic || roomData?.name || roomData?.room_name || 'Room');
        if (!joinedRef.current) {
          await api.post(`/rooms/${roomId}/join`, {});
          joinedRef.current = true;
        }
        if (cancelled) return;
        const tokenResult = await api.post(`/rooms/${roomId}/token`);
        if (cancelled) return;

        const backendUrl = tokenResult.livekit_url || '';
        const lkUrl = backendUrl

          .replace(/ws:\/\/livekit:/, 'ws://localhost:')
          .replace(/ws:\/\/lk:/, 'ws://localhost:')
        const finalUrl = lkUrl || 'ws://localhost:7880';
        setToken(tokenResult.livekit_token);
        setLivekitUrl(finalUrl);
        setPhase('connected');
      } catch (err) {
        if (!cancelled) { setError(err.message); setPhase('error'); }
      }
    }
    joinAndGetToken();
    return () => { cancelled = true; };
  }, [roomId, retrySignal]);

  useEffect(() => {
    if (phase === 'left' && elapsed > 0) setSavedElapsed(elapsed);
  }, [phase, elapsed]);

  useEffect(() => {
    if (phase !== 'connected') return;
    const authToken = getTokens()?.access || '';
    const wsBase = API_BASE_URL.replace('http://', 'ws://').replace('/api/v1', '');

    const wsUrl = `${wsBase}/ws/rooms/${roomId}?token=${authToken}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    setWsSocket(ws);

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === 'system') {
          if (data.event === 'user_joined' || data.event === 'user_left') {
            setWsParticipants(data.participant_count || 0);
          }
        } else if (data.type === 'presence') {
          setWsParticipants(data.connections || 0);
        }
      } catch {}
    };

    return () => {
      ws.close();
      wsRef.current = null;
      setWsSocket(null);
    };
  }, [phase, roomId]);

  useEffect(() => {
    if (phase !== 'connected') {
      if (audioCaptureRef.current) {
        audioCaptureRef.current.stop();
        audioCaptureRef.current = null;
      }
      return;
    }
    const authToken = getTokens()?.access || '';
    if (!authToken) return;
    const capture = createAudioCapture(roomId, authToken, audioWsRef);
    audioCaptureRef.current = capture;
    capture.start();
    return () => {
      capture.stop();
      audioCaptureRef.current = null;
    };
  }, [phase, roomId]);

  const handleParticipantUpdate = useCallback((list) => {
    setParticipantsList(prev => {
      if (!Array.isArray(list)) return prev;
      if (prev.length !== list.length) return list;
      const same = prev.every((p, i) =>
        p.identity === list[i]?.identity &&
        p.micOn === list[i]?.micOn && p.camOn === list[i]?.camOn && p.screenOn === list[i]?.screenOn
      );
      return same ? prev : list;
    });
  }, []);

  function togglePanel(panel) { setActivePanel(prev => prev === panel ? null : panel); }
  function openParticipants() { setActivePanel(prev => prev === 'participants' ? null : 'participants'); }

  function sendEmoji(emoji) {
    setShowEmojiPicker(false);
    const id = Date.now();
    setFloatingEmojis(prev => [...prev, { id, emoji, x: 30 + Math.random() * 40 + '%', y: 30 + Math.random() * 30 + '%' }]);
  }

  if (phase === 'loading') {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--color-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <ConnectingGate />
      </div>
    );
  }

  if (phase === 'error') {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--color-bg)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 14, textAlign: 'center', padding: 20 }}>
        <HiShieldExclamation size={48} color={COLOR.danger} />
        <h2 style={{ fontFamily: 'Nunito, sans-serif', fontSize: 20, margin: 0, color: 'var(--color-text-primary)' }}>Failed to join room</h2>
        <p style={{ color: '#888', fontSize: 14, maxWidth: 400, margin: 0 }}>{error}</p>
        <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
          <button className="room-btn-sec" onClick={handleRetry}>Retry</button>
          <button className="room-btn-pri" onClick={goBack}>Back to Learning</button>
        </div>
        
      </div>
    );
  }

  if (phase === 'left') {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--color-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
        <div style={{ background: 'var(--color-bg-elevated)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 24, padding: '40px 32px', maxWidth: 440, width: '100%', textAlign: 'center', boxShadow: '0 20px 60px rgba(0,0,0,0.5)', animation: 'fadeInUp 0.4s ease both' }}>
          <div style={{ width: 72, height: 72, borderRadius: '50%', background: 'rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
            <HiCheckCircle size={36} color={COLOR.success} />
          </div>
          <h2 style={{ fontFamily: 'Nunito, sans-serif', fontWeight: 800, fontSize: '1.5rem', margin: '0 0 6px', color: 'var(--color-text-primary)' }}>You left the room</h2>
          <p style={{ color: '#888', fontSize: '0.9rem', margin: '0 0 24px', lineHeight: 1.5 }}>
            Thanks for participating in <strong style={{ color: 'var(--color-text-secondary)' }}>{roomName || 'the session'}</strong>!
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 32, padding: '16px 0', marginBottom: 24, borderTop: '1px solid rgba(255,255,255,0.06)', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--color-text-primary)', fontFamily: 'Nunito, sans-serif' }}>{formatTime(savedElapsed || elapsed)}</div>
              <div style={{ fontSize: '0.7rem', color: '#888', marginTop: 2 }}>Duration</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--color-text-primary)', fontFamily: 'Nunito, sans-serif' }}>{participantsList.length || 1}</div>
              <div style={{ fontSize: '0.7rem', color: '#888', marginTop: 2 }}>Participants</div>
            </div>
          </div>
          <button onClick={goBack} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '12px 28px', borderRadius: 99, background: 'var(--color-accent-gradient)', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: 700, fontSize: '0.9rem', fontFamily: 'inherit', boxShadow: '0 4px 20px var(--color-accent-glow)', transition: 'all 0.2s' }}
            onMouseOver={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.filter = 'brightness(1.1)'; }}
            onMouseOut={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.filter = 'brightness(1)'; }}
          >Back to Learning <HiArrowRight size={16} /></button>
        </div>
        
      </div>
    );
  }

  const showSidebar = activePanel === 'chat' || activePanel === 'participants';
  const participantCount = participantsList.length || 1;

  return (
    <div className="meet-root">

      <header className="meet-topbar">
        <div className="meet-topbar-left">
          <button className="meet-back" onClick={goBack} title="Back"><HiArrowLeft size={20} /></button>
          <div className="meet-room-info">
            <h1 className="meet-room-name">{roomName || 'Room'}</h1>
            <div className="meet-room-meta">
              <span className="meet-badge-live">● LIVE</span>
              <span className="meet-timer"><HiClock size={13} />{formatTime(elapsed)}</span>
            </div>
          </div>
        </div>
        <div className="meet-topbar-right">
          {handRaised && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '4px 10px', borderRadius: 99, background: 'rgba(251,191,36,0.15)', color: 'var(--color-warning)', fontSize: 11, fontWeight: 700, animation: 'pulse 1.5s ease-in-out infinite' }}>✋ Raised</span>
          )}
          <button className={`meet-participant-count ${activePanel==='participants'?'active':''}`} onClick={openParticipants} title="View participants"
            style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px', borderRadius: 99, background: activePanel==='participants'?'rgba(255,255,255,0.12)':'rgba(255,255,255,0.06)', border: 'none', cursor: 'pointer', fontSize: 12, color: activePanel==='participants'?COLOR.accent:COLOR.muted, fontFamily: 'inherit', transition: 'all 0.15s' }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>
            <span>{participantCount}</span>
          </button>
          <button className={`meet-chat-toggle ${activePanel==='chat'?'active':''}`} onClick={()=>togglePanel('chat')} title={activePanel==='chat'?'Hide chat':'Show chat'}>
            <HiChatBubbleLeftRight size={18} />
          </button>
        </div>
      </header>

      <div className="meet-main">
        <div className={`meet-video ${showSidebar ? 'with-chat' : 'full'}`}>
          <LiveKitRoom token={token} serverUrl={livekitUrl} video={true} audio={true} onDisconnected={handleDisconnected}
            style={{ width: '100%', height: '100%' }} data-lk-theme="default">
            <MeetControls onLeave={handleLeave} togglePanel={togglePanel} activePanel={activePanel}
              handRaised={handRaised} setHandRaised={setHandRaised}
              showEmojiPicker={showEmojiPicker} setShowEmojiPicker={setShowEmojiPicker}
              sendEmoji={sendEmoji} screenShareOn={screenShareOn} setScreenShareOn={setScreenShareOn} />
            <ParticipantTracker onUpdate={handleParticipantUpdate} />
            <EmojiFly emojis={floatingEmojis} />
            <VideoArea isSharing={screenShareOn} isHandRaised={handRaised} />
            <SelfPreview />
          </LiveKitRoom>
        </div>

        {activePanel === 'chat' && (
          <aside className="meet-chat-panel"><ChatWindow
            roomId={roomId}
            visible={true}
            onToggle={() => setActivePanel(null)}
            wsSocket={wsSocket}
          /></aside>
        )}
        {activePanel === 'participants' && (
          <aside className="meet-chat-panel"><ParticipantsPanel participants={participantsList} onClose={() => setActivePanel(null)} /></aside>
        )}
      </div>

      {handRaiseNotifs.map((n, i) => (
        <div key={n.id} style={{
          position: 'fixed', top: SIZES.topbar + 16 + (i * 52), right: 20,
          padding: '10px 16px', borderRadius: 12, zIndex: 200,
          background: 'rgba(251,191,36,0.15)', border: '1px solid rgba(251,191,36,0.3)',
          color: 'var(--color-warning)', fontSize: 13, fontWeight: 700,
          display: 'flex', alignItems: 'center', gap: 8,
          animation: 'slideIn 0.3s ease both, fadeOut 0.3s ease 5s forwards',
          pointerEvents: 'none',
        }}>
          ✋ {n.name || 'Someone'} raised hand!
        </div>
      ))}

      
    </div>
  );
}
