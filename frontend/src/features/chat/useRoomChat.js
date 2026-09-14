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

// Sort on dinh: bang time truoc, id sau (burst cung ms khong nhay thu tu).
// Id so phai so NUMERIC — so string "30008" < "999" se xep sai va
// slice(-200) cat mat tin moi nhat trong phong dong.
export function compareIds(a, b) {
  if (a === b) return 0;
  const na = typeof a === 'number' ? a : Number(a);
  const nb = typeof b === 'number' ? b : Number(b);
  const aNum = Number.isFinite(na);
  const bNum = Number.isFinite(nb);
  if (aNum && bNum) return na - nb;
  if (aNum !== bNum) return aNum ? -1 : 1;
  return String(a) < String(b) ? -1 : 1;
}

function byTime(a, b) {
  if (a.time !== b.time) return a.time - b.time;
  return compareIds(a.id, b.id);
}

let liveCounter = 0;

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
  // Moc gio don dieu: gio server co the lech gio browser (VD container
  // Docker drift sau sleep) → tin ve sau phai dung sau, khong duoc nhay len tren.
  const maxTimeRef = useRef(0);

  function stampTime(serverTime) {
    const t = Number.isFinite(serverTime) ? serverTime : Date.now();
    const clamped = Math.max(t, maxTimeRef.current);
    maxTimeRef.current = clamped;
    return clamped;
  }
  // Cau @ai vua gui — de gan quote (sourceId) cho bubble live cua chinh no.
  // Dung 1 lan roi thoi (used) de heartbeat sau do khong an quote nham.
  const aiSourceRef = useRef(null);

  // Chunk dau tien cua stream thi "nhan" sourceId (@ai vua gui, neu chua dung).
  // isFirst phai chup TRUOC khi streamsRef.set (goi trong setItems la muon).
  function claimSourceId(isFirst, existingSourceId) {
    if (existingSourceId != null) return existingSourceId;
    if (!isFirst) return undefined;
    const claim = aiSourceRef.current;
    if (claim && !claim.used && claim.id != null) {
      claim.used = true;
      return claim.id;
    }
    return undefined;
  }

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
      const freshIds = new Set(fresh.map((msg) => msg.id));
      setItems((prev) => {
        let base = prev;
        // DB da co ban AI chinh thuc → xoa cac bubble live tam (pending/streaming) tranh trung
        if (hasDbAi) base = prev.filter((it) => !isLiveAiId(it.id));
        // Transcript live da co ban DB (cung message_id) → xoa ban live tranh double
        base = base.filter((it) => !(it.kind === 'transcript' && typeof it.id === 'string' && it.messageId != null && freshIds.has(it.messageId)));
        const have = new Set(base.map((it) => it.id));
        const mapped = [];
        for (const msg of fresh) {
          if (have.has(msg.id)) continue;
          have.add(msg.id);
          const item = toItem(msg);
          item.time = stampTime(item.time);
          if (!item.sender && item.userId && namesRef.current.has(item.userId)) {
            item.sender = namesRef.current.get(item.userId);
          }
          mapped.push(item);
        }
        if (mapped.length === 0 && base === prev) return prev;
        return [...base, ...mapped].sort(byTime).slice(-200);
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
      maxTimeRef.current = 0;
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
        // Id duy nhat tuyet doi (2 cau cung ms khong trung key React)
        const id = data.message_id ?? `live-${Date.now()}-${++liveCounter}`;
        if (knownIds.current.has(id)) return;
        knownIds.current.add(id);
        setItems((prev) => {
          if (prev.some((it) => it.id === id)) return prev;
          return [...prev, { id, kind: 'transcript', messageId: data.message_id ?? null, userId: data.user_id ?? null, sender: data.user_name || 'Someone', text: data.text, confidence: data.confidence ?? null, time: stampTime(Date.now()) }]
            .sort(byTime)
            .slice(-200);
        });
      } else if (data.type === 'ai_stream') {
        const key = data.stream_id || 'default';
        const id = `ai-${key}`;
        const jobId = data.job_id ? String(data.job_id) : '';
        // Stream thu lai cung job: xoa khung do + entry stream cu
        if (jobId) {
          for (const [streamKey, stream] of streamsRef.current.entries()) {
            if (streamKey !== key && stream?.jobId === jobId) streamsRef.current.delete(streamKey);
          }
        }
        const dropSuperseded = (list) => (
          jobId ? list.filter((it) => !(it.jobId === jobId && it.id !== id && it.streaming)) : list
        );
        // Stream moi nhat thang: tat co streaming + thinking cua stream cu
        const settleOthers = (list) => list.map((it) => (
          isLiveAiId(it.id) && it.id !== id && it.id !== 'ai-pending' && it.streaming
            ? { ...it, streaming: false }
            : it
        ));
        // Chunk that dau tien ve → xoa placeholder "thinking"
        setItems((prev) => {
          const settled = settleOthers(dropSuperseded(prev));
          return settled.some((it) => it.id === 'ai-pending') ? settled.filter((it) => it.id !== 'ai-pending') : settled;
        });
        if (data.is_final) {
          const isFirst = !streamsRef.current.has(key);
          const stream = streamsRef.current.get(key) || { text: '', thinking: '' };
          streamsRef.current.delete(key);
          if (!stream.text && !stream.thinking) return;
          if (knownIds.current.has(id)) return;
          knownIds.current.add(id);
          setItems((prev) => {
            // Final thay the bubble streaming cung id (giu vi tri), dong thinking
            const existing = prev.find((it) => it.id === id);
            const rest = settleOthers(dropSuperseded(prev)).filter((it) => it.id !== id);
            return [...rest, { id, kind: 'ai', userId: null, sender: 'AI', text: stream.text, thinkingText: stream.thinking || undefined, streaming: false, jobId: jobId || undefined, sourceId: claimSourceId(isFirst, existing?.sourceId), time: stampTime(Date.now()) }].slice(-200);
          });
        } else if (data.chunk) {
          const isFirst = !streamsRef.current.has(key);
          const prev = streamsRef.current.get(key) || { text: '', thinking: '' };
          if (data.thinking) prev.thinking += data.chunk;
          else prev.text += data.chunk;
          if (jobId) prev.jobId = jobId;
          streamsRef.current.set(key, prev);
          setItems((prevItems) => {
            const existing = prevItems.find((it) => it.id === id);
            const rest = settleOthers(dropSuperseded(prevItems)).filter((it) => it.id !== id);
            return [...rest, { id, kind: 'ai', userId: null, sender: 'AI', text: prev.text, thinkingText: prev.thinking || undefined, streaming: true, jobId: jobId || undefined, sourceId: claimSourceId(isFirst, existing?.sourceId), time: stampTime(Date.now()) }].slice(-200);
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
            : [...prev, { id: 'ai-pending', kind: 'ai', userId: null, sender: 'AI', text: '', thinking: true, time: stampTime(Date.now()) }].slice(-200),
        );
      }
      try {
        const saved = await fetchJson('/messages/', {
          method: 'POST',
          body: JSON.stringify({ room_id: Number(roomIdRef.current), text: clean }),
        });
        if (saved?.id) knownIds.current.add(saved.id);
        // Nho cau @ai de gan quote cho stream live sap ve
        if (isAiQuery && saved?.id != null) {
          aiSourceRef.current = { id: saved.id, used: false };
        }
        const item = toItem({ ...saved, text: clean });
        item.sender = item.sender || 'You';
        item.time = stampTime(item.time);
        setItems((prev) => {
          if (item.id != null && prev.some((it) => it.id === item.id)) return prev;
          return [...prev, item].sort(byTime).slice(-200);
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
