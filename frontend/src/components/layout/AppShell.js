export function AppShell({ children }) {
  return (
    <main className="app-shell">
      <section className="hero-panel">
        <span className="eyebrow">E-Room</span>
        <h1>Realtime English rooms with clean infrastructure first</h1>
        <p>Core backend flows are live. AI modules stay scaffolded until infrastructure is stable.</p>
      </section>
      <section className="content-stack">{children}</section>
    </main>
  );
}
