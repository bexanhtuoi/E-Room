import { API_BASE_URL } from '../api/client';

const SAMPLE_RATE = 16000;
const CHUNK_INTERVAL_MS = 100;
const BUFFER_SIZE = 2048;

export function createAudioCapture(roomId, token, audioWsRef, onStateChange) {
  let audioCtx = null;
  let source = null;
  let processor = null;
  let stream = null;
  let ws = null;
  let seq = 0;
  let isActive = false;

  function connectWs() {
    const base = API_BASE_URL
      .replace('http://', 'ws://')
      .replace('https://', 'wss://')
      .replace('/api/v1', '');
    const url = `${base}/ws/audio/${roomId}?token=${token}`;
    ws = new WebSocket(url);
    ws.onopen = () => { audioWsRef.current = ws; };
    ws.onclose = () => { audioWsRef.current = null; };
    ws.onerror = () => { ws?.close(); };
  }

  async function start() {
    if (isActive) return;
    isActive = true;

    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: SAMPLE_RATE });
      source = audioCtx.createMediaStreamSource(stream);
      processor = audioCtx.createScriptProcessor(BUFFER_SIZE, 1, 1);
      connectWs();
      onStateChange?.(true);

      processor.onaudioprocess = (e) => {
        if (!isActive) return;
        const input = e.inputBuffer.getChannelData(0);
        const pcm16 = new Int16Array(input.length);
        for (let i = 0; i < input.length; i++) {
          const s = Math.max(-1, Math.min(1, input[i]));
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        const bytes = new Uint8Array(pcm16.buffer);
        const binary = String.fromCharCode(...bytes);
        const base64 = btoa(binary);

        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ pcm: base64, seq: seq++ }));
        }
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);
    } catch (err) {
      console.error('Audio capture failed:', err);
      isActive = false;
      onStateChange?.(false);
    }
  }

  function stop() {
    isActive = false;
    processor?.disconnect();
    source?.disconnect();
    audioCtx?.close();
    stream?.getTracks().forEach(t => t.stop());
    ws?.close();
    audioWsRef.current = null;
    processor = null;
    source = null;
    audioCtx = null;
    stream = null;
    ws = null;
    seq = 0;
    onStateChange?.(false);
  }

  return { start, stop, get isActive() { return isActive; } };
}
