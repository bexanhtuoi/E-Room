import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { VoicePicker } from './VoicePicker';

describe('VoicePicker', () => {
  it('shows 4 English voice choices from fallback', () => {
    render(<VoicePicker value="af_heart" onChange={() => {}} />);
    const select = screen.getByLabelText('Choose AI voice');
    expect(select.children.length).toBe(4);
    expect(screen.getByRole('option', { name: /Emma/ })).toBeDefined();
  });

  it('persists choice and notifies parent', () => {
    const onChange = vi.fn();
    render(<VoicePicker value="af_heart" onChange={onChange} />);
    fireEvent.change(screen.getByLabelText('Choose AI voice'), { target: { value: 'bm_george' } });
    expect(onChange).toHaveBeenCalledWith('bm_george');
    expect(localStorage.getItem('eroom-tts-voice')).toBe('bm_george');
  });

  it('loads voices from API when available', async () => {
    const apiVoices = [
      { id: 'af_heart', label: 'Heart' },
      { id: 'am_adam', label: 'Adam' },
      { id: 'bf_emma', label: 'Emma' },
      { id: 'bm_george', label: 'George' },
    ];
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => apiVoices })));
    try {
      render(<VoicePicker value="af_heart" onChange={() => {}} />);
      await waitFor(() => expect(screen.getByRole('option', { name: 'George' })).toBeDefined());
    } finally {
      vi.unstubAllGlobals();
    }
  });
});
