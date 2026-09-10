import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../../lib/api', () => ({ fetchJson: vi.fn() }));
vi.mock('../../app/AuthContext', () => ({
  useAuth: () => ({ user: { id: 9, email: 'an@example.com', full_name: 'An Nguyen' } }),
}));

import { fetchJson } from '../../lib/api';
import { SessionDetailPage } from './SessionDetailPage';

fetchJson.mockImplementation(async (path, options) => {
  if (path === '/sessions/101') {
    return {
      session: { id: 101, user_id: 9, room_id: 3, joined_at: '2026-08-20T11:00:00Z', left_at: '2026-08-20T11:30:00Z', duration_seconds: 1800, summary: null },
      room: { id: 3, name: 'Old Session', status: 'ended', topics: ['Travel'] },
      message_count: 2,
    };
  }
  if (path === '/sessions/101/messages') {
    return { session_id: 101, message_count: 2, transcript: 'An Nguyen: hello there\nAn Nguyen: it was great' };
  }
  if (path === '/sessions/101/ask') {
    return { answer: 'They greeted and praised.', message_count: 2 };
  }
  if (path === '/sessions/101/summarize') {
    return { summary: '## Summary\nNice chat.', message_count: 2 };
  }
  return {};
});

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
  it('shows transcript and answers questions', async () => {
    renderDetail();
    expect(await screen.findByText('Old Session')).toBeTruthy();
    expect(await screen.findByText(/hello there/)).toBeTruthy();

    fireEvent.change(screen.getByLabelText('Ask about this session'), { target: { value: 'What was said?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }));
    expect(await screen.findByText('They greeted and praised.')).toBeTruthy();
    expect(fetchJson).toHaveBeenCalledWith('/sessions/101/ask', expect.objectContaining({ method: 'POST' }));
  });

  it('summarizes on demand', async () => {
    renderDetail();
    fireEvent.click(await screen.findByRole('button', { name: /Recap for Notion/ }));
    await waitFor(() => {
      expect(fetchJson).toHaveBeenCalledWith('/sessions/101/summarize', expect.objectContaining({ method: 'POST' }));
    });
  });
});
