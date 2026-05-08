import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppShell } from '../../components/layout/AppShell';
import { AIAssistantScaffold } from '../../features/ai/AIAssistantScaffold';
import { DashboardOverview } from '../../features/dashboard/DashboardOverview';
import { InfrastructurePanel } from '../../features/dashboard/InfrastructurePanel';
import { RealtimeRoomPanel } from '../../features/realtime/RealtimeRoomPanel';
import { RoomList } from '../../features/rooms/RoomList';
import { TagPanel } from '../../features/tags/TagPanel';
import { useAuth } from '../AuthContext';

export function DashboardPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [refreshKey, setRefreshKey] = useState(0);

  function handleSelectRoom(room) {
    navigate(`/rooms/${room.id}`);
  }

  return (
    <AppShell onRoomCreated={() => setRefreshKey((k) => k + 1)} user={user} onLogout={logout}>
      <DashboardOverview key={`health-${refreshKey}`} />
      <InfrastructurePanel />
      <div className="two-col">
        <RoomList key={`rooms-${refreshKey}`} onSelectRoom={handleSelectRoom} />
        <TagPanel />
      </div>
      <RealtimeRoomPanel />
      <AIAssistantScaffold />
    </AppShell>
  );
}
