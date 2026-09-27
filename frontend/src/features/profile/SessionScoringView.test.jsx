import { describe, expect, it } from 'vitest';

import { dedupeByAttempt, inWindow, parseSessionTime } from './SessionScoringView';

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

describe('dedupeByAttempt (1 thẻ cho cả attempt)', () => {
  const scored = (mid, aid) => ({
    message_id: mid,
    text: 'câu trong cùng attempt',
    pronunciation: aid ? { score: 70.1, method: 'local-v2', attempt_id: aid } : null,
  });

  it('gộp các câu chung attempt_id thành 1', () => {
    const out = dedupeByAttempt([scored(9, 'att1'), scored(10, 'att1'), scored(11, 'att1')]);
    expect(out).toHaveLength(1);
    expect(out[0].message_id).toBe(9);
  });

  it('giữ riêng câu chưa chấm và attempt khác nhau', () => {
    const out = dedupeByAttempt([scored(9, 'att1'), scored(10, 'att1'), scored(12, null), scored(13, 'att2')]);
    expect(out.map((u) => u.message_id)).toEqual([9, 12, 13]);
  });
});
