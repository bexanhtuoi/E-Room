import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { HiArrowRightOnRectangle, HiBookOpen, HiCalendarDays, HiCheckCircle, HiCreditCard, HiDocumentText, HiPencil, HiPlusCircle, HiShieldCheck, HiUserCircle } from 'react-icons/hi2';
import { useAuth } from '../AuthContext';
import { fetchJson } from '../../lib/api';
import { queryClient } from '../../lib/queryClient';
import { useSubscriptionStore } from '../../stores/subscriptionStore';
import { CreateRoomModal } from '../../features/rooms/CreateRoomModal';
import { Face } from '../../components/common/Faces';

const SECTIONS = [
  { key: 'overview', label: 'User info', icon: HiUserCircle },
  { key: 'sessions', label: 'Recent activity', icon: HiBookOpen },
  { key: 'schedule', label: 'Schedule room', icon: HiCalendarDays },
  { key: 'subscription', label: 'Subscription', icon: HiCreditCard },
  { key: 'settings', label: 'Settings', icon: HiShieldCheck },
];

const PLANS = [
  { key: 'free', name: 'Starter', price: '$0', features: ['5 rooms/week', 'Live transcripts', 'Meeting recaps'] },
  { key: 'pro', name: 'Pro', price: '$9.99/mo', features: ['Unlimited rooms', 'Full recaps + history', 'Priority matching', 'Private rooms'], popular: true },
  { key: 'pro_plus', name: 'Pro+', price: '$19.99/mo', features: ['All Pro features', 'Voice playback', 'Smarter @ai answers', 'Guest invites'] },
];

function formatDate(iso) {
  if (!iso) return '';
  try {
    return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(iso));
  } catch {
    return '';
  }
}

function Panel({ title, action, children }) {
  return (
    <section style={{ background: '#fff', border: '1px solid #e8e8e8' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, padding: '16px 20px', borderBottom: '1px solid #111', flexWrap: 'wrap' }}>
        <h2 style={{ fontSize: 18, margin: 0 }}>{title}</h2>
        {action}
      </div>
      <div style={{ padding: 20 }}>{children}</div>
    </section>
  );
}

function UserInfoPanel({ user, name, setName, editing, setEditing, saveMutation }) {
  return (
    <Panel
      title="Personal information"
      action={!editing && (
        <button className="er-btn er-btn--ghost" style={{ padding: '9px 14px' }} onClick={() => setEditing(true)}>
          <HiPencil size={14} /> Edit
        </button>
      )}
    >
      <div className="er-grid er-grid--2" style={{ gap: 14 }}>
        <div>
          <label className="er-label">Full name</label>
          <input className="er-input" value={name} onChange={(e) => setName(e.target.value)} disabled={!editing} />
        </div>
        <div>
          <label className="er-label">Email</label>
          <input className="er-input" value={user.email || ''} disabled />
        </div>
        <div>
          <label className="er-label">English level</label>
          <input className="er-input" value={user.english_level || 'Not set yet'} disabled />
        </div>
        <div>
          <label className="er-label">Member since</label>
          <input className="er-input" value={formatDate(user.created_at) || '—'} disabled />
        </div>
      </div>
      {editing && (
        <div style={{ display: 'flex', gap: 10, marginTop: 18 }}>
          <button className="er-btn" disabled={saveMutation.isPending || !name.trim()} onClick={() => saveMutation.mutate({ full_name: name.trim() })}>
            {saveMutation.isPending ? 'Saving…' : 'Save changes'}
          </button>
          <button className="er-btn er-btn--ghost" onClick={() => { setName(user.full_name || ''); setEditing(false); }}>Cancel</button>
        </div>
      )}
    </Panel>
  );
}

