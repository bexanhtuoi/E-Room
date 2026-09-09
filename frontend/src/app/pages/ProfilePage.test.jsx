import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../lib/api', () => ({ fetchJson: vi.fn() }));
vi.mock('../../features/rooms/CreateRoomModal', () => ({
  CreateRoomModal: () => null,
}));
vi.mock('../../features/rooms/RoomRow', async (importOriginal) => {
  const mod = await importOriginal();
  return { ...mod, useRoomMembers: () => ({ data: [] }) };
});

import { fetchJson } from '../../lib/api';
import { ProfilePage } from './ProfilePage';

const USER = {
  id: 9,
  email: 'an@example.com',
  full_name: 'An Nguyen',
  english_level: 'B1',
  avatar_url: 'face:2',
  created_at: '2026-01-05T10:00:00Z',
};

vi.mock('../AuthContext', () => ({
  useAuth: () => ({ user: { ...USER }, setUser: vi.fn(), logout: vi.fn() }),
}));

const ROOMS = [
  { id: 1, name: 'Hosted Room', host_id: 9, status: 'idle', topics: ['Cinema'], created_at: '2026-09-01T10:00:00Z' },
  { id: 2, name: 'Joined Room', host_id: 5, status: 'active', topics: ['Music'], created_at: '2026-09-02T10:00:00Z' },
  { id: 3, name: 'Old Session', host_id: 5, status: 'ended', topics: ['Travel'], created_at: '2026-08-20T10:00:00Z' },
];

const MESSAGES = [
  { id: 11, room_id: 2, user_id: 9, role: 'user', text: 'hello there', created_at: '2026-09-02T11:00:00Z' },
  { id: 12, room_id: 3, user_id: 9, role: 'user', text: 'it was great', created_at: '2026-08-20T11:00:00Z' },
];

beforeEach(() => {
  fetchJson.mockReset();
  fetchJson.mockImplementation(async (path) => {
    if (path.startsWith('/rooms/')) return ROOMS;
    if (path.startsWith('/users/me/stats')) {
      return {
        messages_total: 42, messages_this_week: 5, messages_last_week: 3,
        week_delta: 2, streak_days: 4, most_active_day: '2026-09-07', most_active_day_count: 3,
      };
    }
    if (path.startsWith('/messages/')) return MESSAGES;
    if (path.startsWith('/notifications/')) {
      return [{ id: 7, user_id: 9, title: 'Room matched', body: 'Cinema room is live', notification_type: 'match', is_read: false, created_at: '2026-09-03T10:00:00Z' }];
    }
    if (path.startsWith('/documents/')) {
      return [{ id: 3, user_id: 9, file_name: 'vocab.pdf', file_type: 'pdf', created_at: '2026-09-01T10:00:00Z' }];
    }
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

async function goTo(label) {
  const sidebar = screen.getByLabelText('Profile sections');
  fireEvent.click(within(sidebar).getByRole('button', { name: new RegExp(label) }));
}

describe('ProfilePage portal', () => {
  it('renders sidebar sections with user row and without subscription/activity', async () => {
    renderPortal();
    const sidebar = await screen.findByLabelText('Profile sections');
    for (const label of ['Overview', 'My rooms', 'Sessions', 'Usage', 'Documents', 'Notifications', 'Settings']) {
      expect(within(sidebar).getByRole('button', { name: new RegExp(label) })).toBeTruthy();
    }
    expect(within(sidebar).queryByRole('button', { name: /Subscription/ })).toBeNull();
    expect(within(sidebar).queryByRole('button', { name: /^Activity/ })).toBeNull();
    expect(within(sidebar).getByRole('button', { name: /Sign out/ })).toBeTruthy();
  });

  it('shows pagehead and accurate message total from stats API', async () => {
    renderPortal();
    expect(await screen.findByRole('heading', { level: 1, name: 'Overview' })).toBeTruthy();
    await waitFor(() => {
      expect(screen.getByText('Messages').previousSibling.textContent).toBe('42');
    });
  });

  it('collapses the sidebar to an icon rail', async () => {
    const { container } = renderPortal();
    await screen.findByLabelText('Profile sections');
    fireEvent.click(screen.getByRole('button', { name: /Collapse sidebar/ }));
    expect(container.querySelector('.portal-app').className).toContain('is-collapsed');
  });

  it('filters rooms by tab and search, expands total counts', async () => {
    renderPortal();
    await goTo('My rooms');
    expect(await screen.findByText('Hosted Room')).toBeTruthy();
    fireEvent.click(screen.getByRole('tab', { name: 'Hosted' }));
    expect(screen.queryByText('Joined Room')).toBeNull();
    fireEvent.click(screen.getByRole('tab', { name: 'All' }));
    fireEvent.change(screen.getByLabelText('Search rooms'), { target: { value: 'joined' } });
    expect(screen.queryByText('Hosted Room')).toBeNull();
    expect(screen.getByText('Joined Room')).toBeTruthy();
  });

  it('lists past sessions with search and expandable lines', async () => {
    renderPortal();
    await goTo('Sessions');
    expect(await screen.findByText('Old Session')).toBeTruthy();
    fireEvent.click(screen.getByText('Old Session'));
    expect(await screen.findByText('it was great')).toBeTruthy();
  });

  it('shows usage report with streak, heat and donut', async () => {
    renderPortal();
    await goTo('Usage');
    expect(await screen.findByText('Day streak')).toBeTruthy();
    expect(screen.getByText('Travel')).toBeTruthy();
    expect(screen.getByText('ROOMS')).toBeTruthy();
  });

  it('shows full activity at the bottom of overview with filters', async () => {
    renderPortal();
    expect(await screen.findByText('hello there')).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Search messages'), { target: { value: 'great' } });
    expect(screen.queryByText('hello there')).toBeNull();
    expect(screen.getByText('it was great')).toBeTruthy();
  });

  it('shows documents as cards with type stats', async () => {
    renderPortal();
    await goTo('Documents');
    expect(await screen.findByText('vocab.pdf')).toBeTruthy();
    expect(screen.getByText('pdf')).toBeTruthy();
  });

  it('hides zero stat cards when there is nothing to count', async () => {
    fetchJson.mockImplementation(async (path) => {
      if (path.startsWith('/rooms/')) return [];
      if (path.startsWith('/messages/')) return [];
      if (path.startsWith('/messages/count')) return { count: 0 };
      if (path.startsWith('/notifications/')) return [];
      if (path.startsWith('/documents/')) return [];
      return [];
    });
    renderPortal();
    await goTo('Documents');
    expect(await screen.findByText(/No documents yet/)).toBeTruthy();
    expect(screen.queryByText('file types')).toBeNull();
    await goTo('Sessions');
    expect(await screen.findByText(/will land here as past sessions/)).toBeTruthy();
    expect(screen.queryByText('Past sessions')).toBeNull();
  });

  it('shows unread notifications with tabs and badge', async () => {
    renderPortal();
    await goTo('Notifications');
    expect(await screen.findByText('Room matched')).toBeTruthy();
    fireEvent.click(screen.getByRole('tab', { name: /Unread/ }));
    expect(screen.getByText('Room matched')).toBeTruthy();
  });

  it('opens settings with identity card, avatar presets and danger zone', async () => {
    renderPortal();
    await goTo('Settings');
    expect(await screen.findByRole('radiogroup', { name: /Choose avatar/ })).toBeTruthy();
    expect(screen.getByDisplayValue('B1')).toBeTruthy();
    expect(screen.getByText('Danger zone')).toBeTruthy();
  });
});
