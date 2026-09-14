import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../lib/api', () => ({ fetchJson: vi.fn() }));

import { fetchJson } from '../../lib/api';
import { compareIds, useRoomChat } from './useRoomChat';

let nextId = 100;

beforeEach(() => {
  nextId = 100;
  fetchJson.mockReset();
  fetchJson.mockImplementation(async (path, options = {}) => {
    if (path.startsWith('/messages/?')) return [];
    if (path === '/messages/' && options.method === 'POST') {
      const body = JSON.parse(options.body);
      nextId += 1;
      return { id: nextId, room_id: body.room_id, user_id: 7, role: 'user', text: body.text, created_at: new Date().toISOString() };
    }
    if (path.startsWith('/users/')) return { id: 7, full_name: 'Tester' };
    return [];
  });
});

async function renderChat() {
  let hook;
  await act(async () => {
    hook = renderHook(() => useRoomChat('30008'));
  });
  await act(async () => {});
  return hook;
}

describe('useRoomChat live flow', () => {
  it('sends a message and shows it', async () => {
    const { result, unmount } = await renderChat();
    await act(async () => {
      await result.current.send('hello room');
    });
    expect(result.current.items.some((it) => it.text === 'hello room')).toBe(true);
    unmount();
  });

  it('@ai shows thinking placeholder, streams, then settles thinking on new stream', async () => {
    const { result, unmount } = await renderChat();
    await act(async () => {
      await result.current.send('@ai hi');
    });
    expect(result.current.items.some((it) => it.id === 'ai-pending')).toBe(true);

    act(() => {
      result.current.handleLiveData({ type: 'ai_stream', stream_id: 's1', room_id: 30008, chunk: 'Searching', thinking: true, is_final: false });
      result.current.handleLiveData({ type: 'ai_stream', stream_id: 's1', room_id: 30008, chunk: 'Hel', is_final: false });
    });
    let first = result.current.items.find((it) => it.id === 'ai-s1');
    expect(first?.streaming).toBe(true);
    expect(first?.thinkingText).toBe('Searching');
    expect(result.current.items.some((it) => it.id === 'ai-pending')).toBe(false);

    // Stream thu 2 bat dau → stream 1 tat streaming (thinking tu dong dong)
    act(() => {
      result.current.handleLiveData({ type: 'ai_stream', stream_id: 's2', room_id: 30008, chunk: 'Yo', is_final: false });
    });
    first = result.current.items.find((it) => it.id === 'ai-s1');
    const second = result.current.items.find((it) => it.id === 'ai-s2');
    expect(first?.streaming).toBe(false);
    expect(second?.streaming).toBe(true);

    // Final stream 2 → khong con bubble streaming nao
    act(() => {
      result.current.handleLiveData({ type: 'ai_stream', stream_id: 's2', room_id: 30008, is_final: true });
    });
    expect(result.current.items.some((it) => it.streaming)).toBe(false);
    unmount();
  });

  it('supersedes unfinished bubble when retry stream shares job_id', async () => {
    const { result, unmount } = await renderChat();
    act(() => {
      result.current.handleLiveData({ type: 'ai_stream', stream_id: 'r1', job_id: 'job9', room_id: 30008, chunk: 'Hel', is_final: false });
    });
    expect(result.current.items.find((it) => it.id === 'ai-r1')?.streaming).toBe(true);

    act(() => {
      result.current.handleLiveData({ type: 'ai_stream', stream_id: 'r2', job_id: 'job9', room_id: 30008, chunk: 'Yo', is_final: false });
    });
    expect(result.current.items.some((it) => it.id === 'ai-r1')).toBe(false);
    expect(result.current.items.find((it) => it.id === 'ai-r2')?.text).toBe('Yo');

    act(() => {
      result.current.handleLiveData({ type: 'ai_stream', stream_id: 'r2', job_id: 'job9', room_id: 30008, is_final: true });
    });
    const settled = result.current.items.filter((it) => it.kind === 'ai' && !it.streaming);
    expect(settled).toHaveLength(1);
    expect(settled[0].text).toBe('Yo');
    unmount();
  });

  it('keeps bubbles from different jobs', async () => {
    const { result, unmount } = await renderChat();
    act(() => {
      result.current.handleLiveData({ type: 'ai_stream', stream_id: 'a1', job_id: 'jobA', room_id: 30008, chunk: 'AAA', is_final: false });
      result.current.handleLiveData({ type: 'ai_stream', stream_id: 'b1', job_id: 'jobB', room_id: 30008, chunk: 'BBB', is_final: false });
    });
    expect(result.current.items.find((it) => it.id === 'ai-a1')?.text).toBe('AAA');
    expect(result.current.items.find((it) => it.id === 'ai-b1')?.text).toBe('BBB');
    unmount();
  });

  it('sorts numeric ids numerically so newest survives slice in busy rooms', () => {
    // "30008" < "999" neu so string — phai so number thi tin moi (id lon)
    // moi dung cuoi va khong bi slice(-200) cat mat trong phong dong.
    expect(compareIds(999, 30008)).toBeLessThan(0);
    expect(compareIds(30008, 999)).toBeGreaterThan(0);
    expect(compareIds(60, 999)).toBeLessThan(0);
    expect(compareIds('ai-s1', 30008)).toBeGreaterThan(0);
    expect(compareIds('ai-pending', 'ai-s1')).toBeLessThan(0);
  });

  it('stamps the @ai source id onto its live bubbles for instant quote', async () => {
    const { result, unmount } = await renderChat();
    await act(async () => {
      await result.current.send('@ai what time is it');
    });
    const askedId = result.current.items.find((it) => it.text === '@ai what time is it')?.id;
    expect(askedId).toBeDefined();

    act(() => {
      result.current.handleLiveData({ type: 'ai_stream', stream_id: 'sq', room_id: 30008, chunk: 'It is', is_final: false });
    });
    expect(result.current.items.find((it) => it.id === 'ai-sq')?.sourceId).toBe(askedId);

    act(() => {
      result.current.handleLiveData({ type: 'ai_stream', stream_id: 'sq', room_id: 30008, is_final: true });
    });
    expect(result.current.items.find((it) => it.id === 'ai-sq')?.sourceId).toBe(askedId);
    unmount();
  });

  it('keeps late-arriving DB messages at the bottom despite clock skew', async () => {
    vi.useFakeTimers();
    try {
      const { result, unmount } = await renderChat();
      await act(async () => {
        await result.current.send('hello first');
      });
      // Poll dem ve dap an AI nhung created_at server lech 7 tieng ve qua khu
      const sevenHoursAgo = new Date(Date.now() - 7 * 3600 * 1000).toISOString();
      fetchJson.mockImplementation(async (path) => {
        if (path.startsWith('/messages/?')) {
          return [{ id: 777, room_id: 30008, user_id: null, role: 'ai', text: 'late answer', created_at: sevenHoursAgo }];
        }
        return [];
      });
      await act(async () => {
        await vi.advanceTimersByTimeAsync(4500);
      });
      const texts = result.current.items.map((it) => it.text);
      expect(texts[texts.length - 1]).toBe('late answer');
      unmount();
    } finally {
      vi.useRealTimers();
    }
  });

  it('dedupes live transcript against its DB version', async () => {
    const { result, unmount } = await renderChat();
    act(() => {
      result.current.handleLiveData({ type: 'transcript', message_id: 555, room_id: 30008, text: 'spoken words', user_id: 7 });
    });
    expect(result.current.items.filter((it) => it.text === 'spoken words')).toHaveLength(1);

    // Poll dem ve ban DB cung id → chi con 1 bubble
    fetchJson.mockImplementation(async (path) => {
      if (path.startsWith('/messages/?')) {
        return [{ id: 555, room_id: 30008, user_id: 7, role: 'user', text: 'spoken words', meta_data: JSON.stringify({ source: 'speech_to_text' }), created_at: new Date().toISOString() }];
      }
      return [];
    });
    await act(async () => {
      await result.current.reload();
    });
    expect(result.current.items.filter((it) => it.text === 'spoken words')).toHaveLength(1);
    unmount();
  });
});
