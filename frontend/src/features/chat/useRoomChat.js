import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchJson } from '../../lib/api';

function parseMeta(raw) {
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

function toItem(msg) {
  const meta = parseMeta(msg.meta_data);
  const kind = meta.source === 'speech_to_text' ? 'transcript' : msg.role === 'ai' ? 'ai' : 'chat';
  return {
    id: msg.id,
    kind,
    userId: msg.user_id ?? null,
    sender: msg.user_name || null,
    text: msg.text || '',
    confidence: meta.confidence ?? null,
    aiType: meta.type || null,
    sourceId: meta.source_message_id ?? null,
    time: msg.created_at ? new Date(msg.created_at).getTime() : Date.now(),
  };
}

function isLiveAiId(id) {
  return typeof id === 'string' && id.startsWith('ai-');
}

export function useRoomChat(roomId) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const knownIds = useRef(new Set());
  const namesRef = useRef(new Map());
  const streamsRef = useRef(new Map());
  const roomIdRef = useRef(roomId);
  roomIdRef.current = roomId;

  const resolveName = useCallback(async (userId) => {
    if (!userId || namesRef.current.has(userId)) return;
    try {
      const user = await fetchJson(`/users/${userId}`);
      if (user?.full_name) namesRef.current.set(userId, user.full_name);
    } catch {}
  }, []);

  const mergeMessages = useCallback(
    async (msgs) => {
      const fresh = [];
      for (const msg of msgs || []) {
        if (msg.id == null || knownIds.current.has(msg.id)) continue;
        knownIds.current.add(msg.id);
        if (msg.user_id) await resolveName(msg.user_id);
        fresh.push(msg);
      }
      if (fresh.length === 0) return;
      const hasDbAi = fresh.some((msg) => msg.role === 'ai' && msg.id != null);
      setItems((prev) => {
        let base = prev;
        // DB da co ban AI chinh thuc → xoa cac bubble live tam (pending/streaming) tranh trung
        if (hasDbAi) base = prev.filter((it) => !isLiveAiId(it.id));
        const have = new Set(base.map((it) => it.id));
        const mapped = [];
        for (const msg of fresh) {
          if (have.has(msg.id)) continue;
          have.add(msg.id);
          const item = toItem(msg);
          if (!item.sender && item.userId && namesRef.current.has(item.userId)) {
            item.sender = namesRef.current.get(item.userId);
          }
          mapped.push(item);
        }
        if (mapped.length === 0 && base === prev) return prev;
        return [...base, ...mapped].sort((a, b) => a.time - b.time).slice(-200);
      });
    },
    [resolveName],
  );

  const loadHistory = useCallback(async () => {
    if (!roomIdRef.current) return;
    setLoading(true);
    setError('');
    try {
      const msgs = await fetchJson(`/messages/?room_id=${roomIdRef.current}&limit=100`);
      knownIds.current.clear();
      streamsRef.current.clear();
      setItems([]);
      await mergeMessages(msgs);
    } catch (err) {
      setError(err.message || 'Could not load chat');
    } finally {
      setLoading(false);
    }
  }, [mergeMessages]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory, roomId]);

  // Poll de bat kip AI replies + transcripts khi miss realtime
  useEffect(() => {
    if (!roomId) return;
    const timer = setInterval(async () => {
      try {
        const msgs = await fetchJson(`/messages/?room_id=${roomId}&limit=30`);
        await mergeMessages(msgs);
      } catch {}
    }, 4000);
    return () => clearInterval(timer);
  }, [roomId, mergeMessages]);

  // Live events tu LiveKit Data Channel (transcript + ai_stream)
  const handleLiveData = useCallback(
    (data) => {
      if (!data || typeof data !== 'object') return;
      if (data.room_id != null && String(data.room_id) !== String(roomIdRef.current)) return;

      if (data.type === 'transcript' && data.text) {
        const id = data.message_id ?? `live-${Date.now()}`;
        if (knownIds.current.has(id)) return;
        knownIds.current.add(id);
        setItems((prev) => {
          if (prev.some((it) => it.id === id)) return prev;
          return [...prev, { id, kind: 'transcript', userId: data.user_id ?? null, sender: data.user_name || 'Someone', text: data.text, confidence: data.confidence ?? null, time: Date.now() }]
            .sort((a, b) => a.time - b.time)
            .slice(-200);
        });
      } else if (data.type === 'ai_stream') {
        const key = data.stream_id || 'default';
        // Chunk that dau tien ve → xoa placeholder "thinking"
        setItems((prev) => (prev.some((it) => it.id === 'ai-pending') ? prev.filter((it) => it.id !== 'ai-pending') : prev));
        if (data.is_final) {
          const stream = streamsRef.current.get(key) || { text: '', thinking: '' };
          streamsRef.current.delete(key);
          if (!stream.text && !stream.thinking) return;
          const id = `ai-${key}`;
          if (knownIds.current.has(id)) return;
          knownIds.current.add(id);
          setItems((prev) => {
            if (prev.some((it) => it.id === id)) return prev;
            return [...prev, { id, kind: 'ai', userId: null, sender: 'AI', text: stream.text, thinkingText: stream.thinking || undefined, time: Date.now() }].slice(-200);
          });
        } else if (data.chunk) {
          const prev = streamsRef.current.get(key) || { text: '', thinking: '' };
          if (data.thinking) prev.thinking += data.chunk;
          else prev.text += data.chunk;
          streamsRef.current.set(key, prev);
          const id = `ai-${key}`;
          setItems((prevItems) => {
            const rest = prevItems.filter((it) => it.id !== id);
            return [...rest, { id, kind: 'ai', userId: null, sender: 'AI', text: prev.text, thinkingText: prev.thinking || undefined, streaming: true, time: Date.now() }].slice(-200);
          });
        }
      }
    },
    [],
  );

  const send = useCallback(
    async (text) => {
      const clean = String(text || '').trim();
      if (!clean || !roomIdRef.current) return false;
      const isAiQuery = clean.replace(/^\s+/, '').toLowerCase().startsWith('@ai');
      setSending(true);
      // Hien "thinking" ngay lap tuc khi hoi @ai (LLM can vai chuc giay)
      if (isAiQuery) {
        setItems((prev) =>
          prev.some((it) => it.id === 'ai-pending')
            ? prev
            : [...prev, { id: 'ai-pending', kind: 'ai', userId: null, sender: 'AI', text: '', thinking: true, time: Date.now() }].slice(-200),
        );
      }
      try {
        const saved = await fetchJson('/messages/', {
          method: 'POST',
          body: JSON.stringify({ room_id: Number(roomIdRef.current), text: clean }),
        });
        if (saved?.id) knownIds.current.add(saved.id);
        const item = toItem({ ...saved, text: clean });
        item.sender = item.sender || 'You';
        setItems((prev) => {
          if (prev.some((it) => it.id === item.id)) return prev;
          return [...prev, item].sort((a, b) => a.time - b.time).slice(-200);
        });
        return true;
      } catch (err) {
        setError(err.message || 'Could not send message');
        setItems((prev) => prev.filter((it) => it.id !== 'ai-pending'));
        return false;
      } finally {
        setSending(false);
      }
    },
    [],
  );

  return { items, loading, sending, error, send, reload: loadHistory, handleLiveData };
}