function ActivityPanel({ messages, isLoading, isError, onRetry }) {
  return (
    <Panel
      title="Recent activity"
      action={<Link className="er-btn er-btn--ghost" style={{ padding: '9px 14px', textDecoration: 'none' }} to="/rooms">Find a room</Link>}
    >
      {isLoading && <p style={{ color: '#666', fontSize: 14 }}>Loading activity…</p>}
      {isError && (
        <div className="er-alert er-alert--err">
          Could not load activity. <button onClick={onRetry} style={{ fontWeight: 800, textDecoration: 'underline', background: 'none', border: 'none', cursor: 'pointer' }}>Try again</button>
        </div>
      )}
      {!isLoading && !isError && messages.length === 0 && (
        <div style={{ border: '1px dashed #bbb', padding: 28, textAlign: 'center', color: '#666', fontSize: 14 }}>
          No messages yet. Join a room and everything you say will appear here.
        </div>
      )}
      {!isLoading && !isError && messages.length > 0 && (
        <div style={{ borderTop: '2px solid #111' }}>
          {messages.map((m) => (
            <Link key={m.id} to={`/rooms/${m.room_id}`} style={{ display: 'flex', gap: 14, alignItems: 'center', padding: '14px 4px', borderBottom: '1px solid #e8e8e8', textDecoration: 'none', color: '#111' }}>
              <span style={{ fontSize: 11, fontWeight: 800, background: m.role === 'ai' ? '#111' : '#fff', color: m.role === 'ai' ? '#fff' : '#111', border: '1px solid #111', padding: '4px 8px', flexShrink: 0 }}>
                {m.role === 'ai' ? 'AI' : 'YOU'}
              </span>
              <span style={{ flex: 1, minWidth: 0 }}>
                <span style={{ display: 'block', fontSize: 14, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{m.text}</span>
                <span style={{ fontSize: 12, color: '#999' }}>{formatDate(m.created_at)}</span>
              </span>
              <span style={{ fontWeight: 800 }} aria-hidden="true">→</span>
            </Link>
          ))}
        </div>
      )}
    </Panel>
  );
}

function SchedulePanel({ onCreateRoom }) {
  return (
    <Panel title="Schedule room">
      <p style={{ color: '#333', fontSize: 15, margin: '0 0 8px' }}><strong style={{ color: '#000' }}>Open a room in 30 seconds.</strong></p>
      <p style={{ color: '#666', fontSize: 14, margin: '0 0 18px' }}>Pick a headline, add up to 5 topics, choose seats. The room goes live immediately.</p>
      <button className="er-btn" onClick={onCreateRoom}><HiPlusCircle size={16} /> Create room</button>
    </Panel>
  );
}

function SubscriptionPanel({ tier }) {
  return (
    <Panel title="Subscription">
      <div className="er-grid er-grid--3" style={{ gap: 12 }}>
        {PLANS.map((plan) => {
          const current = plan.key === tier;
          return (
            <div key={plan.key} style={{ border: current ? '2px solid #111' : '1px solid #e8e8e8', padding: 18, display: 'flex', flexDirection: 'column', background: '#fff' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong>{plan.name}</strong>
                {current
                  ? <span style={{ fontSize: 11, fontWeight: 800, background: '#111', color: '#fff', padding: '3px 8px' }}>CURRENT</span>
                  : plan.popular && <span style={{ fontSize: 11, fontWeight: 800, border: '1px solid #111', padding: '3px 8px' }}>POPULAR</span>}
              </div>
              <div style={{ fontSize: 26, fontWeight: 800, margin: '10px 0' }}>{plan.price}</div>
              <ul style={{ margin: '0 0 16px', paddingLeft: 18, fontSize: 13, color: '#333', display: 'grid', gap: 6 }}>
                {plan.features.map((f) => <li key={f}>{f}</li>)}
              </ul>
              <div style={{ marginTop: 'auto' }}>
                {plan.key === 'free'
                  ? <button className="er-btn er-btn--ghost" style={{ width: '100%', justifyContent: 'center' }} disabled={current}>Free plan</button>
                  : <Link className="er-btn" style={{ width: '100%', justifyContent: 'center', textDecoration: 'none' }} to={`/payment?plan=${plan.key}`}>{current ? 'Manage plan' : 'Upgrade'}</Link>}
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

function SettingsPanel({ logout, onLogout }) {
  const [match, setMatch] = useState(true);
  const [reminders, setReminders] = useState(true);
  const [showProfile, setShowProfile] = useState(true);

  function Switch({ on, onClick, label }) {
    return (
      <button onClick={onClick} aria-pressed={on} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', background: '#fff', border: '1px solid #e8e8e8', padding: '12px 14px', cursor: 'pointer', fontSize: 14, fontWeight: 700 }}>
        {label}
        <span style={{ width: 44, height: 24, background: on ? '#111' : '#ddd', display: 'inline-flex', alignItems: 'center', padding: 3, justifyContent: on ? 'flex-end' : 'flex-start' }}>
          <span style={{ width: 18, height: 18, background: '#fff' }} />
        </span>
      </button>
    );
  }

  return (
    <Panel title="Settings">
      <div style={{ display: 'grid', gap: 8 }}>
        <Switch on={match} onClick={() => setMatch((v) => !v)} label="Room match notifications" />
        <Switch on={reminders} onClick={() => setReminders((v) => !v)} label="Session reminders" />
        <Switch on={showProfile} onClick={() => setShowProfile((v) => !v)} label="Show profile in rooms" />
      </div>
      <div style={{ display: 'flex', gap: 10, marginTop: 18 }}>
        <button className="er-btn er-btn--ghost" onClick={() => { logout(); onLogout(); }}>
          <HiArrowRightOnRectangle size={15} /> Sign out
        </button>
      </div>
      <p style={{ fontSize: 12, color: '#999', marginTop: 12 }}>Notification and privacy switches are stored on this device for now.</p>
    </Panel>
  );
}

export function ProfilePage() {
  const { user, setUser, logout } = useAuth();
  const navigate = useNavigate();
  const [activeSection, setActiveSection] = useState('overview');
  const [displayName, setDisplayName] = useState(user?.full_name || '');
  const [editing, setEditing] = useState(false);
  const [notice, setNotice] = useState(null);
  const [showCreateRoom, setShowCreateRoom] = useState(false);
  const tier = useSubscriptionStore((state) => state.tier);

  const activityQuery = useQuery({
    queryKey: ['user-messages', user?.id],
    queryFn: () => fetchJson(`/messages/?user_id=${user.id}&limit=20`),
    enabled: Boolean(user?.id),
  });
  const messages = Array.isArray(activityQuery.data) ? activityQuery.data : [];

  const saveMutation = useMutation({
    mutationFn: (data) => fetchJson(`/users/${user.id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    onSuccess: (updated) => {
      if (updated?.full_name) {
        setUser({ ...user, full_name: updated.full_name });
        setDisplayName(updated.full_name);
      }
      setEditing(false);
      setNotice({ ok: true, text: 'Profile updated.' });
      setTimeout(() => setNotice(null), 3000);
    },
    onError: (err) => setNotice({ ok: false, text: err?.message || 'Failed to update profile.' }),
  });

  function handleRoomCreated(room) {
    queryClient.invalidateQueries({ queryKey: ['rooms'] });
    setShowCreateRoom(false);
    if (room?.id) navigate(`/rooms/${room.id}`);
  }

  if (!user) return null;

  return (
    <div style={{ background: '#f7f7f7', minHeight: '100svh', padding: '56px 0 96px' }}>
      <div className="er-container" style={{ maxWidth: 1020 }}>
        <div style={{ background: '#fff', border: '2px solid #111', padding: 'clamp(20px,3vw,32px)', display: 'flex', gap: 18, alignItems: 'center', flexWrap: 'wrap' }}>
          <Face name={user.full_name || user.email} size={64} />
          <div style={{ flex: 1, minWidth: 200 }}>
            <h1 style={{ fontSize: 'clamp(24px,3.4vw,34px)', margin: 0 }}>{user.full_name || 'E-Room learner'}</h1>
            <p style={{ color: '#666', fontSize: 14, margin: '4px 0 0' }}>{user.email}</p>
          </div>
          <div style={{ display: 'flex', border: '1px solid #111' }}>
            {[[`${messages.length}`, 'messages'], [tier === 'pro_plus' ? 'Pro+' : tier === 'pro' ? 'Pro' : 'Free', 'plan']].map(([v, l], i) => (
              <div key={l} style={{ padding: '10px 18px', textAlign: 'center', borderLeft: i ? '1px solid #e8e8e8' : 'none' }}>
                <div style={{ fontWeight: 800, fontSize: 18 }}>{v}</div>
                <div style={{ fontSize: 11, color: '#888' }}>{l}</div>
              </div>
            ))}
          </div>
        </div>

        {notice && (
          <div className={`er-alert ${notice.ok ? 'er-alert--ok' : 'er-alert--err'}`} style={{ marginTop: 16 }}>
            {notice.ok && <HiCheckCircle size={15} style={{ marginRight: 6 }} />}{notice.text}
          </div>
        )}

        <div style={{ display: 'flex', gap: 8, marginTop: 16, flexWrap: 'wrap' }}>
          {SECTIONS.map((s) => (
            <button
              key={s.key}
              onClick={() => setActiveSection(s.key)}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 7, padding: '10px 16px', fontWeight: 800, fontSize: 13, cursor: 'pointer', background: activeSection === s.key ? '#111' : '#fff', color: activeSection === s.key ? '#fff' : '#111', border: '1px solid #111' }}
            >
              <s.icon size={15} /> {s.label}
            </button>
          ))}
        </div>

        <div style={{ marginTop: 16 }}>
          {activeSection === 'overview' && (
            <UserInfoPanel user={user} displayName={displayName} setDisplayName={setDisplayName} editing={editing} setEditing={setEditing} saveMutation={saveMutation} />
          )}
          {activeSection === 'sessions' && (
            <ActivityPanel messages={messages} isLoading={activityQuery.isLoading} isError={activityQuery.isError} onRetry={activityQuery.refetch} />
          )}
          {activeSection === 'schedule' && <SchedulePanel onCreateRoom={() => setShowCreateRoom(true)} />}
          {activeSection === 'subscription' && <SubscriptionPanel tier={tier} />}
          {activeSection === 'settings' && <SettingsPanel logout={logout} onLogout={() => navigate('/login')} />}
        </div>

        <div style={{ marginTop: 16, border: '1px solid #e8e8e8', background: '#fff', padding: '18px 20px', display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <HiDocumentText size={18} />
          <p style={{ margin: 0, fontSize: 14, color: '#333', flex: 1, minWidth: 220 }}>Your notes live in one place — recaps, words and highlights from every room.</p>
          <Link className="er-btn er-btn--ghost" style={{ padding: '10px 16px', textDecoration: 'none' }} to="/notes">Open notes</Link>
        </div>
      </div>

      {showCreateRoom && <CreateRoomModal onClose={() => setShowCreateRoom(false)} onRoomCreated={handleRoomCreated} />}
    </div>
  );
}
