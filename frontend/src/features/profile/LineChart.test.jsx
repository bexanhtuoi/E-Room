import { describe, expect, it } from 'vitest';
import { bucketByRange } from './LineChart';

function messageAt(date) {
  return { id: Math.random(), created_at: date.toISOString() };
}

describe('bucketByRange', () => {
  it('buckets the last 24 hours by hour', () => {
    const now = new Date();
    const buckets = bucketByRange([messageAt(now), messageAt(now)], '24h');

    expect(buckets).toHaveLength(24);
    expect(buckets.reduce((s, b) => s + b.count, 0)).toBe(2);
    expect(buckets[23].count).toBe(2);
  });

  it('buckets 7 days and ignores out-of-range messages', () => {
    const now = new Date();
    const old = new Date(now.getTime() - 40 * 86400 * 1000);
    const buckets = bucketByRange([messageAt(now), messageAt(old)], '7d');

    expect(buckets).toHaveLength(7);
    expect(buckets.reduce((s, b) => s + b.count, 0)).toBe(1);
  });

  it('buckets 30 days', () => {
    const buckets = bucketByRange([], '30d');

    expect(buckets).toHaveLength(30);
    expect(buckets.every((b) => b.count === 0)).toBe(true);
  });
});
