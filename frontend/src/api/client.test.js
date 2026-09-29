import { describe, expect, it } from 'vitest';

import { toApiError } from './client';

describe('toApiError', () => {
  it('keeps detail message and attaches code', () => {
    const error = toApiError({ code: 'ROOM_NOT_FOUND', detail: 'Không tìm thấy phòng.' }, 404);
    expect(error).toBeInstanceOf(Error);
    expect(error.message).toBe('Không tìm thấy phòng.');
    expect(error.code).toBe('ROOM_NOT_FOUND');
  });

  it('falls back to status text without detail', () => {
    const error = toApiError({}, 500);
    expect(error.message).toBe('Request failed with status 500');
    expect(error.code).toBeUndefined();
  });

  it('joins FastAPI validation errors', () => {
    const error = toApiError({ detail: [{ msg: 'a' }, { msg: 'b' }] }, 422);
    expect(error.message).toBe('a; b');
  });
});
