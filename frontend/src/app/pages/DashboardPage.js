import { AppShell } from '../../components/layout/AppShell';
import { AIAssistantScaffold } from '../../features/ai/AIAssistantScaffold';
import { AuthPanel } from '../../features/auth/AuthPanel';
import { DashboardOverview } from '../../features/dashboard/DashboardOverview';
import { InfrastructurePanel } from '../../features/dashboard/InfrastructurePanel';
import { RealtimeRoomPanel } from '../../features/realtime/RealtimeRoomPanel';
import { RoomList } from '../../features/rooms/RoomList';
import { RoomSocketPreview } from '../../features/rooms/RoomSocketPreview';
import { TagPanel } from '../../features/tags/TagPanel';

export function DashboardPage() {
  return (
    <AppShell>
      <DashboardOverview />
      <InfrastructurePanel />
      <AuthPanel />
      <div className="grid-two-columns">
        <RoomList />
        <TagPanel />
      </div>
      <div className="grid-two-columns">
        <RoomSocketPreview />
        <RealtimeRoomPanel />
      </div>
      <AIAssistantScaffold />
    </AppShell>
  );
}
