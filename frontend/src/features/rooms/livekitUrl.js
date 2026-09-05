// Backend tra URL noi bo docker (ws://livekit:7880) — doi host thanh host
// cua browser nhung GIU NGUYEN port (tung co bug append port 2 lan).
export function toBrowserLivekitUrl(backendUrl) {
  const host = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
  const fallback = `ws://${host}:7880`;
  if (!backendUrl || typeof backendUrl !== 'string') return fallback;
  try {
    const u = new URL(backendUrl.replace(/^ws/, 'http'));
    if (['livekit', 'lk', 'localhost', '127.0.0.1'].includes(u.hostname)) {
      u.hostname = host;
    }
    const port = u.port || '7880';
    const scheme = u.protocol.startsWith('https') ? 'wss' : 'ws';
    return `${scheme}://${u.hostname}:${port}`;
  } catch {
    return fallback;
  }
}
