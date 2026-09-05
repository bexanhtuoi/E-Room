import { useEffect, useState, useCallback, useRef, useReducer } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { LiveKitRoom, ParticipantTile, useLocalParticipant, useRemoteParticipants, useRoomContext, useTracks, AudioTrack } from '@livekit/components-react';
import '@livekit/components-styles';
import { Track } from 'livekit-client';
import { fetchJson, ApiClient } from '../../lib/api';
import { ChatWindow, RoomDataBridge } from '../chat/ChatWindow';
import { useRoomChat } from '../chat/useRoomChat';
import { MAX_TOPICS, TopicPicker } from './TopicPicker';
import { toBrowserLivekitUrl } from './livekitUrl';
import { Face } from '../../components/common/Faces';
import { useAuth } from '../../app/AuthContext';
import '../../styles/RoomPage.css';
import {
  HiArrowLeft, HiMicrophone, HiVideoCamera, HiVideoCameraSlash,
  HiMicrophone as HiMicOff, HiPhoneXMark, HiChatBubbleLeftRight,
  HiUserGroup, HiShieldExclamation, HiClock, HiCheckCircle, HiArrowRight,
  HiHandRaised, HiFaceSmile, HiComputerDesktop,
  HiUserPlus, HiUser, HiEllipsisVertical, HiCog6Tooth,
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

function useIsMobile(breakpoint = 640) {
  const [mobile, setMobile] = useState(() => typeof window !== 'undefined' && window.innerWidth <= breakpoint);
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${breakpoint}px)`);
    const fn = (e) => setMobile(e.matches);
    if (mq.addEventListener) mq.addEventListener('change', fn);
    setMobile(mq.matches);
    return () => { if (mq.removeEventListener) mq.removeEventListener('change', fn); };
  }, [breakpoint]);
  return mobile;
}

function useOptimisticToggle(live) {
  const [opt, setOpt] = useState(null);
  useEffect(() => {
    if (opt === null) return;
    if (opt === live) {
      setOpt(null);
      return;
    }
    const timer = setTimeout(() => setOpt(null), 2500);
    return () => clearTimeout(timer);
  }, [opt, live]);
  return [opt ?? live, setOpt];
}

function ControlBtn({ icon: Icon, offIcon: OffIcon, on, onClick, label, danger, small }) {
  const ShowIcon = !on && OffIcon ? OffIcon : Icon;
  const labelText = on ? label.on : label.off;
  return (
    <button
      onClick={onClick}
      aria-label={labelText}
      aria-pressed={on}
      title={labelText}
      style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 4,
        minWidth: small ? 56 : 68, minHeight: 56, padding: '8px 10px', cursor: 'pointer',
        background: danger ? '#fff' : on ? '#0a0a0a' : 'transparent',
        color: danger ? '#111' : on ? '#fff' : '#888',
        border: danger ? '2px solid #fff' : on ? '2px solid #fff' : '2px dashed #555',
      }}
    >
      <ShowIcon size={20} />
      <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: '0.04em' }}>{labelText}</span>
    </button>
  );
}

function MeetControls({ roomId, onLeave, togglePanel, activePanel, handRaised, setHandRaised,
  showEmojiPicker, setShowEmojiPicker, sendEmoji, setScreenShareOn, onOpenParticipants }) {
  const { localParticipant } = useLocalParticipant();
  const room = useRoomContext();
  const isMobile = useIsMobile();
  const [showMore, setShowMore] = useState(false);

  const [deviceError, setDeviceError] = useState('');
  // Mic/cam nam hoan toan o trinh duyet (server chi signaling) nen loi nay
  // luon la phia user: chua cap quyen, khong co thiet bi, hoac thiet bi dang ban.
  const onDeviceError = useCallback((e) => {
    const name = e?.name || '';
    console.warn('media device error:', name, e?.message);
    setDeviceError(
      name === 'NotAllowedError' || name === 'SecurityError'
        ? 'Browser blocked the mic/camera — click the lock icon in the address bar to allow access, then try again.'
        : name === 'NotFoundError' || name === 'OverconstrainedError'
          ? 'No mic/camera found on this device — plug one in (or enable it in system settings), then try again.'
          : name === 'NotReadableError' || name === 'AbortError'
            ? 'Your mic/camera looks busy — close other apps or tabs using it (Zoom, Zalo, Meet…), then try again.'
            : 'Could not access mic/camera. Check that a device is connected and not used elsewhere, then try again.',
    );
  }, []);

  // Goi truc tiep localParticipant (khong qua useTrackToggle) de tranh
  // truong hop toggle khong doi state live → optimistic tu revert.
  // State hien thi doc thang tu participant + force re-render qua events.
  const [, forceSync] = useReducer((x) => x + 1, 0);
  const [micBusy, setMicBusy] = useState(false);
  const [camBusy, setCamBusy] = useState(false);
  const [screenBusy, setScreenBusy] = useState(false);

  useEffect(() => {
    if (!localParticipant) return;
    const bump = () => forceSync();
    const evts = ['trackMuted', 'trackUnmuted', 'localTrackPublished', 'localTrackUnpublished', 'trackSubscribed', 'trackUnsubscribed', 'trackEnabled', 'trackDisabled'];
    evts.forEach((e) => localParticipant.on(e, bump));
    return () => { evts.forEach((e) => localParticipant.off(e, bump)); };
  }, [localParticipant]);

  const liveMicOn = localParticipant ? !!localParticipant.isMicrophoneEnabled : true;
  const liveCamOn = localParticipant ? !!localParticipant.isCameraEnabled : true;
  const liveScreenOn = localParticipant ? !!localParticipant.isScreenShareEnabled : false;

  const [micOn, setMicOpt] = useOptimisticToggle(liveMicOn);
  const [camOn, setCamOpt] = useOptimisticToggle(liveCamOn);
  const [screenOn, setScreenOpt] = useOptimisticToggle(liveScreenOn);

  useEffect(() => {
    setScreenShareOn(liveScreenOn);
  }, [liveScreenOn, setScreenShareOn]);

  const toggleMic = useCallback(async () => {
    if (!localParticipant || micBusy) return;
    setDeviceError('');
    const next = !liveMicOn;
    setMicOpt(next);
    setMicBusy(true);
    try {
      await localParticipant.setMicrophoneEnabled(next);
    } catch (e) {
      console.warn('toggleMic:', e);
      onDeviceError(e);
    } finally {
      setMicBusy(false);
    }
  }, [localParticipant, micBusy, liveMicOn, setMicOpt, onDeviceError]);

  const toggleCam = useCallback(async () => {
    if (!localParticipant || camBusy) return;
    setDeviceError('');
    const next = !liveCamOn;
    setCamOpt(next);
    setCamBusy(true);
    try {
      await localParticipant.setCameraEnabled(next);
    } catch (e) {
      console.warn('toggleCam:', e);
      onDeviceError(e);
    } finally {
      setCamBusy(false);
    }
  }, [localParticipant, camBusy, liveCamOn, setCamOpt, onDeviceError]);

  const toggleScreenShare = useCallback(async () => {
    if (!localParticipant || screenBusy) return;
    setDeviceError('');
    const next = !liveScreenOn;
    setScreenOpt(next);
    setScreenBusy(true);
    try {
      await localParticipant.setScreenShareEnabled(next);
    } catch (e) {
      console.warn('toggleScreenShare:', e);
      onDeviceError(e);
    } finally {
      setScreenBusy(false);
    }
  }, [localParticipant, screenBusy, liveScreenOn, setScreenOpt, onDeviceError]);

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

  function PendingBtn({ pending, children }) {
    return (
      <span style={{ position: 'relative', display: 'inline-flex', opacity: pending ? 0.55 : 1 }}>
        {children}
        {pending && (
          <span style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 800, color: '#fff', background: 'rgba(0,0,0,0.45)' }}>…</span>
        )}
      </span>
    );
  }

  const mediaBtns = (
    <>
      <PendingBtn pending={micBusy}>
        <ControlBtn icon={HiMicrophone} offIcon={HiMicOff} on={micOn}
          onClick={toggleMic}
          label={{ on: 'Mic on', off: 'Muted' }}
        />
      </PendingBtn>
      <PendingBtn pending={camBusy}>
        <ControlBtn icon={HiVideoCamera} offIcon={HiVideoCameraSlash} on={camOn}
          onClick={toggleCam}
          label={{ on: 'Cam on', off: 'Cam off' }}
        />
      </PendingBtn>
      <PendingBtn pending={screenBusy}>
        <ControlBtn icon={HiComputerDesktop} on={screenOn}
          onClick={toggleScreenShare}
          label={{ on: 'Sharing', off: 'Share' }}
        />
      </PendingBtn>
    </>
  );

  const funBtns = (
    <>
      <ControlBtn icon={HiHandRaised} on={handRaised}
        onClick={toggleHandRaise}
        label={{ on: 'Hand up', off: 'Raise hand' }}
      />
      <span style={{ position: 'relative', display: 'inline-flex' }}>
        <ControlBtn icon={HiFaceSmile} on={showEmojiPicker}
          onClick={() => setShowEmojiPicker(prev => !prev)}
          label={{ on: 'React', off: 'React' }}
        />
        {showEmojiPicker && (
          <span style={{ position: 'absolute', bottom: 64, left: '50%', transform: 'translateX(-50%)', display: 'flex', gap: 4, background: '#fff', border: '2px solid #111', padding: 8, zIndex: 50 }}>
            {EMOJIS.map(emoji => (
              <button key={emoji} onClick={() => sendEmoji(emoji)} style={{ fontSize: 20, background: 'none', border: 'none', cursor: 'pointer' }}>{emoji}</button>
            ))}
          </span>
        )}
      </span>
    </>
  );

  const panelBtns = (
    <>
      <ControlBtn icon={HiChatBubbleLeftRight} on={activePanel === 'chat'}
        onClick={() => { setShowMore(false); togglePanel('chat'); }}
        label={{ on: 'Chat open', off: 'Chat' }}
      />
      <ControlBtn icon={HiUserGroup} on={activePanel === 'participants'}
        onClick={() => { setShowMore(false); onOpenParticipants?.(); }}
        label={{ on: 'People', off: 'People' }}
      />
      <ControlBtn icon={HiCog6Tooth} on={activePanel === 'settings'}
        onClick={() => { setShowMore(false); togglePanel('settings'); }}
        label={{ on: 'Setup', off: 'Setup' }}
      />
    </>
  );

  async function handleLeaveNow() {
    // Bao server xoa minh khoi phong NGAY (khong doi webhook LiveKit —
    // webhook miss khi tab dong dot ngot), roi moi ngat ket noi.
    try {
      await fetchJson(`/rooms/${roomId}/leave`, { method: 'POST' });
    } catch {}
    try {
      room?.disconnect();
    } catch {}
    onLeave();
  }

  function LeaveBtn() {
    return (
      <button onClick={handleLeaveNow} title="Leave call" aria-label="Leave call"
        style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 4, minWidth: 68, minHeight: 56, padding: '8px 10px', cursor: 'pointer', background: '#fff', color: '#111', border: '2px solid #fff' }}>
        <HiPhoneXMark size={20} />
        <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: '0.04em' }}>Leave</span>
      </button>
    );
  }

  return (
    <footer style={{ background: '#0a0a0a', borderTop: '2px solid #000', padding: '10px 12px' }}>
      {deviceError && (
        <div style={{ maxWidth: 640, margin: '0 auto 8px', background: '#fff', color: '#111', border: '2px solid #111', padding: '8px 12px', fontSize: 12, fontWeight: 700, display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ flex: 1 }}>{deviceError}</span>
          <button onClick={() => setDeviceError('')} aria-label="Dismiss" style={{ background: 'none', border: '1px solid #111', fontWeight: 800, cursor: 'pointer', padding: '2px 8px' }}>✕</button>
        </div>
      )}
      {isMobile ? (
        <>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 8 }}>
            {mediaBtns}
            <button onClick={() => setShowMore(v => !v)} aria-label="More controls" aria-expanded={showMore}
              style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 4, minWidth: 68, minHeight: 56, padding: '8px 10px', cursor: 'pointer', background: showMore ? '#fff' : 'transparent', color: showMore ? '#111' : '#fff', border: '2px solid #fff' }}>
              <HiEllipsisVertical size={20} />
              <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: '0.04em' }}>More</span>
            </button>
            <LeaveBtn />
          </div>
          {showMore && (
            <div style={{ display: 'flex', justifyContent: 'center', gap: 8, flexWrap: 'wrap', marginTop: 8, paddingTop: 10, borderTop: '1px solid #333' }}>
              {funBtns}
              {panelBtns}
            </div>
          )}
        </>
      ) : (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, flexWrap: 'wrap', maxWidth: 1200, margin: '0 auto' }}>
          {mediaBtns}
          {funBtns}
          <LeaveBtn />
        </div>
      )}
    </footer>
  );
}

function isAiParticipant(identity) {
  return String(identity || '').startsWith('ai_');
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
      // AI (ai_assistant/ai_transcriber/ai_observer) khong chiem seat,
      // khong hien nhu 1 user trong room.
      if (isAiParticipant(p.identity)) return;
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

function RemoteAudioRenderer() {
  const remoteParticipants = useRemoteParticipants();
  return (
    <>
      {remoteParticipants?.map(p => (
        <AudioTrack key={p.identity} trackRef={{ participant: p, source: Track.Source.Microphone }} />
      ))}
    </>
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
  // Loc AI (ai_*) khoi video grid — khong chiem seat, khong hien nhu user.
  const roomTracks = tracks.filter((track) => {
    if (track?.source === Track.Source.ScreenShare) return true;
    if (track?.participant?.isLocal) return false;
    return !isAiParticipant(track?.participant?.identity);
  });
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
    <div className="room-page__video-inner">
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

const CONNECT_STEPS = ['Finding your room…', 'Checking mic & camera…', 'Reserving your seat…', 'Going live…'];

function EqualizerBars() {
  const bars = [0, 1, 2, 3, 4, 5, 6];
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'center', gap: 6, height: 56 }} aria-hidden="true">
      {bars.map((i) => (
        <span
          key={i}
          style={{
            width: 10,
            height: '100%',
            background: '#111',
            transformOrigin: 'bottom',
            animation: `er-eq 1s ease-in-out ${i * 0.12}s infinite`,
          }}
        />
      ))}
    </div>
  );
}

function ConnectingGate({ roomName }) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setStep((s) => (s + 1) % CONNECT_STEPS.length), 1400);
    return () => clearInterval(timer);
  }, []);

  return (
    <div style={{ minHeight: '100dvh', background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      <div style={{ background: '#fff', border: '2px solid #111', padding: 'clamp(32px, 5vw, 56px)', textAlign: 'center', maxWidth: 440, width: '100%', boxShadow: '8px 8px 0 #111' }}>
        <div style={{ display: 'inline-flex', gap: 4, marginBottom: 20 }} aria-hidden="true">
          {[0, 1, 2, 3].map((i) => (
            <span
              key={i}
              style={{
                width: 14,
                height: 14,
                background: '#111',
                animation: `er-seat 1.2s ease-in-out ${i * 0.15}s infinite`,
              }}
            />
          ))}
        </div>
        <EqualizerBars />
        <p style={{ margin: '20px 0 4px', fontSize: 11, fontWeight: 800, letterSpacing: '0.22em', color: '#666' }}>JOINING ROOM</p>
        <h2 style={{ margin: 0, fontSize: 24, color: '#111', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {roomName || '…'}
        </h2>
        <p key={step} style={{ margin: '14px 0 0', fontSize: 14, fontWeight: 600, color: '#111', animation: 'er-fadein 0.4s ease' }}>
          {CONNECT_STEPS[step]}
        </p>
      </div>
      <style>{`
        @keyframes er-eq { 0%, 100% { transform: scaleY(0.25); } 50% { transform: scaleY(1); } }
        @keyframes er-seat { 0%, 100% { opacity: 0.25; } 50% { opacity: 1; } }
        @keyframes er-fadein { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
      `}</style>
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
    <aside className="room-page__panel">
      <header className="room-page__panel-header">
        <div className="room-page__panel-header-left">
          <span className="room-page__panel-header-icon" style={{ color: '#111' }}><HiUserGroup size={16} /></span>
          <h3 className="room-page__panel-header-title">Participants</h3>
          <span className="room-page__panel-header-count">{participants?.length ?? 0}</span>
        </div>
        <button onClick={onClose} aria-label="Close" className="room-page__panel-close-btn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
        </button>
      </header>
      <div className="room-page__panel-body">
        {participants.map((p, i) => {
          const alreadyFriend = isFriend(p.identity);
          return (
            <div key={p.identity || i} className="room-page__panel-row">
              <span style={{ display: 'inline-flex', position: 'relative', flexShrink: 0 }}>
                <Face name={p.name} size={38} />
                <span style={{ position: 'absolute', bottom: -2, right: -2, width: 12, height: 12, background: p.camOn ? '#15803d' : '#999', border: '2px solid #fff' }} />
              </span>
              <div className="room-page__panel-row-name-wrap">
                <div className="room-page__panel-row-name">
                  {p.name}
                  {p.isLocal && <span className="room-page__panel-you-badge">You</span>}
                </div>
                <div className="room-page__panel-status-row">
                  <span className="room-page__panel-status-item" style={{ color: p.micOn ? 'var(--color-success)' : 'var(--color-danger)' }}>
                    <span className="room-page__panel-status-dot" style={{ background: p.micOn ? 'var(--color-success)' : 'var(--color-danger)' }} />
                    {p.micOn ? 'Mic on' : 'Muted'}
                  </span>
                  <span className="room-page__panel-status-item" style={{ color: p.camOn ? 'var(--color-success)' : 'var(--color-danger)' }}>
                    <span className="room-page__panel-status-dot" style={{ background: p.camOn ? 'var(--color-success)' : 'var(--color-danger)' }} />
                    {p.camOn ? 'Cam on' : 'Cam off'}
                  </span>
                </div>
              </div>
              {!p.isLocal && (
                alreadyFriend ? (
                  <button onClick={() => removeFriend(p.identity)} className="room-page__panel-btn-friend"><HiUser size={11} /> Friends</button>
                ) : (
                  <button onClick={() => addFriend(p.identity, p.name)} className="room-page__panel-btn-add"><HiUserPlus size={11} /> Add Friend</button>
                ))}
            </div>
          );
        })}
      </div>
      {friends.length > 0 && (
        <div className="room-page__panel-friends-section">
          <div className="room-page__panel-friends-title">Friends ({friends.length})</div>
          <div className="room-page__panel-friends-row">
            {friends.map(f => (
              <span key={f.id} className="room-page__panel-friend-tag">
                <div className="room-page__panel-friend-avatar" style={{ background: hashColor(f.name) }}>{getInitials(f.name)}</div>
                {f.name}
              </span>
            ))}
          </div>
        </div>
      )}
    </aside>
  );
}

const FEATURE_DEFS = [
  { key: 'enable_heartbeat', label: 'Heartbeat', desc: 'AI restarts quiet rooms with warm-up questions' },
  { key: 'enable_transcript', label: 'Transcript', desc: 'Live speech-to-text for every voice' },
  { key: 'enable_agent', label: 'Agent live', desc: 'AI answers @ai mentions in chat + voice' },
];

function FeatureSwitch({ on, onClick, label, desc }) {
  return (
    <button onClick={onClick} aria-pressed={on}
      style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, width: '100%', background: '#fff', border: on ? '2px solid #111' : '1px solid #e8e8e8', padding: '12px 14px', cursor: 'pointer', textAlign: 'left' }}>
      <span>
        <span style={{ display: 'block', fontWeight: 800, fontSize: 14 }}>{label}</span>
        <span style={{ display: 'block', fontSize: 12, color: '#666', marginTop: 2 }}>{desc}</span>
      </span>
      <span style={{ width: 46, height: 26, background: on ? '#111' : '#ddd', display: 'inline-flex', alignItems: 'center', padding: 3, justifyContent: on ? 'flex-end' : 'flex-start', flexShrink: 0 }}>
        <span style={{ width: 20, height: 20, background: '#fff', border: on ? 'none' : '1px solid #bbb' }} />
      </span>
    </button>
  );
}

function RoomSettings({ roomId, current, onClose, onSave, api }) {
  const [name, setName] = useState(current.name || '');
  const [description, setDescription] = useState(current.description || '');
  const [topics, setTopics] = useState(Array.isArray(current.topics) ? current.topics : []);
  const [seats, setSeats] = useState(current.max_participants || 4);
  const [flags, setFlags] = useState({
    enable_heartbeat: current.enable_heartbeat !== false,
    enable_transcript: current.enable_transcript !== false,
    enable_agent: current.enable_agent !== false,
  });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');

  const handleSave = useCallback(async () => {
    setSaving(true);
    setSaveError('');
    try {
      await api.patch(`/rooms/${roomId}`, {
        name: name.trim() || undefined,
        description: description.trim() || undefined,
        topics,
        max_participants: seats,
        ...flags,
      });
      if (onSave) await onSave();
      onClose();
    } catch (err) {
      setSaveError(err?.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  }, [roomId, name, description, topics, seats, flags, api, onSave, onClose]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0, background: '#fff' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', borderBottom: '2px solid #111', flexShrink: 0 }}>
        <strong style={{ fontSize: 14, display: 'inline-flex', alignItems: 'center', gap: 8 }}><HiCog6Tooth size={16} /> Room setup</strong>
        <button onClick={onClose} aria-label="Close settings" style={{ background: '#fff', border: '1px solid #111', width: 30, height: 30, fontWeight: 800, cursor: 'pointer' }}>✕</button>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: 14, display: 'grid', gap: 16, alignContent: 'start', minHeight: 0 }}>
        <div>
          <label className="er-label">Room name</label>
          <input className="er-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="AI Agents & Automation" />
        </div>
        <div>
          <label className="er-label">Description</label>
          <textarea className="er-textarea" rows={3} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What is this room about?" />
        </div>
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <label className="er-label" style={{ margin: 0 }}>Topics</label>
            <span style={{ fontSize: 12, fontWeight: 800, color: '#999' }}>{topics.length}/{MAX_TOPICS}</span>
          </div>
          <TopicPicker topics={topics} onChange={setTopics} />
        </div>
        <div>
          <label className="er-label">Seats</label>
          <div style={{ display: 'flex', gap: 8 }}>
            {[2, 3, 4].map((n) => (
              <button key={n} type="button" onClick={() => setSeats(n)}
                style={{ flex: 1, padding: '12px 0', fontWeight: 800, cursor: 'pointer', background: seats === n ? '#111' : '#fff', color: seats === n ? '#fff' : '#111', border: '1px solid #111' }}>
                {n}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="er-label">Features</label>
          <div style={{ display: 'grid', gap: 8 }}>
            {FEATURE_DEFS.map((f) => (
              <FeatureSwitch key={f.key} label={f.label} desc={f.desc} on={!!flags[f.key]} onClick={() => setFlags((p) => ({ ...p, [f.key]: !p[f.key] }))} />
            ))}
          </div>
        </div>
        {saveError && <div className="er-alert er-alert--err">{saveError}</div>}
      </div>
      <div style={{ display: 'flex', gap: 10, padding: 14, borderTop: '2px solid #111', flexShrink: 0 }}>
        <button className="er-btn er-btn--ghost" style={{ flex: 1, justifyContent: 'center' }} onClick={onClose}>Cancel</button>
        <button className="er-btn" style={{ flex: 2, justifyContent: 'center' }} onClick={handleSave} disabled={saving}>
          {saving ? 'Saving…' : 'Save setup'}
        </button>
      </div>
    </div>
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
  const [roomData, setRoomData] = useState(null);
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
  const [retrySignal, setRetrySignal] = useState(0);
  const [connError, setConnError] = useState('');
  const chat = useRoomChat(roomId);
  const { user } = useAuth();

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
  const refreshRoomData = useCallback(async () => {
    try {
      const data = await fetchJson(`/rooms/${roomId}`);
      setRoomData(data);
      setRoomName(data?.name || data?.room_name || 'Room');
    } catch {}
  }, [roomId]);

  const handleLeave = useCallback(() => {
    hasLeftRef.current = true;
    setPhase('left');
  }, []);
  const goBack = useCallback(() => {
    // Mui ten back cung la roi phong — bao server truoc khi chuyen trang
    fetchJson(`/rooms/${roomId}/leave`, { method: 'POST' }).catch(() => {});
    navigate('/rooms');
  }, [navigate, roomId]);

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

  // Lay ten phong som de man hinh loading hien ten that
  useEffect(() => {
    refreshRoomData();
  }, [refreshRoomData]);

  useEffect(() => {
    let cancelled = false;
    async function joinAndGetToken() {
      try {
        const roomData = await fetchJson(`/rooms/${roomId}`);
        if (cancelled) return;
        setRoomName(roomData?.name || roomData?.room_name || 'Room');
        setRoomData(roomData);
        // Backend theo doi participants qua LiveKit webhook — lay token la du de join.
        const tokenResult = await api.post(`/rooms/${roomId}/token`);
        if (cancelled) return;

        const finalUrl = toBrowserLivekitUrl(tokenResult.livekit_url);
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
      <div className="room-page__loading-wrap">
        <ConnectingGate roomName={roomName} />
      </div>
    );
  }

  if (phase === 'error') {
    return (
      <div style={{ minHeight: '100dvh', background: '#f7f7f7', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <div style={{ background: '#fff', border: '2px solid #111', maxWidth: 440, width: '100%', padding: 'clamp(28px,4vw,44px)', textAlign: 'center' }}>
          <div style={{ display: 'inline-flex', width: 56, height: 56, border: '2px solid #111', alignItems: 'center', justifyContent: 'center', fontSize: 28, fontWeight: 800 }}>!</div>
          <h2 style={{ fontSize: 26, margin: '18px 0 8px', color: '#000' }}>Failed to join room</h2>
          <p style={{ color: '#666', fontSize: 14, margin: '0 0 24px' }}>{error}</p>
          <div style={{ display: 'flex', gap: 10 }}>
            <button className="er-btn er-btn--ghost" style={{ flex: 1, justifyContent: 'center' }} onClick={handleRetry}>Retry</button>
            <button className="er-btn" style={{ flex: 1, justifyContent: 'center' }} onClick={goBack}>Back to Rooms</button>
          </div>
        </div>
      </div>
    );
  }

  if (phase === 'left') {
    return (
      <div style={{ minHeight: '100dvh', background: '#f7f7f7', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <div style={{ background: '#fff', border: '2px solid #111', maxWidth: 440, width: '100%', padding: 'clamp(28px,4vw,44px)', textAlign: 'center' }}>
          <div style={{ display: 'inline-flex', width: 56, height: 56, background: '#111', color: '#fff', alignItems: 'center', justifyContent: 'center' }}>
            <HiCheckCircle size={30} />
          </div>
          <h2 style={{ fontSize: 28, margin: '18px 0 8px', color: '#000' }}>You left the room</h2>
          <p style={{ color: '#666', fontSize: 14, margin: '0 0 20px' }}>Thanks for joining <strong style={{ color: '#111' }}>{roomName || 'the session'}</strong>!</p>
          <div style={{ display: 'flex', border: '1px solid #111', marginBottom: 24 }}>
            <div style={{ flex: 1, padding: '14px 0' }}>
              <div style={{ fontWeight: 800, fontSize: 22, color: '#111' }}>{formatTime(savedElapsed || elapsed)}</div>
              <div style={{ fontSize: 12, color: '#666' }}>Duration</div>
            </div>
            <div style={{ flex: 1, padding: '14px 0', borderLeft: '1px solid #e8e8e8' }}>
              <div style={{ fontWeight: 800, fontSize: 22, color: '#111' }}>{participantsList.length || 1}</div>
              <div style={{ fontSize: 12, color: '#666' }}>Participants</div>
            </div>
          </div>
          <button className="er-btn" style={{ width: '100%', justifyContent: 'center' }} onClick={goBack}>Back to Rooms →</button>
        </div>
      </div>
    );
  }

  const participantCount = participantsList.length || 1;
  const panelOpen = activePanel === 'participants' || activePanel === 'settings';

  function TopIconBtn({ active, onClick, title, children }) {
    return (
      <button className="meet-topbar-iconbtn" onClick={onClick} title={title} aria-label={title}
        style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 12px', cursor: 'pointer', fontSize: 13, fontWeight: 800, background: active ? '#111' : '#fff', color: active ? '#fff' : '#111', border: '1px solid #111' }}>
        {children}
      </button>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100dvh', background: '#fff', color: '#111' }}>

      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, padding: '10px 16px', background: '#fff', borderBottom: '2px solid #111', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
          <button onClick={goBack} title="Back to rooms" aria-label="Back to rooms"
            style={{ width: 38, height: 38, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: '#fff', border: '1px solid #111', cursor: 'pointer', flexShrink: 0 }}>
            <HiArrowLeft size={18} />
          </button>
          <div style={{ minWidth: 0 }}>
            <h1 style={{ fontSize: 17, margin: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{roomName || 'Room'}</h1>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 2 }}>
              <span style={{ fontSize: 11, fontWeight: 800, background: '#111', color: '#fff', padding: '2px 7px' }}>● LIVE</span>
              <span style={{ fontSize: 12, color: '#555', display: 'inline-flex', alignItems: 'center', gap: 4 }}><HiClock size={12} />{formatTime(elapsed)}</span>
              {handRaised && <span style={{ fontSize: 11, fontWeight: 800, border: '1px solid #111', padding: '2px 7px' }}>✋ Raised</span>}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <TopIconBtn active={activePanel === 'participants'} onClick={openParticipants} title="View participants">
            <HiUserGroup size={15} /><span>{participantCount}</span>
          </TopIconBtn>
          <TopIconBtn active={activePanel === 'settings'} onClick={() => togglePanel('settings')} title="Room settings">
            <HiCog6Tooth size={16} />
          </TopIconBtn>
          <TopIconBtn active={activePanel === 'chat'} onClick={() => togglePanel('chat')} title={activePanel === 'chat' ? 'Hide chat' : 'Show chat'}>
            <HiChatBubbleLeftRight size={16} />
          </TopIconBtn>
        </div>
      </header>

      {connError && (
        <div style={{ background: '#fff', color: '#111', borderBottom: '2px solid #111', padding: '8px 16px', fontSize: 12, fontWeight: 700, display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ flex: 1 }}>Live connection issue: {connError}</span>
          <button onClick={() => setConnError('')} aria-label="Dismiss" style={{ background: 'none', border: '1px solid #111', color: '#111', fontWeight: 800, cursor: 'pointer', padding: '2px 8px' }}>✕</button>
        </div>
      )}

      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', background: '#0a0a0a' }}>
          <LiveKitRoom token={token} serverUrl={livekitUrl} video={true} audio={true} onDisconnected={handleDisconnected} onError={(e) => setConnError(e?.message || 'Could not connect to the live room')}
            className="room-page__livekit" data-lk-theme="default" style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, height: '100%' }}>
            <RemoteAudioRenderer />
            <RoomDataBridge onData={chat.handleLiveData} />
            <ParticipantTracker onUpdate={handleParticipantUpdate} />
            <EmojiFly emojis={floatingEmojis} />
            <div style={{ flex: 1, minHeight: 0, position: 'relative', display: 'flex', flexDirection: 'column' }}>
              <VideoArea isSharing={screenShareOn} isHandRaised={handRaised} />
              <SelfPreview />
            </div>
            <MeetControls roomId={roomId} onLeave={handleLeave} togglePanel={togglePanel} activePanel={activePanel}
              handRaised={handRaised} setHandRaised={setHandRaised}
              showEmojiPicker={showEmojiPicker} setShowEmojiPicker={setShowEmojiPicker}
              sendEmoji={sendEmoji} screenShareOn={screenShareOn} setScreenShareOn={setScreenShareOn}
              onOpenParticipants={openParticipants} />
          </LiveKitRoom>
        </div>

        <ChatWindow
          chat={chat}
          visible={activePanel === 'chat'}
          onClose={() => setActivePanel(null)}
          currentUserId={user?.id}
        />
        {panelOpen && (
          <aside style={{ width: 340, maxWidth: '92vw', background: '#fff', borderLeft: '2px solid #111', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            {activePanel === 'participants' && <ParticipantsPanel participants={participantsList} onClose={() => setActivePanel(null)} />}
            {activePanel === 'settings' && roomData && <RoomSettings roomId={roomId} current={roomData} onClose={() => setActivePanel(null)} onSave={refreshRoomData} api={api} />}
          </aside>
        )}
      </div>

      {handRaiseNotifs.map((n, i) => (
        <div key={n.id} style={{
          position: 'fixed', top: 76 + (i * 52), right: 20,
          padding: '10px 16px', zIndex: 200,
          background: '#fff', border: '2px solid #111',
          color: '#111', fontSize: 13, fontWeight: 700,
          display: 'flex', alignItems: 'center', gap: 8,
          pointerEvents: 'none',
        }}>
          ✋ {n.name || 'Someone'} raised hand!
        </div>
      ))}

    </div>
  );
}
