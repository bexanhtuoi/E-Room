import { describe, expect, it } from 'vitest';

import { inWindow, isFreshScore, parseSessionTime } from './SessionScoringView';

describe('inWindow (session naive UTC vs utterance ISO)', () => {
  // Case thật đêm 27/09: session naive UTC, utterance ISO +00:00.
  const joined = '2026-09-26 21:59:07.392259';
  const left = '2026-09-26 21:59:58.476959';
  const created = '2026-09-26T21:59:38.305200+00:00';

  it('coi session naive là UTC, không phải giờ local', () => {
    // 21:59:07 naive phải == 21:59:07 UTC, lệch đúng 0 (kể cả khi TZ=+07).
    expect(parseSessionTime(joined)).toBe(Date.parse('2026-09-26T21:59:07.392259Z'));
  });

  it('giữ câu nói trong session (bug cũ lọc mất -> 0 lines)', () => {
    expect(inWindow(created, joined, left)).toBe(true);
  });

  it('loại câu ngoài window', () => {
    expect(inWindow('2026-09-26T22:05:00+00:00', joined, left)).toBe(false);
    expect(inWindow('2026-09-26T21:50:00+00:00', joined, left)).toBe(false);
  });

  it('session đang mở (không left_at) vẫn giữ câu mới', () => {
    expect(inWindow(created, joined, null)).toBe(true);
  });
});

describe('isFreshScore (rescore phải đợi điểm mới)', () => {
  it('chưa có điểm thì không fresh', () => {
    expect(isFreshScore(null, null)).toBe(false);
    expect(isFreshScore(undefined, { score: 80 })).toBe(false);
  });

  it('chấm lần đầu thì điểm nào cũng fresh', () => {
    expect(isFreshScore({ score: 80 }, null)).toBe(true);
    expect(isFreshScore({ score: 80 }, undefined)).toBe(true);
  });

  it('chấm lại thì đợi scored_at mới', () => {
    const prev = { score: 80, scored_at: '2026-10-15T10:00:00Z' };
    expect(isFreshScore({ ...prev }, prev)).toBe(false);
    expect(isFreshScore({ score: 81, scored_at: '2026-10-15T10:05:00Z' }, prev)).toBe(true);
  });

  it('điểm cũ không stamp thì so nội dung', () => {
    const prev = { score: 80, method: 'local-v2' };
    expect(isFreshScore({ score: 80, method: 'local-v2' }, prev)).toBe(false);
    expect(isFreshScore({ score: 81, method: 'local-v2' }, prev)).toBe(true);
  });
});
