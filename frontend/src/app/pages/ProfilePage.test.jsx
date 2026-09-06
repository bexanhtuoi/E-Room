import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../lib/api', () => ({ fetchJson: vi.fn() }));
vi.mock('../../features/rooms/CreateRoomModal', () => ({
  CreateRoomModal: () => null,
}));

import { fetchJson } from '../../lib/api';
import { ProfilePage } from './ProfilePage';

const USER = {
  id: 9,
  email: 'an@example.com',
  full_name: 'An Nguyen',
  english_level: 'B1',
  avatar_url: 'face:2',
};

vi.mock('../AuthContext', () => ({
  useAuth: () => ({ user: { ...USER }, setUser: vi.fn(), logout: vi.fn() }),
}));

const ROOMS = [
  { id: 1, name: 'Hosted Room', host_id: 9, status: 'idle', topics: ['Cinema'], created_at: '2026-09-01T10:00:00Z' },
  { id: 2, name: 'Joined Room', host_id: 5, status: 'active', topics: [], created_at: '2026-09-02T10:00:00Z' },
];

beforeEach(() => {
  fetchJson.mockReset();
  fetchJson.mockImplementation(async (path) => {
    if (path.startsWith('/rooms/')) return ROOMS;
    if (path.startsWith('/messages/')) {
      return [{ id: 11, room_id: 2, user_id: 9, role: 'user', text: 'hello there', created_at: '2026-09-02T11:00:00Z' }];
    }
    if (path.startsWith('/notifications/')) {
      return [{ id: 7, user_id: 9, title: 'Room matched', body: 'Cinema room is live', notification_type: 'match', is_read: false, created_at: '2026-09-03T10:00:00Z' }];
    }
    if (path.startsWith('/documents/')) return [];
    return [];
  });
});

function renderPortal() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>
        <ProfilePage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe('ProfilePage portal', () => {
  it('renders sidebar sections and header identity', async () => {
    renderPortal();
    for (const label of ['Overview', 'My rooms', 'Activity', 'Documents', 'Notifications', 'Subscription', 'Settings']) {
      expect(await screen.findByRole('button', { name: new RegExp(label) })).toBeTruthy();
    }
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('An Nguyen');
  });

  it('shows real stats on the dashboard', async () => {
    renderPortal();
    await waitFor(() => {
      expect(screen.getByText('rooms hosted').previousSibling.textContent).toBe('1');
      expect(screen.getByText('rooms joined').previousSibling.textContent).toBe('1');
      expect(screen.getByText('messages sent').previousSibling.textContent).toBe('1');
    });
  });

  it('navigates to My rooms and expands a room with my messages', async () => {
    renderPortal();
    fireEvent.click(await screen.findByRole('button', { name: /My rooms/ }));
    expect(await screen.findByText('Hosted Room')).toBeTruthy();
    expect(screen.getByText('Joined Room')).toBeTruthy();
    fireEvent.click(screen.getByText('Joined Room'));
    expect(await screen.findByText('hello there')).toBeTruthy();
  });

  it('shows unread notifications with a sidebar badge', async () => {
    renderPortal();
    fireEvent.click(await screen.findByRole('button', { name: /Notifications/ }));
    expect(await screen.findByText('Room matched')).toBeTruthy();
    expect(screen.getByText('1 new')).toBeTruthy();
  });

  it('opens settings with avatar presets and english level', async () => {
    renderPortal();
    fireEvent.click(await screen.findByRole('button', { name: /Settings/ }));
    expect(await screen.findByRole('radiogroup', { name: /Choose avatar/ })).toBeTruthy();
    expect(screen.getByDisplayValue('B1')).toBeTruthy();
  });
});
