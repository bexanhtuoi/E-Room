import { Card } from '../../components/ui/Card';

export function AIAssistantScaffold() {
  return (
    <Card title="AI modules" subtitle="Scaffolded contracts. Implementation follows after infrastructure is stable.">
      <div className="ai-grid-scaffold">
        <div className="ai-box-scaffold">
          <strong>Heartbeat</strong>
          <p>UI and event contracts attach here later.</p>
        </div>
        <div className="ai-box-scaffold">
          <strong>Expert</strong>
          <p>RAG and search remain behind the infrastructure milestone.</p>
        </div>
        <div className="ai-box-scaffold">
          <strong>Correction</strong>
          <p>Message and transcript resources are ready for enrichment.</p>
        </div>
      </div>
    </Card>
  );
}
