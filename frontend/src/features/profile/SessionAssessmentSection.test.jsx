import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../../lib/api', () => ({
  fetchJson: vi.fn(),
  getTokens: () => ({ access: 'test-token', refresh: null }),
  API_BASE_URL: '/api/v1',
}));
vi.mock('../chat/voiceApi', () => ({
  getStoredVoice: () => 'af_heart',
  storeVoice: vi.fn(),
  speakToAudioUrl: vi.fn(async () => 'blob:mock'),
  FALLBACK_VOICES: [{ id: 'af_heart', label: 'Heart' }],
  fetchVoices: vi.fn(async () => [{ id: 'af_heart', label: 'Heart' }]),
}));

import { fetchJson } from '../../lib/api';
import { SessionAssessmentSection } from './SessionAssessmentSection';

function sessionDetail(id, roomName) {
  return {
    session: { id, user_id: 9, room_id: 3, joined_at: '2026-08-20T11:00:00Z', left_at: '2026-08-20T11:30:00Z', duration_seconds: 1800, summary: null },
    room: { id: 3, name: roomName, status: 'ended', topics: [] },
    message_count: 1,
  };
}

fetchJson.mockImplementation(async (path, options = {}) => {
  if (path === '/sessions/mine') {
    return {
      sessions: [
        { session: { id: 102, room_id: 3 }, room: { id: 3, name: 'New Session' }, message_count: 5 },
        { session: { id: 101, room_id: 3 }, room: { id: 3, name: 'Old Session' }, message_count: 2 },
      ],
    };
  }
  if (path === '/sessions/102') return sessionDetail(102, 'New Session');
  if (path === '/sessions/101') return sessionDetail(101, 'Old Session');
  if (path === '/sessions/102/messages' || path === '/sessions/101/messages') {
    return { session_id: 0, message_count: 1, transcript: 'An: hello', transcript_lines: [{ speaker: 'An', text: 'hello' }], chat: [] };
  }
  if (path === '/rooms/3/speech-logs/me') return [];
  return {};
});

function renderAssessment() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>
        <SessionAssessmentSection />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe('SessionAssessmentSection', () => {
  it('defaults to the newest session and shows scoring view', async () => {
    renderAssessment();
    expect(await screen.findByText('New Session')).toBeTruthy();
    expect(await screen.findByText('AI feedbacks')).toBeTruthy();
    expect(await screen.findByText('My pronunciation scores')).toBeTruthy();
  });

  it('switches sessions via dropdown', async () => {
    renderAssessment();
    const select = await screen.findByLabelText('Choose session');
    fireEvent.change(select, { target: { value: '101' } });
    expect(await screen.findByText('Old Session')).toBeTruthy();
  });

  it('shows empty state without sessions', async () => {
    const fallback = fetchJson.getMockImplementation();
    fetchJson.mockImplementation(async (path, options = {}) => {
      if (path === '/sessions/mine') return { sessions: [] };
      return fallback(path, options);
    });
    try {
      renderAssessment();
      expect(await screen.findByText(/Chưa có session nào/)).toBeTruthy();
    } finally {
      fetchJson.mockImplementation(fallback);
    }
  });

  it('edits own line via pencil and PATCHes corrected text', async () => {
    const fallback = fetchJson.getMockImplementation();
    const calls = [];
    fetchJson.mockImplementation(async (path, options = {}) => {
      calls.push([path, options]);
      if (path === '/sessions/mine') {
        return {
          sessions: [
            { session: { id: 101, room_id: 3 }, room: { id: 3, name: 'Old Session' }, message_count: 1 },
          ],
        };
      }
      if (path === '/sessions/101') {
        return {
          session: { id: 101, user_id: 9, room_id: 3, joined_at: '2026-08-20T11:00:00Z', left_at: '2026-08-20T11:30:00Z', duration_seconds: 1800, summary: null },
          room: { id: 3, name: 'Old Session', status: 'ended', topics: [] },
          message_count: 1,
        };
      }
      if (path === '/sessions/101/messages') {
        return {
          session_id: 101, message_count: 1, transcript: 'An: it was great',
          transcript_lines: [{ speaker: 'An', text: 'it was great', message_id: 12, user_id: 9 }],
          chat: [],
        };
      }
      if (path === '/rooms/3/speech-logs/me') {
        return [{
          message_id: 12, room_id: 3, text: 'it was great', corrected_text: 'it was great',
          created_at: '2026-08-20T11:10:00Z', pronunciation: null, feedback: null,
        }];
      }
      if (path === '/rooms/3/speech-logs/12' && (options.method || 'GET') === 'PATCH') {
        return { message_id: 12, corrected_text: 'it was really great' };
      }
      return fallback(path, options);
    });
    try {
      renderAssessment();
      fireEvent.click(await screen.findByLabelText('Sửa: it was great'));
      fireEvent.change(screen.getByLabelText('Sửa câu đã nói'), { target: { value: 'it was really great' } });
      fireEvent.click(screen.getByRole('button', { name: 'Lưu' }));
      await waitFor(() => {
        expect(calls.some(([p, o]) => p === '/rooms/3/speech-logs/12' && (o.method || 'GET') === 'PATCH')).toBe(true);
      });
      const patchCall = calls.find(([p, o]) => p === '/rooms/3/speech-logs/12' && (o.method || 'GET') === 'PATCH');
      expect(JSON.parse(patchCall[1].body)).toEqual({ corrected_text: 'it was really great' });
    } finally {
      fetchJson.mockImplementation(fallback);
    }
  });
});
