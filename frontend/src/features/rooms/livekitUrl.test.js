import { describe, expect, it } from 'vitest';

import { toBrowserLivekitUrl } from './livekitUrl';

describe('toBrowserLivekitUrl', () => {
  it('rewrites the docker hostname but keeps the port exactly once', () => {
    expect(toBrowserLivekitUrl('ws://livekit:7880')).toBe('ws://localhost:7880');
  });

  it('keeps an already-correct localhost url untouched', () => {
    expect(toBrowserLivekitUrl('ws://localhost:7880')).toBe('ws://localhost:7880');
  });

  it('keeps LiveKit Cloud url without appending a port', () => {
    expect(toBrowserLivekitUrl('wss://myproj.livekit.cloud')).toBe('wss://myproj.livekit.cloud');
  });

  it('keeps a custom backend port', () => {
    expect(toBrowserLivekitUrl('ws://livekit:9999')).toBe('ws://localhost:9999');
  });

  it('falls back to the default url for missing or invalid input', () => {
    expect(toBrowserLivekitUrl('')).toBe('ws://localhost:7880');
    expect(toBrowserLivekitUrl(undefined)).toBe('ws://localhost:7880');
    expect(toBrowserLivekitUrl('not a url')).toBe('ws://localhost:7880');
  });

  it('routes Tailscale Funnel visitors to funnel root for internal urls', () => {
    const original = window.location;
    Object.defineProperty(window, 'location', {
      value: { hostname: 'pc.tail9f35e1.ts.net' },
      writable: true,
    });
    try {
      expect(toBrowserLivekitUrl('ws://livekit:7880')).toBe('wss://pc.tail9f35e1.ts.net');
    } finally {
      Object.defineProperty(window, 'location', { value: original, writable: true });
    }
  });

  it('never rewrites a public cloud url, even for funnel visitors', () => {
    const original = window.location;
    Object.defineProperty(window, 'location', {
      value: { hostname: 'pc.tail9f35e1.ts.net' },
      writable: true,
    });
    try {
      expect(toBrowserLivekitUrl('wss://eroom-6ahxkoab.livekit.cloud')).toBe('wss://eroom-6ahxkoab.livekit.cloud');
    } finally {
      Object.defineProperty(window, 'location', { value: original, writable: true });
    }
  });
});
