import { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { HiAcademicCap, HiArrowRightOnRectangle, HiBell, HiCalendarDays, HiClock, HiHome, HiUserGroup } from 'react-icons/hi2';
import { useAuth } from '../AuthContext';
import { fetchJson } from '../../lib/api';
import { queryClient } from '../../lib/queryClient';
import { useSubscriptionStore } from '../../stores/subscriptionStore';
import { CreateRoomModal } from '../../features/rooms/CreateRoomModal';
import { Face, avatarFaceProps } from '../../components/common/Faces';
import { OverviewSection } from '../../features/profile/OverviewSection';
import { RoomsSection } from '../../features/profile/RoomsSection';
import { SessionsSection } from '../../features/profile/SessionsSection';
import { ScheduleSection } from '../../features/profile/ScheduleSection';
import { AssessmentSection } from '../../features/profile/AssessmentSection';
import { ProfileInfoSection } from '../../features/profile/ProfileInfoSection';
import { NotificationsPopup } from '../../features/profile/NotificationsPopup';
import '../../styles/ProfilePage.css';

const NAV_MAIN = [
  { key: 'overview', label: 'Overview', to: '/overview', icon: HiHome },
  { key: 'rooms', label: 'My rooms', to: '/my-rooms', icon: HiUserGroup },
  { key: 'sessions', label: 'Session', to: '/session', icon: HiCalendarDays },
  { key: 'schedule', label: 'Schedule', to: '/schedule', icon: HiClock },
  { key: 'assessment', label: 'Assessment', to: '/assessment', icon: HiAcademicCap },
];

const PAGEHEAD = {
  overview: { crumb: 'Workspace', title: 'Overview', desc: 'Your learning pulse at a glance.' },
  rooms: { crumb: 'Workspace', title: 'My rooms', desc: 'Rooms you created.' },
  sessions: { crumb: 'Workspace', title: 'Session', desc: 'Every finished room, with what you said in each.' },
  schedule: { crumb: 'Workspace', title: 'Schedule', desc: 'Live now and open rooms waiting for you.' },
  assessment: { crumb: 'Workspace', title: 'Assessment', desc: 'Replay what you said and level up your English.' },
  me: { crumb: 'Workspace', title: 'Profile', desc: 'Your public profile — click the pencil to edit anything.' },
};

function tierLabel(tier) {
  if (tier === 'pro_plus') return 'Pro+';
  if (tier === 'pro') return 'Pro';
  return 'Free';
}

export function ProfilePage({ section = 'overview' }) {
  const { user, setUser, logout } = useAuth();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const [sideOpen, setSideOpen] = useState(false);
  const [showCreateRoom, setShowCreateRoom] = useState(false);
  const [showNotif, setShowNotif] = useState(false);
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

  const statsQuery = useQuery({
    queryKey: ['users', 'me', 'stats'],
    queryFn: () => fetchJson('/users/me/stats'),
    enabled: Boolean(user?.id),
  });
  const stats = statsQuery.data ?? null;

  const notifQuery = useQuery({
    queryKey: ['notifications', 'mine'],
    queryFn: () => fetchJson('/notifications/?limit=50'),
    enabled: Boolean(user?.id),
  });
  const unreadCount = Array.isArray(notifQuery.data) ? notifQuery.data.filter((n) => !n.is_read).length : 0;

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
      headline: updated.headline ?? user.headline,
      bio: updated.bio ?? user.bio,
      location: updated.location ?? user.location,
      website: updated.website ?? user.website,
      skills: updated.skills ?? user.skills,
      experience: updated.experience ?? user.experience,
      education: updated.education ?? user.education,
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

  const head = PAGEHEAD[section] || PAGEHEAD.overview;

  return (
    <div className={`portal-app${collapsed ? ' is-collapsed' : ''}${sideOpen ? ' side-open' : ''}`}>
      {sideOpen && <div className="pf-backdrop" onClick={() => setSideOpen(false)} aria-hidden="true" />}
      <aside className="portal-side" aria-label="Profile sections">
        <div className="portal-side__id">
          <span className="portal-side__logo" aria-hidden="true">E</span>
          <div className="portal-side__id-text">
            <strong>E-Room</strong>
            <span>{tierLabel(tier)} workspace</span>
          </div>
          <button type="button" className="portal-side__collapse" onClick={() => setCollapsed((v) => !v)} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
            {collapsed ? '»' : '«'}
          </button>
        </div>
        <nav className="portal-side__nav">
          <div className="portal-side__group">Menu</div>
          {NAV_MAIN.map((s) => (
            <NavLink
              key={s.key}
              to={s.to}
              title={s.label}
              onClick={() => setSideOpen(false)}
              className={({ isActive }) => `portal-side__btn${isActive ? ' is-active' : ''}`}
            >
              <s.icon size={18} /> <span className="portal-side__label">{s.label}</span>
            </NavLink>
          ))}
          <div className="portal-side__bottom">
            <div className="portal-side__group">General</div>
            <button
              type="button"
              title="Notifications"
              onClick={() => setShowNotif(true)}
              className="portal-side__btn"
            >
              <HiBell size={18} /> <span className="portal-side__label">Notifications</span>
              {unreadCount > 0 && <span className="portal-count">{unreadCount}</span>}
            </button>
            <div className="portal-side__plan">
              <strong>{tierLabel(tier)} plan</strong>
              <span>Unlock recaps, voice and more.</span>
              <Link to="/pricing">Upgrade</Link>
            </div>
          </div>
        </nav>
        <div className="portal-side__user">
          <Link to="/profile" className="portal-side__profile" title="My profile">
            <Face {...avatarFaceProps(user.avatar_url, user.full_name || user.email)} size={32} />
            <span className="portal-side__user-info">
              <strong>{user.full_name || 'E-Room learner'}</strong>
              <span>{user.email}</span>
            </span>
          </Link>
          <button type="button" className="portal-side__signout" title="Sign out" aria-label="Sign out" onClick={handleSignOut}>
            <HiArrowRightOnRectangle size={15} />
          </button>
        </div>
      </aside>

      <main className="portal-main">
        <button
          type="button" className="pf-drawerbtn" aria-label="Open menu"
          onClick={() => setSideOpen(true)}
        >
          ☰ Menu
        </button>
        <div className="portal-pagehead">
          <div>
            <div className="portal-pagehead__crumb">{head.crumb} / {head.title}</div>
            <h1>{head.title}</h1>
            <p>{head.desc}</p>
          </div>
          <div className="portal-pagehead__actions" />
        </div>

        <div style={{ height: 16 }} />

        {section === 'overview' && (
          <OverviewSection
            userName={(user.full_name || '').split(' ')[0]}
            hostedRooms={hostedRooms}
            joinedRooms={joinedRooms}
            liveRooms={liveRooms}
            messages={messages}
            stats={stats}
            rooms={rooms}
            activityLoading={activityQuery.isLoading}
            activityError={activityQuery.isError}
            activityRetry={activityQuery.refetch}
            onGo={(key) => navigate(key === 'rooms' ? '/my-rooms' : key === 'sessions' ? '/session' : `/${key}`)}
            onCreateRoom={() => setShowCreateRoom(true)}
          />
        )}
        {section === 'rooms' && (
          <RoomsSection
            hostedRooms={hostedRooms}
            liveRooms={liveRooms}
            messagesByRoom={messagesByRoom}
            onRoomDeleted={handleRoomDeleted}
          />
        )}
        {section === 'sessions' && (
          <SessionsSection sessions={pastSessions} messagesByRoom={messagesByRoom} userId={user.id} />
        )}
        {section === 'schedule' && (
          <ScheduleSection rooms={rooms} hostedRooms={hostedRooms} onCreateRoom={() => setShowCreateRoom(true)} />
        )}
        {section === 'assessment' && (
          <AssessmentSection rooms={rooms} messagesByRoom={messagesByRoom} userId={user.id} />
        )}
        {section === 'me' && (
          <ProfileInfoSection
            user={user}
            tierLabel={tierLabel(tier)}
            onSaved={handleProfileSaved}
            onSignOut={handleSignOut}
          />
        )}
      </main>

      {showCreateRoom && <CreateRoomModal onClose={() => setShowCreateRoom(false)} onRoomCreated={handleRoomCreated} />}
      {showNotif && <NotificationsPopup onClose={() => setShowNotif(false)} />}
    </div>
  );
}
