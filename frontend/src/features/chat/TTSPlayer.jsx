import { useEffect, useState, useRef } from 'react';
import { HiSpeakerWave, HiPlay, HiPause } from 'react-icons/hi2';
import './TTSPlayer.css';
import { getStoredVoice, speakToAudioUrl } from './voiceApi';

export function TTSPlayer({ text, onPlay, audioUrl, voice }) {
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const audioRef = useRef(null);
  const blobUrlRef = useRef(null);

  function playUrl(url) {
    if (!audioRef.current) audioRef.current = new Audio();
    audioRef.current.src = url;
    audioRef.current.onended = () => setPlaying(false);
    audioRef.current.play().then(() => setPlaying(true)).catch(() => setPlaying(false));
  }

  async function togglePlay() {
    if (playing) {
      audioRef.current?.pause();
      setPlaying(false);
      return;
    }
    // Phát lại URL đã tải (đỡ gọi API lần nữa)
    const cached = audioUrl || blobUrlRef.current;
    if (cached) {
      playUrl(cached);
      return;
    }
    // Gọi TTS server với giọng đang chọn
    setLoading(true);
    setFailed(false);
    try {
      const url = await speakToAudioUrl(text, voice || getStoredVoice());
      blobUrlRef.current = url;
      playUrl(url);
    } catch {
      setFailed(true);
      onPlay?.(text);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    return () => {
      audioRef.current?.pause();
      audioRef.current = null;
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (audioUrl) playUrl(audioUrl);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [audioUrl]);

  const label = loading ? 'Loading…' : failed ? 'Retry' : playing ? 'Playing...' : 'Hear it';

  return (
    <button
      onClick={togglePlay}
      disabled={loading || !text}
      className="tts-player-btn"
      style={{
        background: playing ? 'var(--color-accent-muted)' : 'var(--color-bg-surface)',
        color: playing ? 'var(--color-accent)' : 'var(--color-text-secondary)',
        opacity: loading ? 0.6 : 1,
      }}
      onMouseOver={(e) => { e.currentTarget.style.background = 'var(--color-bg-hover)'; }}
      onMouseOut={(e) => { e.currentTarget.style.background = playing ? 'var(--color-accent-muted)' : 'var(--color-bg-surface)'; }}
    >
      {playing ? <HiPause size={16} /> : loading ? <HiPlay size={16} /> : <HiSpeakerWave size={16} />}
      {label}
    </button>
  );
}
