import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { HiArrowRightOnRectangle, HiBell, HiBookOpen, HiCalendarDays, HiChartBar, HiDocumentText, HiHome, HiPlusCircle, HiShieldCheck, HiUserGroup } from 'react-icons/hi2';
import { useAuth } from '../AuthContext';
import { fetchJson } from '../../lib/api';
import { queryClient } from '../../lib/queryClient';
import { useSubscriptionStore } from '../../stores/subscriptionStore';
import { CreateRoomModal } from '../../features/rooms/CreateRoomModal';
import { Face, avatarFaceProps } from '../../components/common/Faces';
import { OverviewSection } from '../../features/profile/OverviewSection';
import { RoomsSection } from '../../features/profile/RoomsSection';
import { SessionsSection } from '../../features/profile/SessionsSection';
import { UsageSection } from '../../features/profile/UsageSection';
import { ActivitySection } from '../../features/profile/ActivitySection';
import { DocumentsSection } from '../../features/profile/DocumentsSection';
import { NotificationsSection } from '../../features/profile/NotificationsSection';
import { SettingsSection } from '../../features/profile/SettingsSection';
import '../../styles/ProfilePage.css';

const NAV_MAIN = [
  { key: 'overview', label: 'Overview', icon: HiHome },
  { key: 'rooms', label: 'My rooms', icon: HiUserGroup },
  { key: 'sessions', label: 'Sessions', icon: HiCalendarDays },
  { key: 'activity', label: 'Activity', icon: HiBookOpen },
  { key: 'usage', label: 'Usage', icon: HiChartBar },
  { key: 'documents', label: 'Documents', icon: HiDocumentText },
];

const NAV_BOTTOM = [
  { key: 'notifications', label: 'Notifications', icon: HiBell },
  { key: 'settings', label: 'Settings', icon: HiShieldCheck },
];

const PAGEHEAD = {
  overview: { crumb: 'Workspace', title: 'Overview', desc: 'Your learning pulse at a glance.' },
  rooms: { crumb: 'Workspace', title: 'My rooms', desc: 'Rooms you host and rooms you speak in.' },
  sessions: { crumb: 'Workspace', title: 'Sessions', desc: 'Every finished room, with what you said in each.' },
  activity: { crumb: 'Workspace', title: 'Activity', desc: 'Your full message timeline, newest first.' },
  usage: { crumb: 'Workspace', title: 'Usage', desc: 'Streaks, rhythms and favourite topics.' },
  documents: { crumb: 'Workspace', title: 'Documents', desc: 'Files attached to your learning.' },
  notifications: { crumb: 'Workspace', title: 'Notifications', desc: 'Matches, recaps and reviews.' },
  settings: { crumb: 'Workspace', title: 'Settings', desc: 'Identity, avatar, preferences and account.' },
};

function tierLabel(tier) {
  if (tier === 'pro_plus') return 'Pro+';
  if (tier === 'pro') return 'Pro';
  return 'Free';
}

