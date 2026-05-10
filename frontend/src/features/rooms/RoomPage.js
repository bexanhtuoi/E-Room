import { useEffect, useState, useCallback, useRef, forwardRef, useImperativeHandle } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { LiveKitRoom, GridLayout, useLocalParticipant, useRemoteParticipants, useRoomContext } from '@livekit/components-react';
import '@livekit/components-styles';
import { fetchJson, getTokens } from '../../lib/api';
import { ChatBox } from '../../components/ui/ChatBox';
import { useAuth } from '../../app/AuthContext';
import {
  HiArrowLeft, HiMicrophone, HiVideoCamera, HiVideoCameraSlash,
  HiMicrophone as HiMicOff, HiPhoneXMark, HiChatBubbleLeftRight,
  HiUserGroup, HiShieldExclamation, HiClock, HiCheckCircle, HiArrowRight,
  HiHandRaised, HiFaceSmile, HiComputerDesktop,
  HiUserPlus, HiUser,
} from 'react-icons/hi2';

/* ── Helpers ── */
const SIZES = { topbar: 56, controls: 68 };
const COLOR = {
  danger: 'var(--color-danger)',
  muted: 'var(--color-text-muted)',
  accent: 'var(--color-accent)',
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
};
const EMOJIS = ['👋', '👍', '❤️', '😂', '🔥', '👏', '🎉', '💯', '✨', '🙌'];

function getUserIdFromToken() {
  try {
    const { access } = getTokens();
    if (!access) return null;
    const payload = JSON.parse(atob(access.split('.')[1]));
    return payload.sub || payload.user_id || null;
  } catch { return null; }
}

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
  const PALETTE = ['#6366f1','#8b5cf6','#ec4899','#f59e0b','#10b981','#06b6d4','#f43f5e','#84cc16'];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return PALETTE[Math.abs(hash) % PALETTE.length];
}

/* ── Control Button ── */
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

/* ── MeetControls — lives inside LiveKitRoom for direct localParticipant access ── */
function MeetControls({ onLeave, togglePanel, activePanel, handRaised, setHandRaised,
  showEmojiPicker, setShowEmojiPicker, sendEmoji, screenShareOn, setScreenShareOn }) {
  const { localParticipant } = useLocalParticipant();
  const room = useRoomContext();
  const [micOn, setMicOn] = useState(true);
  const [camOn, setCamOn] = useState(true);

  // Sync with actual LiveKit participant state
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
      await localParticipant.setMicrophoneEnabled(!localParticipant.isMicrophoneEnabled);
    } catch (e) { console.warn('toggleMic:', e); }
    setMicOn(p => !p);
  }, [localParticipant]);

  const toggleCam = useCallback(async () => {
    if (!localParticipant) { setCamOn(p => !p); return; }
    try {
      await localParticipant.setCameraEnabled(!localParticipant.isCameraEnabled);
    } catch (e) { console.warn('toggleCam:', e); }
    setCamOn(p => !p);
  }, [localParticipant]);

  const toggleScreenShare = useCallback(() => {
    if (!localParticipant) { setScreenShareOn(p => !p); return; }
    localParticipant.setScreenShareEnabled(!localParticipant.isScreenShareEnabled)
      .then(() => setScreenShareOn(p => !p))
      .catch(e => { console.warn('toggleScreenShare:', e); setScreenShareOn(p => !p); });
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

/* ── ParticipantTracker ── */
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

/* ── Emoji Fly ── */
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
      <style>{`
        @keyframes emojiFloat {
          0% { opacity: 1; transform: translateY(0) scale(1); }
          50% { opacity: 1; transform: translateY(-60px) scale(1.3); }
          100% { opacity: 0; transform: translateY(-140px) scale(0.8); }
        }
      `}</style>
    </>
  );
}

