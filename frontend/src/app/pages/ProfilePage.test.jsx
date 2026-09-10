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

const NOTIFS = [
  { id: 7, user_id: 9, title: 'Room matched', body: 'Cinema room is live', notification_type: 'match', is_read: false, created_at: '2026-09-03T10:00:00Z' },
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
    if (path.startsWith('/notifications/')) return NOTIFS;
    return [];
  });
});

function renderPortal(section = 'overview') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>
        <ProfilePage section={section} />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe('ProfilePage portal', () => {
  it('renders five section links with routes, no usage/documents/settings pages', async () => {
    renderPortal();
    const sidebar = await screen.findByLabelText('Profile sections');
    for (const [label, href] of [['Overview', '/overview'], ['My rooms', '/my-rooms'], ['Session', '/session'], ['Schedule', '/schedule'], ['Assessment', '/assessment']]) {
      const link = within(sidebar).getByRole('link', { name: new RegExp(label) });
      expect(link.getAttribute('href')).toBe(href);
    }
    expect(within(sidebar).queryByRole('link', { name: /Usage/ })).toBeNull();
    expect(within(sidebar).queryByRole('link', { name: /Documents/ })).toBeNull();
    expect(within(sidebar).queryByRole('link', { name: /Settings/ })).toBeNull();
    expect(within(sidebar).getByRole('button', { name: /Notifications/ })).toBeTruthy();
  });

  it('shows overview today panel, week facts and up-next without KPI cards', async () => {
    renderPortal();
    expect(await screen.findByRole('heading', { level: 1, name: 'Overview' })).toBeTruthy();
    expect(await screen.findByText(/Good (morning|afternoon|evening)|Up late/)).toBeTruthy();
    expect(screen.queryByText('Rooms hosted')).toBeNull();
    expect(screen.queryByText('Day streak')).toBeNull();
    expect(screen.queryByRole('button', { name: /New room/ })).toBeNull();
    await waitFor(() => {
      expect(screen.getByText(/4-day streak/)).toBeTruthy();
    });
    expect(screen.getByText(/Peak day 2026-09-07/)).toBeTruthy();
    expect(screen.getByText(/Level journey/)).toBeTruthy();
    expect(screen.getByText(/Up next/)).toBeTruthy();
    expect(screen.getByText(/Your top topic is Cinema/)).toBeTruthy();
  });

  it('links avatar and name to the profile page', async () => {
    renderPortal();
    const profile = await screen.findByTitle('My profile');
    expect(profile.getAttribute('href')).toBe('/profile');
  });

  it('shows only hosted rooms with search and manage actions', async () => {
    renderPortal('rooms');
    expect(await screen.findByText('Hosted Room')).toBeTruthy();
    expect(screen.queryByText('Joined Room')).toBeNull();
    fireEvent.change(screen.getByLabelText('Search rooms'), { target: { value: 'zzz-no-match' } });
    expect(screen.queryByText('Hosted Room')).toBeNull();
    fireEvent.change(screen.getByLabelText('Search rooms'), { target: { value: 'hosted' } });
    expect(await screen.findByText('Hosted Room')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Configure Hosted Room' }).getAttribute('href')).toBe('/rooms/1/config');
    expect(screen.getByRole('link', { name: 'Enter Hosted Room' }).getAttribute('href')).toBe('/rooms/1');
    expect(screen.getByRole('button', { name: 'Delete Hosted Room' })).toBeTruthy();
  });

  it('opens notifications as a popup with delete action', async () => {
    renderPortal();
    const sidebar = await screen.findByLabelText('Profile sections');
    fireEvent.click(within(sidebar).getByRole('button', { name: /Notifications/ }));
    expect(await screen.findByRole('dialog', { name: 'Notifications' })).toBeTruthy();
    expect(screen.getByText('Room matched')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: /Delete notification/ }));
    await waitFor(() => {
      expect(fetchJson).toHaveBeenCalledWith('/notifications/7', { method: 'DELETE' });
    });
  });

  it('lists past sessions with quote preview', async () => {
    renderPortal('sessions');
    expect(await screen.findByText('Old Session')).toBeTruthy();
    expect(screen.getByText(/it was great/)).toBeTruthy();
  });

  it('shows schedule with live and open rooms', async () => {
    renderPortal('schedule');
    expect(await screen.findByRole('heading', { level: 1, name: 'Schedule' })).toBeTruthy();
    expect(await screen.findByText('Joined Room')).toBeTruthy();
    expect(screen.getByText('Hosted Room')).toBeTruthy();
  });

  it('shows assessment review list from joined rooms', async () => {
    renderPortal('assessment');
    expect(await screen.findByText('Replay what you said, level up how you say it.')).toBeTruthy();
    expect(await screen.findByText('Old Session')).toBeTruthy();
  });

  it('opens profile resume with pencil edits, avatar popup and save bar', async () => {
    renderPortal('me');
    expect(await screen.findByRole('heading', { level: 1, name: 'Profile' })).toBeTruthy();
    expect(screen.queryByText('Danger zone')).toBeNull();
    expect(screen.queryByText('Account')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Edit English level' }));
    expect(screen.getByDisplayValue('B1')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Change avatar' }));
    expect(await screen.findByRole('dialog', { name: 'Choose avatar' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Reset' })).toBeTruthy();
  });

  it('shows resume sections with editable bio and learning goal', async () => {
    renderPortal('me');
    expect(await screen.findByRole('heading', { name: 'Overview' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'My learning goal' })).toBeTruthy();
    expect(screen.queryByRole('heading', { name: /Skills/ })).toBeNull();
    expect(screen.queryByRole('heading', { name: /Experience/ })).toBeNull();
    expect(screen.queryByRole('heading', { name: /Education/ })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Edit headline' }));
    expect(screen.getByLabelText('Headline')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Done editing headline' }));
    fireEvent.click(screen.getByRole('button', { name: 'Edit learning goal' }));
    fireEvent.change(screen.getByLabelText('Learning goal'), { target: { value: 'Speak daily.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Done editing learning goal' }));
    expect(await screen.findByText('Speak daily.')).toBeTruthy();
  });

  it('collapses the sidebar to an icon rail', async () => {
    const { container } = renderPortal();
    await screen.findByLabelText('Profile sections');
    fireEvent.click(screen.getByRole('button', { name: /Collapse sidebar/ }));
    expect(container.querySelector('.portal-app').className).toContain('is-collapsed');
  });
});
