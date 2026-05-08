import { useState } from 'react';
import { AppShell } from '../../components/layout/AppShell';
import { AIAssistantScaffold } from '../../features/ai/AIAssistantScaffold';
import { DashboardOverview } from '../../features/dashboard/DashboardOverview';
import { InfrastructurePanel } from '../../features/dashboard/InfrastructurePanel';
import { RealtimeRoomPanel } from '../../features/realtime/RealtimeRoomPanel';
import { RoomDetail } from '../../features/rooms/RoomDetail';
import { RoomList } from '../../features/rooms/RoomList';
import { TagPanel } from '../../features/tags/TagPanel';

export function DashboardPage() {
  const [selectedRoom, setSelectedRoom] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <AppShell onRoomCreated={() => setRefreshKey((k) => k + 1)}>
      <DashboardOverview key={`health-${refreshKey}`} />
      <InfrastructurePanel />

      {selectedRoom ? (
        <RoomDetail room={selectedRoom} onBack={() => setSelectedRoom(null)} />
      ) : (
        <>
          <div className="two-col">
            <RoomList key={`rooms-${refreshKey}`} onSelectRoom={setSelectedRoom} />
            <TagPanel />
          </div>
          <RealtimeRoomPanel />
          <AIAssistantScaffold />
        </>
      )}
    </AppShell>
  );
}
