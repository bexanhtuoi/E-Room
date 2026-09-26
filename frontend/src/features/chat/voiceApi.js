import { ApiClient } from '../../api/client';

const STORAGE_KEY = 'eroom-tts-voice';
const DEFAULT_VOICE = 'af_heart';

// Fallback khi API chưa sẵn — khớp 4 giọng backend đã test.
export const FALLBACK_VOICES = [
  { id: 'af_heart', label: 'Heart — nữ Mỹ' },
  { id: 'am_adam', label: 'Adam — nam Mỹ' },
  { id: 'bf_emma', label: 'Emma — nữ Anh' },
  { id: 'bm_george', label: 'George — nam Anh' },
];

const api = new ApiClient();

export function getStoredVoice() {
  try {
    return localStorage.getItem(STORAGE_KEY) || DEFAULT_VOICE;
  } catch {
    return DEFAULT_VOICE;
  }
}

export function storeVoice(voiceId) {
  try {
    localStorage.setItem(STORAGE_KEY, voiceId);
  } catch {}
}

export async function fetchVoices() {
  try {
    const voices = await api.get('/tts/voices');
    if (Array.isArray(voices) && voices.length > 0) return voices;
  } catch {}
  return FALLBACK_VOICES;
}

// POST /tts/speak (tra mp3 nhi phan) -> object URL de <audio> play.
export async function speakToAudioUrl(text, voice) {
  const base = '/api/v1';
  const response = await fetch(`${base}/tts/speak`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ text, voice: voice || getStoredVoice() }),
  });
  if (!response.ok) {
    throw new Error(`TTS failed (${response.status})`);
  }
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}
