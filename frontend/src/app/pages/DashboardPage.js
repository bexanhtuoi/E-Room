import { AppShell } from '../../components/layout/AppShell';
import { AIAssistantScaffold } from '../../features/ai/AIAssistantScaffold';
import { DashboardOverview } from '../../features/dashboard/DashboardOverview';
import { RoomList } from '../../features/rooms/RoomList';
import { TagPanel } from '../../features/tags/TagPanel';

export function DashboardPage() {
  return (
    <AppShell>
      <DashboardOverview />
      <div className="grid-two-columns">
        <RoomList />
        <TagPanel />
      </div>
      <AIAssistantScaffold />
    </AppShell>
  );
}
