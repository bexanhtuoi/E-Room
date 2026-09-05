import { describe, expect, it } from 'vitest';

import { toBrowserLivekitUrl } from './livekitUrl';

describe('toBrowserLivekitUrl', () => {
  it('rewrites the docker hostname but keeps the port exactly once', () => {
    expect(toBrowserLivekitUrl('ws://livekit:7880')).toBe('ws://localhost:7880');
  });

  it('keeps an already-correct localhost url untouched', () => {
    expect(toBrowserLivekitUrl('ws://localhost:7880')).toBe('ws://localhost:7880');
  });

  it('keeps a custom backend port', () => {
    expect(toBrowserLivekitUrl('ws://livekit:9999')).toBe('ws://localhost:9999');
  });

  it('falls back to the default url for missing or invalid input', () => {
    expect(toBrowserLivekitUrl('')).toBe('ws://localhost:7880');
    expect(toBrowserLivekitUrl(undefined)).toBe('ws://localhost:7880');
    expect(toBrowserLivekitUrl('not a url')).toBe('ws://localhost:7880');
  });
});
