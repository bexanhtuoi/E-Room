import { describe, expect, it } from 'vitest';
import { bucketByDay } from './WeekBars';

describe('bucketByDay', () => {
  it('counts a message sent right now in the today bucket', () => {
    const buckets = bucketByDay([{ created_at: new Date().toISOString() }], 14);
    expect(buckets[buckets.length - 1].today).toBe(true);
    expect(buckets[buckets.length - 1].count).toBe(1);
  });

  it('matches single-digit months and days (padding bug)', () => {
    // 5 Jan: month and day both single digit
    const d = new Date(2026, 0, 5, 12, 0, 0);
    const diff = Math.round((new Date().setHours(0, 0, 0, 0) - new Date(2026, 0, 5).getTime()) / 86400000);
    const buckets = bucketByDay([{ created_at: d.toISOString() }], diff + 1);
    expect(buckets.reduce((s, b) => s + b.count, 0)).toBe(1);
    expect(buckets[0].count).toBe(1);
  });

  it('shows empty state instead of dead bars when nothing happened', async () => {
    const { render, screen } = await import('@testing-library/react');
    const { WeekBars } = await import('./WeekBars');
    const buckets = bucketByDay([], 7);
    render(<WeekBars data={buckets} />);
    expect(screen.getByText(/No activity in this period/)).toBeTruthy();
    expect(document.querySelector('.bars__fill')).toBeNull();
  });
});
