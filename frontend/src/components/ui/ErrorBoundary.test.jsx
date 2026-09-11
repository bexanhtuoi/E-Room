import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ErrorBoundary } from './ErrorBoundary';

function Boom({ message }) {
  throw new Error(message);
}

describe('ErrorBoundary stale chunk reload', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it('reloads once when a lazy chunk fails to fetch', () => {
    const reloadMock = vi.fn();
    Object.defineProperty(window, 'location', { value: { reload: reloadMock }, writable: true });

    vi.spyOn(console, 'error').mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <Boom message="Failed to fetch dynamically imported module: RoomsPage-abc.js" />
      </ErrorBoundary>,
    );

    expect(reloadMock).toHaveBeenCalledTimes(1);
    expect(sessionStorage.getItem('er-chunk-reloaded')).toBe('1');
  });

  it('shows the fallback instead of looping when reload already happened', () => {
    const reloadMock = vi.fn();
    Object.defineProperty(window, 'location', { value: { reload: reloadMock }, writable: true });
    sessionStorage.setItem('er-chunk-reloaded', '1');

    vi.spyOn(console, 'error').mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <Boom message="Failed to fetch dynamically imported module: RoomsPage-abc.js" />
      </ErrorBoundary>,
    );

    expect(reloadMock).not.toHaveBeenCalled();
    expect(screen.getByText('Something went wrong')).toBeTruthy();
  });

  it('shows the fallback for non-chunk errors without reloading', () => {
    const reloadMock = vi.fn();
    Object.defineProperty(window, 'location', { value: { reload: reloadMock }, writable: true });

    vi.spyOn(console, 'error').mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <Boom message="Some render bug" />
      </ErrorBoundary>,
    );

    expect(reloadMock).not.toHaveBeenCalled();
    expect(screen.getByText('Some render bug')).toBeTruthy();
  });
});
