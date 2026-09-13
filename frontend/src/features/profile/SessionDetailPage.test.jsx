import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../../lib/api', () => ({
  fetchJson: vi.fn(),
  getTokens: () => ({ access: 'test-token', refresh: null }),
  API_BASE_URL: '/api/v1',
}));
vi.mock('../../app/AuthContext', () => ({
  useAuth: () => ({ user: { id: 9, email: 'an@example.com', full_name: 'An Nguyen' } }),
}));

import { fetchJson } from '../../lib/api';
import { SessionDetailPage } from './SessionDetailPage';

let mockChat = [];
fetchJson.mockImplementation(async (path) => {
  if (path === '/sessions/101') {
    return {
      session: { id: 101, user_id: 9, room_id: 3, joined_at: '2026-08-20T11:00:00Z', left_at: '2026-08-20T11:30:00Z', duration_seconds: 1800, summary: null },
      room: { id: 3, name: 'Old Session', status: 'ended', topics: ['Travel'] },
      message_count: 2,
    };
  }
  if (path === '/sessions/101/messages') {
    return {
      session_id: 101,
      message_count: 2,
      transcript: 'An Nguyen: hello there\nAn Nguyen: it was great',
      chat: mockChat,
    };
  }
  return {};
});

function mockStreamSse(frames) {
  const payload = frames.map((event) => `data: ${JSON.stringify(event)}\n\n`).join('');
  global.fetch = vi.fn(async () => ({
    ok: true,
    body: new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(payload));
        controller.close();
      },
    }),
  }));
}

function renderDetail() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <MemoryRouter initialEntries={['/session/101']}>
      <QueryClientProvider client={client}>
        <Routes>
          <Route path="/session/:sessionId" element={<SessionDetailPage />} />
          <Route path="/session" element={<div>Sessions list</div>} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe('SessionDetailPage', () => {
  it('shows transcript and streams answers with thinking', async () => {
    mockStreamSse([
      { kind: 'thinking', text: 'Reading transcript…' },
      { kind: 'token', text: 'They greeted' },
      { kind: 'token', text: ' and praised.' },
      { kind: 'done', message_count: 2 },
    ]);
    renderDetail();
    expect(await screen.findByText('Old Session')).toBeTruthy();
    expect(await screen.findByText(/hello there/)).toBeTruthy();

    fireEvent.change(screen.getByLabelText('Ask about this session'), { target: { value: 'What was said?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }));

    expect(await screen.findByText('They greeted and praised.')).toBeTruthy();
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/sessions/101/chat/stream',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('asks via quick prompt chips', async () => {
    mockStreamSse([{ kind: 'token', text: 'They greeted and praised.' }, { kind: 'done', message_count: 2 }]);
    renderDetail();
    fireEvent.click(await screen.findByRole('button', { name: 'What did we decide?' }));
    expect(await screen.findByText('They greeted and praised.')).toBeTruthy();
  });

  it('restores saved chat history after reload', async () => {
    mockChat = [{ role: 'user', text: 'Old question?' }, { role: 'ai', text: 'Old answer.' }];
    try {
      renderDetail();
      expect(await screen.findByText('Old question?')).toBeTruthy();
      expect(await screen.findByText('Old answer.')).toBeTruthy();
    } finally {
      mockChat = [];
    }
  });

  it('shows the server error message when the stream fails', async () => {
    mockStreamSse([{ kind: 'error', text: 'No messages in this session yet' }]);
    renderDetail();
    fireEvent.click(await screen.findByRole('button', { name: 'What did we decide?' }));
    expect(await screen.findByText('No messages in this session yet')).toBeTruthy();
  });
});
