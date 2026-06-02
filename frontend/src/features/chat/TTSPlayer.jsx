import { useEffect, useState, useRef } from 'react';
import { HiSpeakerWave, HiPlay, HiPause } from 'react-icons/hi2';

export function TTSPlayer({ text, onPlay, audioUrl }) {
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef(null);

  function togglePlay() {
    if (audioUrl) {
      if (playing) {
        audioRef.current?.pause();
      } else {
        audioRef.current?.play();
      }
      setPlaying(!playing);
      return;
    }

    onPlay?.(text);
    setPlaying(true);

    setTimeout(() => setPlaying(false), 3000);
  }

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (audioUrl && audioRef.current) {
      audioRef.current.src = audioUrl;
      audioRef.current.play().then(() => setPlaying(true)).catch(() => setPlaying(false));
    }
  }, [audioUrl]);

  return (
    <button
      onClick={togglePlay}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '6px 14px', borderRadius: 99,
        background: playing ? 'var(--color-accent-muted)' : 'var(--color-bg-surface)',
        border: '1px solid var(--color-border)',
        cursor: 'pointer', color: playing ? 'var(--color-accent)' : 'var(--color-text-secondary)',
        fontFamily: 'inherit', fontSize: '0.78rem', fontWeight: 600,
        transition: 'all 0.12s',
      }}
      onMouseOver={(e) => { e.currentTarget.style.background = 'var(--color-bg-hover)'; }}
      onMouseOut={(e) => { e.currentTarget.style.background = playing ? 'var(--color-accent-muted)' : 'var(--color-bg-surface)'; }}
    >
      {playing ? <HiPause size={16} /> : <HiSpeakerWave size={16} />}
      {playing ? 'Playing...' : 'Hear it'}
    </button>
  );
}