/* ── Self Preview ── */
function SelfPreview() {
  return (
    <div className="self-preview">
      <div className="self-preview-badge">You</div>
      <div className="self-preview-feed"><div className="self-avatar">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>
      </div></div>
      <style>{`
        .self-preview{position:absolute;bottom:${SIZES.controls+20}px;right:20px;width:200px;aspect-ratio:16/10;z-index:20;border-radius:12px;overflow:hidden;background:#1e1e30;border:2px solid rgba(255,255,255,0.12);box-shadow:0 4px 20px rgba(0,0,0,0.5);transition:all 0.3s ease}
        @media(max-width:640px){.self-preview{width:120px;bottom:${SIZES.controls+10}px;right:10px}}
        .self-preview:hover{border-color:${COLOR.accent};transform:scale(1.02)}
        .self-preview-badge{position:absolute;top:6px;left:6px;z-index:5;background:rgba(0,0,0,0.55);color:#fff;font-size:10px;font-weight:700;padding:2px 8px;border-radius:99px;backdrop-filter:blur(6px)}
        .self-preview-feed{width:100%;height:100%;display:flex;align-items:center;justify-content:center}
        .self-avatar{width:56px;height:56px;border-radius:50%;background:rgba(255,255,255,0.06);display:flex;align-items:center;justify-content:center;color:${COLOR.muted}}
      `}</style>
    </div>
  );
}

/* ── Waiting ── */
function WaitingForOthers() {
  return (
    <div className="waiting-card">
      <div className="waiting-icon"><HiUserGroup size={40} color={COLOR.muted} /></div>
      <h3 className="waiting-title">Waiting for others to join</h3>
      <p className="waiting-sub">Share the room link to invite participants. This room is live.</p>
      <style>{`
        .waiting-card{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:10px;padding:20px;z-index:10;background:radial-gradient(ellipse at center,rgba(255,255,255,0.02)0%,transparent 70%)}
        .waiting-icon{width:80px;height:80px;border-radius:50%;background:rgba(255,255,255,0.04);border:2px dashed rgba(255,255,255,0.1);display:flex;align-items:center;justify-content:center;margin-bottom:8px}
        .waiting-title{font-family:var(--font-display);font-size:1.3rem;font-weight:700;color:var(--color-text-primary);margin:0}
        .waiting-sub{color:var(--color-text-muted);font-size:0.85rem;max-width:320px;margin:0;line-height:1.5}
      `}</style>
    </div>
  );
}