export function ProfilePage() {
  const { user, setUser, logout } = useAuth();
  const navigate = useNavigate();
  const [activeSection, setActiveSection] = useState('overview');
  const [collapsed, setCollapsed] = useState(false);
  const [showCreateRoom, setShowCreateRoom] = useState(false);
  const tier = useSubscriptionStore((state) => state.tier);

  const roomsQuery = useQuery({
    queryKey: ['rooms', 'list'],
    queryFn: () => fetchJson('/rooms/?limit=100'),
  });
  const rooms = Array.isArray(roomsQuery.data) ? roomsQuery.data : [];

  const activityQuery = useQuery({
    queryKey: ['user-messages', user?.id],
    queryFn: () => fetchJson(`/messages/?user_id=${user.id}&limit=100`),
    enabled: Boolean(user?.id),
  });
  const messages = Array.isArray(activityQuery.data) ? activityQuery.data : [];

  const msgCountQuery = useQuery({
    queryKey: ['messages', 'count', user?.id],
    queryFn: () => fetchJson(`/messages/count?user_id=${user.id}`).then((r) => r?.count ?? 0).catch(() => messages.length),
    enabled: Boolean(user?.id),
  });
  const messagesTotal = typeof msgCountQuery.data === 'number' ? msgCountQuery.data : messages.length;

  const notifQuery = useQuery({
    queryKey: ['notifications', 'mine'],
    queryFn: () => fetchJson('/notifications/?limit=50'),
    enabled: Boolean(user?.id),
  });
  const unreadCount = Array.isArray(notifQuery.data) ? notifQuery.data.filter((n) => !n.is_read).length : 0;

  const docsQuery = useQuery({
    queryKey: ['documents', 'list'],
    queryFn: () => fetchJson('/documents/?limit=100'),
    enabled: Boolean(user?.id),
  });
  const myDocs = Array.isArray(docsQuery.data) ? docsQuery.data.filter((d) => String(d.user_id) === String(user?.id)) : [];

  const hostedRooms = rooms.filter((r) => String(r.host_id) === String(user?.id));
  const messagesByRoom = new Map();
  for (const m of messages) {
    if (!messagesByRoom.has(m.room_id)) messagesByRoom.set(m.room_id, []);
    messagesByRoom.get(m.room_id).push(m);
  }
  const joinedRooms = rooms.filter((r) => String(r.host_id) !== String(user?.id) && messagesByRoom.has(r.id));
  const myRooms = [...hostedRooms, ...joinedRooms];
  const liveRooms = myRooms.filter((r) => r.status === 'active');
  const pastSessions = rooms.filter((r) => r.status === 'ended' && (String(r.host_id) === String(user?.id) || messagesByRoom.has(r.id)));

  function handleRoomCreated(room) {
    queryClient.invalidateQueries({ queryKey: ['rooms', 'list'] });
    queryClient.invalidateQueries({ queryKey: ['rooms'] });
    setShowCreateRoom(false);
    if (room?.id) navigate(`/rooms/${room.id}`);
  }

  function handleProfileSaved(updated) {
    if (!updated) return;
    setUser({
      ...user,
      full_name: updated.full_name ?? user.full_name,
      english_level: updated.english_level ?? user.english_level,
      avatar_url: updated.avatar_url ?? user.avatar_url,
    });
  }

  function handleRoomDeleted() {
    queryClient.invalidateQueries({ queryKey: ['rooms', 'list'] });
  }

  function handleSignOut() {
    logout();
    navigate('/login');
  }

  if (!user) return null;

  const head = PAGEHEAD[activeSection] || PAGEHEAD.overview;

  function navBtn(s, badge) {
    return (
      <button
        key={s.key}
        type="button"
        title={s.label}
        onClick={() => setActiveSection(s.key)}
        className={`portal-side__btn${activeSection === s.key ? ' is-active' : ''}`}
      >
        <s.icon size={18} /> <span className="portal-side__label">{s.label}</span>
        {badge > 0 && <span className="portal-count">{badge}</span>}
      </button>
    );
  }

  return (
    <div className={`portal-app${collapsed ? ' is-collapsed' : ''}`}>
      <aside className="portal-side" aria-label="Profile sections">
        <div className="portal-side__id">
          <span className="portal-side__avatar">
            <Face {...avatarFaceProps(user.avatar_url, user.full_name || user.email)} size={40} />
          </span>
          <div className="portal-side__id-text">
            <strong>{user.full_name || 'E-Room learner'}</strong>
            <span>{tierLabel(tier)} workspace</span>
          </div>
          <button type="button" className="portal-side__collapse" onClick={() => setCollapsed((v) => !v)} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
            {collapsed ? '»' : '«'}
          </button>
        </div>
        <nav className="portal-side__nav">
          <div className="portal-side__group">Menu</div>
          {NAV_MAIN.map((s) => navBtn(s))}
          <div className="portal-side__bottom">
            <div className="portal-side__group">General</div>
            {NAV_BOTTOM.map((s) => navBtn(s, s.key === 'notifications' ? unreadCount : 0))}
            <div className="portal-side__plan">
              <strong>{tierLabel(tier)} plan</strong>
              <span>Unlock recaps, voice and more.</span>
              <Link to="/pricing">Upgrade</Link>
            </div>
          </div>
        </nav>
        <div className="portal-side__user">
          <Face {...avatarFaceProps(user.avatar_url, user.full_name || user.email)} size={30} />
          <div className="portal-side__user-info">
            <strong>{user.full_name || 'E-Room learner'}</strong>
            <span>{user.email}</span>
          </div>
          <button type="button" className="portal-side__signout" title="Sign out" aria-label="Sign out" onClick={handleSignOut}>
            <HiArrowRightOnRectangle size={16} />
          </button>
        </div>
      </aside>

      <main className="portal-main">
        <div className="portal-pagehead">
          <div>
            <div className="portal-pagehead__crumb">{head.crumb} / {head.title}</div>
            <h1>{head.title}</h1>
            <p>{head.desc}</p>
          </div>
          <div className="portal-pagehead__actions">
            {(activeSection === 'overview' || activeSection === 'rooms') && (
              <button className="er-btn" onClick={() => setShowCreateRoom(true)}><HiPlusCircle size={16} /> New room</button>
            )}
          </div>
        </div>

        <div style={{ height: 16 }} />

        {activeSection === 'overview' && (
          <OverviewSection
            hostedRooms={hostedRooms}
            joinedRooms={joinedRooms}
            liveRooms={liveRooms}
            messages={messages}
            messagesTotal={messagesTotal}
            documentsCount={myDocs.length}
            onGo={setActiveSection}
          />
        )}
        {activeSection === 'rooms' && (
          <RoomsSection
            hostedRooms={hostedRooms}
            joinedRooms={joinedRooms}
            liveRooms={liveRooms}
            messagesByRoom={messagesByRoom}
            onCreateRoom={() => setShowCreateRoom(true)}
            onRoomDeleted={handleRoomDeleted}
          />
        )}
        {activeSection === 'sessions' && (
          <SessionsSection sessions={pastSessions} messagesByRoom={messagesByRoom} userId={user.id} />
        )}
        {activeSection === 'activity' && (
          <ActivitySection messages={messages} rooms={rooms} isLoading={activityQuery.isLoading} isError={activityQuery.isError} onRetry={activityQuery.refetch} />
        )}
        {activeSection === 'usage' && (
          <UsageSection messages={messages} messagesTotal={messagesTotal} hostedRooms={hostedRooms} joinedRooms={joinedRooms} pastSessions={pastSessions} />
        )}
        {activeSection === 'documents' && <DocumentsSection userId={user.id} />}
        {activeSection === 'notifications' && <NotificationsSection />}
        {activeSection === 'settings' && (
          <SettingsSection user={user} tierLabel={tierLabel(tier)} onSaved={handleProfileSaved} onSignOut={handleSignOut} />
        )}
      </main>

      {showCreateRoom && <CreateRoomModal onClose={() => setShowCreateRoom(false)} onRoomCreated={handleRoomCreated} />}
    </div>
  );
}
