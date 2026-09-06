import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { HiBell, HiBookOpen, HiCreditCard, HiDocumentText, HiHome, HiShieldCheck, HiUserGroup } from 'react-icons/hi2';
import { useAuth } from '../AuthContext';
import { fetchJson } from '../../lib/api';
import { queryClient } from '../../lib/queryClient';
import { useSubscriptionStore } from '../../stores/subscriptionStore';
import { CreateRoomModal } from '../../features/rooms/CreateRoomModal';
import { Face, avatarFaceProps } from '../../components/common/Faces';
import { OverviewSection } from '../../features/profile/OverviewSection';
import { RoomsSection } from '../../features/profile/RoomsSection';
import { ActivitySection } from '../../features/profile/ActivitySection';
import { DocumentsSection } from '../../features/profile/DocumentsSection';
import { NotificationsSection } from '../../features/profile/NotificationsSection';
import { SubscriptionSection } from '../../features/profile/SubscriptionSection';
import { SettingsSection } from '../../features/profile/SettingsSection';
import '../../styles/ProfilePage.css';

const SECTIONS = [
  { key: 'overview', label: 'Overview', icon: HiHome },
  { key: 'rooms', label: 'My rooms', icon: HiUserGroup },
  { key: 'activity', label: 'Activity', icon: HiBookOpen },
  { key: 'documents', label: 'Documents', icon: HiDocumentText },
  { key: 'notifications', label: 'Notifications', icon: HiBell },
  { key: 'subscription', label: 'Subscription', icon: HiCreditCard },
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

  return (
    <div className="portal">
      <div className="er-container portal-container">
        <header className="portal-header">
          <Face {...avatarFaceProps(user.avatar_url, user.full_name || user.email)} size={64} />
          <div className="portal-header__main">
            <h1>{user.full_name || 'E-Room learner'}</h1>
            <p>{user.email}</p>
          </div>
          <div className="portal-header__stats">
            <div><strong>{messages.length}</strong><span>messages</span></div>
            <div><strong>{tierLabel(tier)}</strong><span>plan</span></div>
          </div>
        </header>

        <div className="portal-layout">
          <aside className="portal-sidebar" aria-label="Profile sections">
            <div className="portal-sidebar__identity">
              <Face {...avatarFaceProps(user.avatar_url, user.full_name || user.email)} size={36} />
              <div className="portal-sidebar__identity-text">
                <strong>{user.full_name || 'E-Room learner'}</strong>
                <span>{user.email}</span>
              </div>
            </div>
            <nav className="portal-sidebar__nav">
              {SECTIONS.map((s) => (
                <button
                  key={s.key}
                  type="button"
                  onClick={() => setActiveSection(s.key)}
                  className={`portal-sidebar__btn${activeSection === s.key ? ' is-active' : ''}`}
                >
                  <s.icon size={16} /> {s.label}
                  {s.key === 'notifications' && unreadCount > 0 && <span className="portal-count">{unreadCount}</span>}
                </button>
              ))}
            </nav>
            <div className="portal-sidebar__foot">
              <span className="portal-flag is-solid">{tierLabel(tier)} plan</span>
            </div>
          </aside>

          <main className="portal-main">
            {activeSection === 'overview' && (
              <OverviewSection
                user={user}
                hostedRooms={hostedRooms}
                joinedRooms={joinedRooms}
                messages={messages}
                documents={myDocs}
                tierLabel={tierLabel(tier)}
                onCreateRoom={() => setShowCreateRoom(true)}
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
            {activeSection === 'activity' && (
              <ActivitySection messages={messages} isLoading={activityQuery.isLoading} isError={activityQuery.isError} onRetry={activityQuery.refetch} />
            )}
            {activeSection === 'documents' && <DocumentsSection userId={user.id} />}
            {activeSection === 'notifications' && <NotificationsSection />}
            {activeSection === 'subscription' && <SubscriptionSection tier={tier} />}
            {activeSection === 'settings' && (
              <SettingsSection user={user} onSaved={handleProfileSaved} onSignOut={() => { logout(); navigate('/login'); }} />
            )}
          </main>
        </div>
      </div>

      {showCreateRoom && <CreateRoomModal onClose={() => setShowCreateRoom(false)} onRoomCreated={handleRoomCreated} />}
    </div>
  );
}
