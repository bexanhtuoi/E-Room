import { describe, expect, it } from 'vitest';

import { sortRooms } from './roomSort';

describe('sortRooms', () => {
  it('orders live before open before ended, newest first inside each status', () => {
    const rooms = [
      { id: 1, status: 'ended' },
      { id: 2, status: 'idle' },
      { id: 3, status: 'active' },
      { id: 4, status: 'idle' },
      { id: 5, status: 'active' },
      { id: 6, status: 'ended' },
    ];
    expect(sortRooms(rooms).map((r) => r.id)).toEqual([5, 3, 4, 2, 6, 1]);
  });

  it('handles empty and unknown statuses', () => {
    expect(sortRooms([])).toEqual([]);
    expect(sortRooms([{ id: 1, status: 'weird' }])).toEqual([{ id: 1, status: 'weird' }]);
  });
});
