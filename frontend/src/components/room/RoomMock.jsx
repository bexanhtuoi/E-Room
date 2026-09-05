import { HiMicrophone, HiVideoCamera, HiHandRaised, HiChatBubbleLeftRight, HiComputerDesktop, HiFaceSmile, HiPhoneXMark } from 'react-icons/hi2';
import { Face } from '../common/Faces';

const TILES = [
  { name: 'Linh Nguyen', tag: 'You • Hanoi', speaking: true, mic: true, hand: false, face: 0 },
  { name: 'Carlos Mendez', tag: 'Mexico City', speaking: false, mic: true, hand: true, face: 1 },
  { name: 'Yuki Tanaka', tag: 'Osaka', speaking: false, mic: false, hand: false, face: 2 },
  { name: 'AI Companion', tag: 'In this room', speaking: false, mic: true, hand: false, face: null },
];

const CHAT = [
  { who: 'Linh Nguyen', text: 'Has anyone tried an agent that books meetings by itself?' },
  { who: 'Carlos Mendez', text: 'Yes — mine handles invites but still asks before sending.' },
  { who: 'Yuki Tanaka', text: '@ai what is an AI agent in one sentence?' },
  { who: 'AI Companion', text: 'Software that perceives, decides and acts toward a goal — like a junior teammate on autopilot.', ai: true },
  { who: 'Linh Nguyen', text: 'That junior teammate analogy is perfect.' },
];

export function RoomMock() {
  return (
    <div style={{ border: '2px solid #111', background: '#fff' }}>
      {/* browser chrome */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', borderBottom: '1px solid #e8e8e8', background: '#f7f7f7' }}>
        <span style={{ display: 'flex', gap: 6 }}>
          <i style={{ width: 10, height: 10, background: '#111', display: 'block' }} />
          <i style={{ width: 10, height: 10, background: '#bbb', display: 'block' }} />
          <i style={{ width: 10, height: 10, background: '#ddd', display: 'block', border: '1px solid #bbb' }} />
        </span>
        <span style={{ flex: 1, background: '#fff', border: '1px solid #e8e8e8', fontSize: 12, color: '#666', padding: '6px 12px' }}>eroom.app/rooms/ai-agents-daily</span>
        <span className="er-tag">● Live</span>
      </div>

      {/* room top bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderBottom: '1px solid #111', background: '#fff', flexWrap: 'wrap', gap: 8 }}>
        <div>
          <strong style={{ fontSize: 15 }}>AI Agents & Automation</strong>
          <span style={{ fontSize: 12, color: '#666', marginLeft: 10 }}>00:12:46 • up to 4 seats</span>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ fontSize: 12, fontWeight: 700, border: '1px solid #111', padding: '5px 10px' }}>4 / 4 talking</span>
          <span style={{ fontSize: 12, fontWeight: 800, background: '#111', color: '#fff', padding: '6px 12px' }}>Leave</span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr' }} className="roommock-grid">
        {/* video grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, background: '#111', padding: 2 }}>
          {TILES.map((p) => (
            <div key={p.name} style={{ background: '#262626', color: '#fff', minHeight: 190, padding: 12, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', outline: p.speaking ? '3px solid #fff' : 'none', outlineOffset: -3 }}>
              <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
                <span style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
                  {p.hand && <HiHandRaised size={13} color="#fff" />}
                  <HiMicrophone size={13} color={p.mic ? '#fff' : '#888'} />
                  <HiVideoCamera size={13} color="#fff" />
                </span>
              </div>
              <div style={{ textAlign: 'center' }}>
                {p.face === null ? (
                  <div style={{ width: 56, height: 56, background: '#fff', color: '#111', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 22 }}>AI</div>
                ) : (
                  <span style={{ display: 'inline-block', outline: p.speaking ? '3px solid #fff' : 'none' }}><Face name={p.name} size={56} variant={p.face} /></span>
                )}
                <div style={{ marginTop: 8, fontWeight: 700, fontSize: 14 }}>{p.name}</div>
                <div style={{ fontSize: 12, color: '#bbb' }}>{p.tag}</div>
              </div>
              <div style={{ fontSize: 11, color: p.speaking ? '#fff' : '#888', fontWeight: 700 }}>{p.speaking ? '● Speaking…' : p.mic ? 'Listening' : 'Muted'}</div>
            </div>
          ))}
        </div>

        {/* single shared chat */}
        <div style={{ background: '#fff', display: 'flex', flexDirection: 'column', borderLeft: '1px solid #111', minHeight: 380 }}>
          <div style={{ padding: '12px 14px', borderBottom: '1px solid #111', display: 'flex', alignItems: 'center', gap: 8, fontWeight: 800, fontSize: 13 }}>
            <HiChatBubbleLeftRight size={16} /> Room chat
          </div>
          <div style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 10, flex: 1 }}>
            {CHAT.map((t) => (
              <div key={t.text} style={{ border: t.ai ? '1px solid #111' : '1px solid #e8e8e8', padding: '10px 12px', background: t.ai ? '#f7f7f7' : '#fff' }}>
                <div style={{ fontSize: 12, fontWeight: 800 }}>{t.who}{t.ai && <span style={{ marginLeft: 8, fontSize: 11, background: '#111', color: '#fff', padding: '2px 6px' }}>@ai reply</span>}</div>
                <div style={{ fontSize: 14, color: '#333', marginTop: 4 }}>{t.text}</div>
              </div>
            ))}
          </div>
          <div style={{ padding: 10, borderTop: '1px solid #e8e8e8', display: 'flex', gap: 8 }}>
            <div style={{ flex: 1, border: '1px solid #111', padding: '10px 12px', color: '#999', fontSize: 13 }}>@ai sum up this debate…</div>
            <div style={{ background: '#111', color: '#fff', padding: '10px 16px', fontWeight: 800, fontSize: 13 }}>Send</div>
          </div>
        </div>
      </div>

      {/* control bar mirroring the real room */}
      <div style={{ display: 'flex', gap: 8, justifyContent: 'center', alignItems: 'center', padding: 14, borderTop: '2px solid #111', background: '#fff', flexWrap: 'wrap' }}>
        {[HiComputerDesktop, HiMicrophone, HiVideoCamera, HiHandRaised, HiFaceSmile].map((Icon, i) => (
          <span key={i} style={{ border: '1px solid #111', width: 42, height: 42, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: i === 1 ? '#111' : '#fff' }}>
            <Icon size={18} color={i === 1 ? '#fff' : '#111'} />
          </span>
        ))}
        <span style={{ background: '#111', color: '#fff', width: 52, height: 42, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}><HiPhoneXMark size={20} /></span>
        <span style={{ border: '1px solid #111', width: 42, height: 42, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}><HiChatBubbleLeftRight size={18} /></span>
      </div>
    </div>
  );
}
