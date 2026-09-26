import { useEffect, useState } from 'react';
import { HiSpeakerWave } from 'react-icons/hi2';

import { FALLBACK_VOICES, fetchVoices, getStoredVoice, storeVoice } from './voiceApi';

// Nút chọn 1 trong 4 giọng Anh (Heart/Adam/Emma/George). Lưu localStorage.
export function VoicePicker({ value, onChange }) {
  const [voices, setVoices] = useState(FALLBACK_VOICES);
  const [inner, setInner] = useState(() => value || getStoredVoice());
  const current = value || inner;

  useEffect(() => {
    let alive = true;
    fetchVoices().then((list) => {
      if (alive && list.length > 0) setVoices(list);
    });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (value) setInner(value);
  }, [value]);

  function handleChange(e) {
    const next = e.target.value;
    setInner(next);
    storeVoice(next);
    onChange?.(next);
  }

  return (
    <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#555' }}>
      <HiSpeakerWave size={14} title="AI voice" />
      <select
        aria-label="Choose AI voice"
        value={current}
        onChange={handleChange}
        style={{ border: '1px solid #111', padding: '4px 6px', fontSize: 12, cursor: 'pointer', background: '#fff' }}
      >
        {voices.map((v) => (
          <option key={v.id} value={v.id}>{v.label || v.id}</option>
        ))}
      </select>
    </label>
  );
}
