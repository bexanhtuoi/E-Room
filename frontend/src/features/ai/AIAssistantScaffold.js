import { Card } from '../../components/ui/Card';

export function AIAssistantScaffold() {
  return (
    <Card title="AI scaffold" subtitle="Keep the contract, delay the heavy infrastructure">
      <div className="ai-grid">
        <div className="ai-box">
          <strong>Heartbeat</strong>
          <p>UI and event contracts can attach here later.</p>
        </div>
        <div className="ai-box">
          <strong>Expert</strong>
          <p>RAG and Web Search stay behind the infrastructure milestone.</p>
        </div>
        <div className="ai-box">
          <strong>Correction</strong>
          <p>Message and transcript resources are ready for later enrichment.</p>
        </div>
      </div>
    </Card>
  );
}
