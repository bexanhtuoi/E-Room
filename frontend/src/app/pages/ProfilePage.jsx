import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { HiBell, HiBookOpen, HiCalendarDays, HiChartBar, HiDocumentText, HiHome, HiShieldCheck, HiUserGroup } from 'react-icons/hi2';
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

function tierLabel(tier) {
  if (tier === 'pro_plus') return 'Pro+';
  if (tier === 'pro') return 'Pro';
  return 'Free';
}

export function ProfilePage() {
  const { user, setUser, logout } = useAuth();
  const navigate = useNavigate();
  const [activeSection, setActiveSection] = useState('overview');
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

  if (!user) return null;

  function navBtn(s, badge) {
    return (
      <button
        key={s.key}
        type="button"
        onClick={() => setActiveSection(s.key)}
        className={`portal-side__btn${activeSection === s.key ? ' is-active' : ''}`}
      >
        <s.icon size={17} /> {s.label}
        {badge > 0 && <span className="portal-count">{badge}</span>}
      </button>
    );
  }

  return (
    <div className="portal-app">
      <aside className="portal-side" aria-label="Profile sections">
        <div className="portal-side__id">
          <Face {...avatarFaceProps(user.avatar_url, user.full_name || user.email)} size={40} />
          <div className="portal-side__id-text">
            <strong>{user.full_name || 'E-Room learner'}</strong>
            <span>{tierLabel(tier)} workspace</span>
          </div>
        </div>
        <nav className="portal-side__nav">
          <div className="portal-side__group">Menu</div>
          {NAV_MAIN.map((s) => navBtn(s))}
          <div className="portal-side__bottom">
            {NAV_BOTTOM.map((s) => navBtn(s, s.key === 'notifications' ? unreadCount : 0))}
            <div className="portal-side__plan">
              <strong>{tierLabel(tier)} plan</strong>
              <span>Unlock recaps, voice and more.</span>
              <Link to="/pricing">Upgrade</Link>
            </div>
          </div>
        </nav>
      </aside>

      <main className="portal-main">
        {activeSection === 'overview' && (
          <OverviewSection
            user={user}
            hostedRooms={hostedRooms}
            joinedRooms={joinedRooms}
            messages={messages}
            documentsCount={myDocs.length}
            onCreateRoom={() => setShowCreateRoom(true)}
            onGo={setActiveSection}
          />
        )}
        {activeSection === 'rooms' && (
          <RoomsSection
            hostedRooms={hostedRooms}
            joinedRooms={joinedRooms}
            messagesByRoom={messagesByRoom}
            onCreateRoom={() => setShowCreateRoom(true)}
            onRoomDeleted={handleRoomDeleted}
          />
        )}
        {activeSection === 'sessions' && (
          <SessionsSection sessions={pastSessions} messagesByRoom={messagesByRoom} userId={user.id} />
        )}
        {activeSection === 'usage' && (
          <UsageSection messages={messages} hostedRooms={hostedRooms} joinedRooms={joinedRooms} />
        )}
        {activeSection === 'activity' && (
          <ActivitySection messages={messages} isLoading={activityQuery.isLoading} isError={activityQuery.isError} onRetry={activityQuery.refetch} />
        )}
        {activeSection === 'documents' && <DocumentsSection userId={user.id} />}
        {activeSection === 'notifications' && <NotificationsSection />}
        {activeSection === 'settings' && (
          <SettingsSection user={user} onSaved={handleProfileSaved} onSignOut={() => { logout(); navigate('/login'); }} />
        )}
      </main>

      {showCreateRoom && <CreateRoomModal onClose={() => setShowCreateRoom(false)} onRoomCreated={handleRoomCreated} />}
    </div>
  );
}
