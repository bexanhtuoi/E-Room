import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../../lib/api', () => ({ API_BASE_URL: '/api/v1', fetchJson: vi.fn() }));

const ROOM = {
  id: 1, name: 'Hosted Room', host_id: 9, status: 'idle', topics: ['Cinema'],
  description: 'A test room', max_participants: 4,
  enable_heartbeat: true, enable_transcript: true, enable_agent: true,
  is_private: true, allowed_emails: ['friend@example.com'], system_prompt: null,
  created_at: '2026-09-01T10:00:00Z',
};

let currentUserId = 9;
vi.mock('../../app/AuthContext', () => ({
  useAuth: () => ({ user: { id: currentUserId, email: 'an@example.com', full_name: 'An Nguyen' } }),
}));

import { fetchJson } from '../../lib/api';
import { RoomConfigPage } from './RoomConfigPage';

fetchJson.mockImplementation(async (path) => {
  if (path === '/rooms/1') return { ...ROOM };
  if (path === '/rooms/1/skills') return [{ id: 5, room_id: 1, kind: 'skill', file_name: 'Coach', file_type: 'skill', file_path: '', content: 'Be kind.', enabled: true }];
  if (path === '/rooms/1/documents') return [{ id: 6, room_id: 1, kind: 'file', file_name: 'notes.md', file_type: 'md', file_path: 'documents/x', created_at: '2026-09-01T10:00:00Z' }];
  if (path.startsWith('/rooms/')) return [];
  return [];
});

function renderConfig() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter initialEntries={['/rooms/1/config']}>
      <QueryClientProvider client={client}>
        <Routes>
          <Route path="/rooms/:roomId/config" element={<RoomConfigPage />} />
          <Route path="/rooms" element={<div>Rooms list</div>} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe('RoomConfigPage', () => {
  it('shows all config cards for the host', async () => {
    currentUserId = 9;
    renderConfig();
    for (const title of ['Basics', 'Who can enter', /AI prompt/, /Documents for AI/]) {
      expect(await screen.findByRole('heading', { name: title })).toBeTruthy();
    }
    expect(await screen.findByDisplayValue('Hosted Room')).toBeTruthy();
    expect(screen.getByText('friend@example.com')).toBeTruthy();
    const docLink = screen.getByRole('link', { name: 'notes.md' });
    expect(docLink.getAttribute('href')).toBe('/api/v1/rooms/1/documents/6/file');
    expect(docLink.getAttribute('target')).toBe('_blank');
  });

  it('lets the host pick the spoken language', async () => {
    currentUserId = 9;
    renderConfig();
    const select = await screen.findByLabelText('Spoken language for transcript');
    expect(select.value).toBe('en');
    fireEvent.change(select, { target: { value: 'vi' } });
    expect(select.value).toBe('vi');
  });

  it('redirects non-hosts to rooms list', async () => {
    currentUserId = 5;
    renderConfig();
    expect(await screen.findByText('Rooms list')).toBeTruthy();
  });
});