/* ── Video area ── */
function VideoArea({ isSharing, isHandRaised }) {
  const remoteParticipants = useRemoteParticipants();
  const hasRemote = Array.isArray(remoteParticipants) && remoteParticipants.length > 0;

  if (!hasRemote && !isSharing) return <WaitingForOthers />;

  return (
    <div style={{ position: 'relative', height: '100%' }}>
      <GridLayout />
      {isSharing && (
        <div style={{ position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)', padding: '6px 16px', borderRadius: 99, background: 'rgba(99,102,241,0.9)', color: '#fff', fontSize: 12, fontWeight: 700, zIndex: 30, pointerEvents: 'none' }}>
          🖥️ Sharing screen
        </div>
      )}
      {isHandRaised && (
        <div style={{ position: 'absolute', bottom: 80, left: '50%', transform: 'translateX(-50%)', padding: '8px 18px', borderRadius: 99, background: 'rgba(251,191,36,0.9)', color: '#1a1a2e', fontSize: 13, fontWeight: 700, zIndex: 30, animation: 'pulse 1.5s ease-in-out infinite', pointerEvents: 'none' }}>
          ✋ Hand raised
        </div>
      )}
    </div>
  );
}

/* ── Connecting ── */
function ConnectingGate() {
  return (
    <div style={{ display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',minHeight:'60vh',gap:14,color:'#888' }}>
      <div style={{ width:36,height:36,border:'3px solid rgba(255,255,255,0.1)',borderTopColor:COLOR.accent,borderRadius:'50%',animation:'gs 0.7s linear infinite' }} />
      <p style={{ fontSize:14,margin:0 }}>Connecting to room...</p>
      <style>{`@keyframes gs{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}

/* ── Friends helpers (localStorage) ── */
function getFriends() { try { return JSON.parse(localStorage.getItem('eroom-friends')||'[]'); } catch { return []; } }
function addFriend(identity, name) { const f=getFriends(); if(!f.find(x=>x.id===identity)){f.push({id:identity,name,addedAt:Date.now()});localStorage.setItem('eroom-friends',JSON.stringify(f));} }
function removeFriend(identity) { const f=getFriends().filter(x=>x.id!==identity); localStorage.setItem('eroom-friends',JSON.stringify(f)); }
function isFriend(identity) { return getFriends().some(x=>x.id===identity); }

/* ── Participants Panel ── */
function ParticipantsPanel({ participants, onClose }) {
  const friends = getFriends();
  return (
    <aside style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#13131f' }}>
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 16px', borderBottom: '1px solid rgba(255,255,255,0.06)', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <HiUserGroup size={18} style={{ color: '#818cf8' }} />
          <h3 style={{ fontFamily: "'Nunito',sans-serif", fontSize: 14, fontWeight: 700, color: '#e8e8f0', margin: 0 }}>Participants</h3>
          <span style={{ fontSize: 11, color: '#666', background: '#1a1a2e', padding: '2px 10px', borderRadius: 99, fontWeight: 600 }}>{participants?.length ?? 0}</span>
        </div>
        <button onClick={onClose} aria-label="Close" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: 30, height: 30, borderRadius: '50%', border: 'none', background: 'transparent', color: '#666', cursor: 'pointer', transition: 'all 0.15s' }}
          onMouseOver={e => { e.currentTarget.style.color = '#ef4444'; e.currentTarget.style.background = 'rgba(239,68,68,0.1)'; }}
          onMouseOut={e => { e.currentTarget.style.color = '#666'; e.currentTarget.style.background = 'transparent'; }}
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
                  background: p.camOn ? '#34d399' : '#6b7280',
                  border: '2px solid #13131f',
                }} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: 13, fontWeight: 700, color: '#e8e8f0',
                  display: 'flex', alignItems: 'center', gap: 5,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {p.name}
                  {p.isLocal && <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 99, background: 'rgba(99,102,241,0.2)', color: '#818cf8', fontWeight: 600 }}>You</span>}
                </div>
                <div style={{ display: 'flex', gap: 10, marginTop: 3 }}>
                  <span style={{ fontSize: 10, display: 'flex', alignItems: 'center', gap: 3, color: p.micOn ? '#34d399' : '#ef4444' }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: p.micOn ? '#34d399' : '#ef4444' }} />
                    {p.micOn ? 'Mic on' : 'Muted'}
                  </span>
                  <span style={{ fontSize: 10, display: 'flex', alignItems: 'center', gap: 3, color: p.camOn ? '#34d399' : '#ef4444' }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: p.camOn ? '#34d399' : '#ef4444' }} />
                    {p.camOn ? 'Cam on' : 'Cam off'}
                  </span>
                </div>
              </div>
              {!p.isLocal && (
                alreadyFriend ? (
                  <button onClick={() => removeFriend(p.identity)}
                    style={{
                      padding: '5px 10px', borderRadius: 99, flexShrink: 0,
                      background: 'rgba(52,211,153,0.12)', color: '#34d399',
                      border: '1px solid rgba(52,211,153,0.2)', cursor: 'pointer',
                      fontSize: 10, fontWeight: 700, fontFamily: 'inherit',
                      display: 'flex', alignItems: 'center', gap: 3, transition: 'all 0.15s',
                    }}
                    onMouseOver={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.15)'; e.currentTarget.style.color = '#ef4444'; e.currentTarget.style.borderColor = 'rgba(239,68,68,0.2)'; }}
                    onMouseOut={e => { e.currentTarget.style.background = 'rgba(52,211,153,0.12)'; e.currentTarget.style.color = '#34d399'; e.currentTarget.style.borderColor = 'rgba(52,211,153,0.2)'; }}
                  ><HiUser size={11} /> Friends</button>
                ) : (
                  <button onClick={() => addFriend(p.identity, p.name)}
                    style={{
                      padding: '5px 10px', borderRadius: 99, flexShrink: 0,
                      background: 'rgba(99,102,241,0.12)', color: '#818cf8',
                      border: '1px solid rgba(99,102,241,0.2)', cursor: 'pointer',
                      fontSize: 10, fontWeight: 700, fontFamily: 'inherit',
                      display: 'flex', alignItems: 'center', gap: 3, transition: 'all 0.15s',
                    }}
                    onMouseOver={e => { e.currentTarget.style.background = 'rgba(99,102,241,0.25)'; }}
                    onMouseOut={e => { e.currentTarget.style.background = 'rgba(99,102,241,0.12)'; }}
                  ><HiUserPlus size={11} /> Add Friend</button>
                )
              )}
            </div>
          );
        })}
      </div>
      {friends.length > 0 && (
        <div style={{ padding: '10px 16px', borderTop: '1px solid rgba(255,255,255,0.06)', flexShrink: 0 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#666', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Friends ({friends.length})</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {friends.map(f => (
              <span key={f.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '3px 8px', borderRadius: 99, background: 'rgba(52,211,153,0.1)', color: '#34d399', fontSize: 10, fontWeight: 600, border: '1px solid rgba(52,211,153,0.15)' }}>
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

/* ═══════════════════════════════════════════════════════════
   RoomPage
   ═══════════════════════════════════════════════════════════ */
export function RoomPage() {
  const { roomId } = useParams();
  const navigate = useNavigate();
  const hasLeftRef = useRef(false);
  const getUserId = useCallback(getUserIdFromToken, []);

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

  const handleDisconnected = useCallback(() => { setPhase('left'); }, []);
  const handleLeave = useCallback(() => {
    hasLeftRef.current = true;
    const userId = getUserId();
    fetchJson(`/rooms/${roomId}/leave`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId }),
    }).catch(() => {});
    setPhase('left');
  }, [roomId, getUserId]);
  const goBack = useCallback(() => { navigate('/learning'); }, [navigate]);

  /* Leave cleanup — ensures /leave is called even on browser back / unmount */
  useEffect(() => {
    return () => {
      if (hasLeftRef.current) return;
      const userId = getUserId();
      fetchJson(`/rooms/${roomId}/leave`, {
        method: 'POST',
        body: JSON.stringify({ user_id: userId }),
      }).catch(() => {});
    };
  }, [roomId, getUserId]);

  /* Timer */
  useEffect(() => {
    if (phase !== 'connected') return;
    const iv = setInterval(() => setElapsed(prev => prev + 1), 1000);
    return () => clearInterval(iv);
  }, [phase]);

  /* Clean up floating emojis */
  useEffect(() => {
    if (floatingEmojis.length === 0) return;
    const timeout = setTimeout(() => {
      setFloatingEmojis(prev => prev.filter(e => Date.now() - e.id < 2000));
    }, 2000);
    return () => clearTimeout(timeout);
  }, [floatingEmojis]);

  /* Hand raise notification listener */
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

  /* Clean up old hand raise notifications */
  useEffect(() => {
    if (handRaiseNotifs.length === 0) return;
    const timeout = setTimeout(() => {
      setHandRaiseNotifs(prev => prev.filter(n => Date.now() - n.id < 6000));
    }, 6000);
    return () => clearTimeout(timeout);
  }, [handRaiseNotifs]);

  /* Join room */
  useEffect(() => {
    let cancelled = false;
    async function joinAndGetToken() {
      try {
        const userId = getUserId();
        const roomData = await fetchJson(`/rooms/${roomId}`);
        if (cancelled) return;
        setRoomName(roomData?.topic || roomData?.name || roomData?.room_name || 'Room');
        await fetchJson(`/rooms/${roomId}/join`, {
          method: 'POST',
          body: JSON.stringify({ user_id: userId }),
        });
        if (cancelled) return;
        const tokenResult = await fetchJson(`/rooms/${roomId}/token`, { method: 'POST' });
        if (cancelled) return;
        const rawUrl = (tokenResult.livekit_url || 'ws://localhost:7880')
          .replace('ws://livekit:', 'ws://localhost:');
        setToken(tokenResult.livekit_token);
        setLivekitUrl(rawUrl);
        setPhase('connected');
      } catch (err) {
        if (!cancelled) { setError(err.message); setPhase('error'); }
      }
    }
    joinAndGetToken();
    return () => { cancelled = true; };
  }, [roomId, getUserId]);

  useEffect(() => {
    if (phase === 'left' && elapsed > 0) setSavedElapsed(elapsed);
  }, [phase, elapsed]);

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

  /* ── Loading ── */
  if (phase === 'loading') {
    return (
      <div style={{ minHeight: '100vh', background: '#0a0a12', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <ConnectingGate />
      </div>
    );
  }

  /* ── Error ── */
  if (phase === 'error') {
    return (
      <div style={{ minHeight: '100vh', background: '#0a0a12', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 14, textAlign: 'center', padding: 20 }}>
        <HiShieldExclamation size={48} color={COLOR.danger} />
        <h2 style={{ fontFamily: 'Nunito, sans-serif', fontSize: 20, margin: 0, color: '#e8e8f0' }}>Failed to join room</h2>
        <p style={{ color: '#888', fontSize: 14, maxWidth: 400, margin: 0 }}>{error}</p>
        <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
          <button className="room-btn-sec" onClick={() => window.location.reload()}>Retry</button>
          <button className="room-btn-pri" onClick={goBack}>Back to Learning</button>
        </div>
        <style>{`
          .room-btn-pri{padding:10px 20px;border-radius:99px;background:var(--color-accent-gradient);color:#fff;font-weight:600;font-size:13px;border:none;cursor:pointer}
          .room-btn-sec{padding:10px 20px;border-radius:99px;background:rgba(255,255,255,0.06);color:#e8e8f0;font-weight:500;font-size:13px;border:1px solid rgba(255,255,255,0.1);cursor:pointer}
          .room-btn-pri:hover{filter:brightness(1.1)}.room-btn-sec:hover{background:rgba(255,255,255,0.12)}
        `}</style>
      </div>
    );
  }

  /* ── Left ── */
  if (phase === 'left') {
    return (
      <div style={{ minHeight: '100vh', background: '#0a0a12', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
        <div style={{ background: 'linear-gradient(145deg,#12121e 0%,#0d0d1a 100%)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 24, padding: '40px 32px', maxWidth: 440, width: '100%', textAlign: 'center', boxShadow: '0 20px 60px rgba(0,0,0,0.5)', animation: 'fadeInUp 0.4s ease both' }}>
          <div style={{ width: 72, height: 72, borderRadius: '50%', background: 'linear-gradient(135deg,rgba(99,102,241,0.15),rgba(139,92,246,0.1))', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
            <HiCheckCircle size={36} color={COLOR.success} />
          </div>
          <h2 style={{ fontFamily: 'Nunito, sans-serif', fontWeight: 800, fontSize: '1.5rem', margin: '0 0 6px', color: '#e8e8f0' }}>You left the room</h2>
          <p style={{ color: '#888', fontSize: '0.9rem', margin: '0 0 24px', lineHeight: 1.5 }}>
            Thanks for participating in <strong style={{ color: '#c4c4d0' }}>{roomName || 'the session'}</strong>!
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 32, padding: '16px 0', marginBottom: 24, borderTop: '1px solid rgba(255,255,255,0.06)', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#e8e8f0', fontFamily: 'Nunito, sans-serif' }}>{formatTime(savedElapsed || elapsed)}</div>
              <div style={{ fontSize: '0.7rem', color: '#888', marginTop: 2 }}>Duration</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#e8e8f0', fontFamily: 'Nunito, sans-serif' }}>{participantsList.length || 1}</div>
              <div style={{ fontSize: '0.7rem', color: '#888', marginTop: 2 }}>Participants</div>
            </div>
          </div>
          <button onClick={goBack} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '12px 28px', borderRadius: 99, background: 'var(--color-accent-gradient)', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: 700, fontSize: '0.9rem', fontFamily: 'inherit', boxShadow: '0 4px 20px var(--color-accent-glow)', transition: 'all 0.2s' }}
            onMouseOver={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.filter = 'brightness(1.1)'; }}
            onMouseOut={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.filter = 'brightness(1)'; }}
          >Back to Learning <HiArrowRight size={16} /></button>
        </div>
        <style>{`@keyframes fadeInUp{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:translateY(0)}}`}</style>
      </div>
    );
  }

  const showSidebar = activePanel === 'chat' || activePanel === 'participants';
  const participantCount = participantsList.length || 1;

  /* ════════════════ Connected ════════════════ */
  return (
    <div className="meet-root">
      {/* ── Top Bar ── */}
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
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '4px 10px', borderRadius: 99, background: 'rgba(251,191,36,0.15)', color: '#fbbf24', fontSize: 11, fontWeight: 700, animation: 'pulse 1.5s ease-in-out infinite' }}>✋ Raised</span>
          )}
          <button className={`meet-participant-count ${activePanel==='participants'?'active':''}`} onClick={openParticipants} title="View participants"
            style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px', borderRadius: 99, background: activePanel==='participants'?'rgba(99,102,241,0.15)':'rgba(255,255,255,0.06)', border: 'none', cursor: 'pointer', fontSize: 12, color: activePanel==='participants'?COLOR.accent:COLOR.muted, fontFamily: 'inherit', transition: 'all 0.15s' }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>
            <span>{participantCount}</span>
          </button>
          <button className={`meet-chat-toggle ${activePanel==='chat'?'active':''}`} onClick={()=>togglePanel('chat')} title={activePanel==='chat'?'Hide chat':'Show chat'}>
            <HiChatBubbleLeftRight size={18} />
          </button>
        </div>
      </header>

      {/* ── Main ── */}
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
          <aside className="meet-chat-panel"><ChatBox roomId={roomId} visible={true} onToggle={() => setActivePanel(null)} /></aside>
        )}
        {activePanel === 'participants' && (
          <aside className="meet-chat-panel"><ParticipantsPanel participants={participantsList} onClose={() => setActivePanel(null)} /></aside>
        )}
      </div>

      {/* ── Hand raise notifications ── */}
      {handRaiseNotifs.map((n, i) => (
        <div key={n.id} style={{
          position: 'fixed', top: SIZES.topbar + 16 + (i * 52), right: 20,
          padding: '10px 16px', borderRadius: 12, zIndex: 200,
          background: 'rgba(251,191,36,0.15)', border: '1px solid rgba(251,191,36,0.3)',
          color: '#fbbf24', fontSize: 13, fontWeight: 700,
          display: 'flex', alignItems: 'center', gap: 8,
          animation: 'slideIn 0.3s ease both, fadeOut 0.3s ease 5s forwards',
          pointerEvents: 'none',
        }}>
          ✋ {n.name || 'Someone'} raised hand!
        </div>
      ))}

      {/* ═══ Styles ═══ */}
      <style>{`
        .meet-root{display:flex;flex-direction:column;height:100vh;width:100vw;background:#0a0a12;overflow:hidden;font-family:'Nunito',-apple-system,BlinkMacSystemFont,sans-serif;color:#e0e0e0}
        .meet-root,.meet-root *{scrollbar-width:none;-ms-overflow-style:none}
        .meet-root::-webkit-scrollbar,.meet-root *::-webkit-scrollbar{display:none;width:0;height:0}
        .meet-topbar{display:flex;align-items:center;justify-content:space-between;height:${SIZES.topbar}px;min-height:${SIZES.topbar}px;padding:0 16px;background:rgba(16,16,28,0.92);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);border-bottom:1px solid rgba(255,255,255,0.06);z-index:30}
        .meet-topbar-left{display:flex;align-items:center;gap:12px}
        .meet-back{display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:50%;color:#aaa;border:none;background:transparent;cursor:pointer;transition:all 0.15s ease}
        .meet-back:hover{color:#fff;background:rgba(255,255,255,0.08)}
        .meet-room-info{display:flex;flex-direction:column;gap:1px}
        .meet-room-name{font-family:'Nunito',sans-serif;font-size:15px;font-weight:700;color:#e8e8f0;margin:0;line-height:1.2;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .meet-room-meta{display:flex;align-items:center;gap:10px}
        .meet-badge-live{font-size:10px;font-weight:700;letter-spacing:0.08em;color:${COLOR.success};text-transform:uppercase}
        .meet-timer{display:flex;align-items:center;gap:4px;font-size:11px;color:${COLOR.muted};font-variant-numeric:tabular-nums}
        .meet-topbar-right{display:flex;align-items:center;gap:8px}
        .meet-participant-count{transition:all 0.15s ease}
        .meet-participant-count:hover{background:rgba(255,255,255,0.12)!important}
        .meet-chat-toggle{display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:50%;color:${COLOR.muted};border:none;background:transparent;cursor:pointer;transition:all 0.15s ease}
        .meet-chat-toggle:hover,.meet-chat-toggle.active{color:${COLOR.accent};background:rgba(255,255,255,0.06)}
        .meet-main{display:flex;flex:1;overflow:hidden}
        .meet-video{flex:1;position:relative;background:#09090f;transition:all 0.3s ease;padding-bottom:${SIZES.controls}px}
        .meet-video.with-chat{flex:1}
        .meet-video.full{flex:1}
        .meet-chat-panel{flex:0 0 320px;min-width:280px;max-width:380px;display:flex;flex-direction:column;border-left:1px solid rgba(255,255,255,0.04);background:#13131f;animation:slideIn 0.2s ease both;padding-bottom:${SIZES.controls}px}
        @keyframes slideIn{from{opacity:0;transform:translateX(16px)}to{opacity:1;transform:translateX(0)}}

        /* ── Controls — fixed @ bottom like Google Meet ── */
        .meet-controls{position:fixed;bottom:0;left:0;right:0;display:flex;align-items:center;justify-content:center;height:${SIZES.controls}px;padding:0 16px;background:rgba(16,16,28,0.92);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);border-top:1px solid rgba(255,255,255,0.06);z-index:100}
        .meet-controls-center{display:flex;align-items:center;gap:8px}
        .ctrl-btn{display:flex;align-items:center;justify-content:center;width:44px;height:44px;border-radius:50%;background:rgba(255,255,255,0.08);color:#e0e0e0;border:none;cursor:pointer;transition:all 0.18s ease;position:relative}
        .ctrl-btn:hover{background:rgba(255,255,255,0.16);transform:scale(1.06)}
        .ctrl-btn--active{background:${COLOR.accent};color:#fff}
        .ctrl-btn--active:hover{background:${COLOR.accent}}
        .ctrl-btn--danger{background:${COLOR.danger};color:#fff}
        .ctrl-btn--danger:hover{background:var(--color-danger-hover);transform:scale(1.06)}
        .ctrl-hangup{display:flex;align-items:center;justify-content:center;width:50px;height:50px;border-radius:50%;background:${COLOR.danger};color:#fff;border:none;cursor:pointer;transition:all 0.18s ease}
        .ctrl-hangup:hover{background:var(--color-danger-hover);transform:scale(1.08);box-shadow:0 0 20px rgba(239,68,68,0.3)}

        /* ── Dark theme for sidebar ── */
        .meet-chat-panel .chatbox-v2{background:#13131f!important}
        .meet-chat-panel .chat-v2-header{border-bottom-color:rgba(255,255,255,0.06);padding:14px 16px}
        .meet-chat-panel .chat-v2-messages .chat-v2-bubble:not(.mine){background:#1a1a2e}
        .meet-chat-panel .chat-v2-messages .chat-v2-empty-icon{background:#1a1a2e;color:#555}
        .meet-chat-panel .chat-v2-messages .chat-v2-empty-title{color:#e8e8f0}
        .meet-chat-panel .chat-v2-messages .chat-v2-empty-sub{color:#666}
        .meet-chat-panel .chat-v2-input-wrapper{background:#1a1a2e;border-color:rgba(255,255,255,0.06)}
        .meet-chat-panel .chat-v2-input-wrapper:focus-within{border-color:#6366f1}
        .meet-chat-panel .chat-v2-input-field{color:#e8e8f0}
        .meet-chat-panel .chat-v2-input-field::placeholder{color:#555}
        .meet-chat-panel .chat-v2-send{background:#232340;color:#555}
        .meet-chat-panel .chat-v2-send.active{background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff}
        .meet-chat-panel .chat-v2-header-dot{box-shadow:0 0 6px #34d399}
        .meet-chat-panel .chat-v2-title{color:#e8e8f0}
        .meet-chat-panel .chat-v2-count{background:#1a1a2e;color:#666}
        .meet-chat-panel .chat-v2-time{color:#555}
        .meet-chat-panel .chat-v2-typing{color:#555}

        .lk-grid-layout{height:100%!important}
        .lk-grid-layout{padding-bottom:${SIZES.controls}px}

        @media(max-width:860px){.meet-video.with-chat{flex:0 0 55%}.meet-chat-panel{width:45%;min-width:0;max-width:none}}
        @media(max-width:500px){.meet-video.with-chat{display:none}.meet-chat-panel{width:100%!important;max-width:none}.meet-room-name{font-size:13px;max-width:120px}.meet-topbar{padding:0 10px}.ctrl-hangup{width:42px;height:42px}}
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.6}}
        @keyframes fadeOut{from{opacity:1;transform:translateX(0)}to{opacity:0;transform:translateX(16px)}}
      `}</style>
    </div>
  );
}
