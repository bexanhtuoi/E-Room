// Backend tra URL noi bo docker (ws://livekit:7880) — doi host thanh host
// cua browser nhung GIU NGUYEN port (tung co bug append port 2 lan).
// URL public san (vd LiveKit Cloud wss://...livekit.cloud) GIU NGUYEN,
// khong duoc rewrite — tung co bug ep ve funnel root gay 502.
export function toBrowserLivekitUrl(backendUrl) {
  const host = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
  const fallback = host.endsWith('.ts.net') ? `wss://${host}` : `ws://${host}:7880`;
  if (!backendUrl || typeof backendUrl !== 'string') return fallback;
  try {
    const u = new URL(backendUrl.replace(/^ws/, 'http'));
    if (['livekit', 'lk', 'localhost', '127.0.0.1'].includes(u.hostname)) {
      // Host noi bo → map sang host browser. Qua funnel (*.ts.net) thi
      // signaling di chung cong 443 (wss), serve path /rtc + /validate.
      if (host.endsWith('.ts.net')) {
        return `wss://${host}`;
      }
      u.hostname = host;
    }
    // Cloud (livekit.cloud) khong co port trong URL → dung port mac dinh,
    // khong append :7880 bua.
    const port = u.port ? `:${u.port}` : '';
    const scheme = u.protocol.startsWith('https') ? 'wss' : 'ws';
    return `${scheme}://${u.hostname}${port}`;
  } catch {
    return fallback;
  }
}
