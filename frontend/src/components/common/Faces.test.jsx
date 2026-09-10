import { describe, expect, it } from 'vitest';
import { FACE_VARIANT_COUNT, avatarFaceProps, avatarValue } from './Faces';

describe('avatar presets', () => {
  it('exposes 6 hand-drawn variants', () => {
    expect(FACE_VARIANT_COUNT).toBe(6);
  });

  it('parses a saved face:N value to that variant', () => {
    expect(avatarFaceProps('face:2', 'An')).toEqual({ variant: 2, name: 'An' });
  });

  it('wraps out-of-range variants instead of crashing', () => {
    expect(avatarFaceProps('face:99', 'An').variant).toBe(99 % FACE_VARIANT_COUNT);
  });

  it('falls back to name hash when nothing saved', () => {
    expect(avatarFaceProps(null, 'An')).toEqual({ variant: undefined, name: 'An' });
    expect(avatarFaceProps('garbage', 'An')).toEqual({ variant: undefined, name: 'An' });
  });

  it('builds the saved value for a variant', () => {
    expect(avatarValue(0)).toBe('face:0');
  });

  it('maps an uploaded avatar marker to its file URL', () => {
    expect(avatarFaceProps('avatar:9', 'An')).toEqual({ variant: undefined, name: 'An', src: '/api/v1/users/9/avatar/file' });
  });
});
