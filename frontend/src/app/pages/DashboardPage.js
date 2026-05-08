import { AppShell } from '../../components/layout/AppShell';
import { AIAssistantScaffold } from '../../features/ai/AIAssistantScaffold';
import { DashboardOverview } from '../../features/dashboard/DashboardOverview';
import { InfrastructurePanel } from '../../features/dashboard/InfrastructurePanel';
import { RoomList } from '../../features/rooms/RoomList';
import { RoomSocketPreview } from '../../features/rooms/RoomSocketPreview';
import { TagPanel } from '../../features/tags/TagPanel';

export function DashboardPage() {
  return (
    <AppShell>
      <DashboardOverview />
      <InfrastructurePanel />
      <div className="grid-two-columns">
        <RoomList />
        <TagPanel />
      </div>
      <RoomSocketPreview />
      <AIAssistantScaffold />
    </AppShell>
  );
}
