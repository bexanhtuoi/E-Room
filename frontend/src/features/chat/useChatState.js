import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchJson } from '../../lib/api';
import { useAuth } from '../../app/AuthContext';

export function useChatState(roomId, wsSocket, visible) {
  const { user } = useAuth();
  const currentUser = user?.display_name || 'You';
  const currentUserId = user?.id || 'me';

  const [transcripts, setTranscripts] = useState([]);
  const [corrections, setCorrections] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [input, setInput] = useState('');

  const wsRef = useRef(wsSocket);
  const inputRef = useRef(null);
  const bottomRef = useRef(null);

  useEffect(() => { wsRef.current = wsSocket; }, [wsSocket]);

  // WebSocket listeners
  useEffect(() => {
    const ws = wsRef.current;
    if (!ws) return;

    const isRaw = typeof ws.addEventListener === 'function';
    const listeners = [];

    function on(wsEvent, callback) {
      if (isRaw) {
        const handler = (e) => {
          try {
            const msg = JSON.parse(e.data);
            if (msg.type === wsEvent) callback(msg);
          } catch {}
        };
        ws.addEventListener('message', handler);
        listeners.push(() => ws.removeEventListener('message', handler));
      } else {
        const unsub = ws.on(wsEvent, callback);
        listeners.push(unsub);
      }
    }

    on('transcript', (data) => {
      setTranscripts((prev) => {
        const updated = [...prev];
        const lastIdx = updated.length - 1;
        if (data.status === 'interim' && lastIdx >= 0 && updated[lastIdx].status === 'interim') {
          updated[lastIdx] = { ...updated[lastIdx], text: data.text };
        } else if (data.status === 'interim') {
          updated.push({ id: Date.now(), speaker: data.speaker || data.user_id, text: data.text, status: 'interim', speakerColor: data.speaker_color });
        } else if (lastIdx >= 0 && updated[lastIdx].status === 'interim' && updated[lastIdx].speaker === (data.speaker || data.user_id)) {
          updated[lastIdx] = { ...updated[lastIdx], text: data.text, status: 'final' };
        } else {
          updated.push({ id: Date.now(), speaker: data.speaker || data.user_id, text: data.text, status: 'final', speakerColor: data.speaker_color });
        }
        return updated.slice(-200);
      });
    });

    on('correction', (data) => {
      setCorrections((prev) => {
        const item = {
          id: data.id || Date.now(),
          original: data.original,
          corrected: data.corrected,
          explanation: data.explanation,
          pronunciation_feedback: data.pronunciation_feedback || '',
          errors: data.errors || [],
          tts_text: data.tts_text || data.corrected,
          user_id: data.user_id,
          time: data.created_at || Date.now(),
        };
        return [...prev, item].slice(-50);
      });
    });

    on('chat_message', (data) => {
      const userId = data.user_id || data.sender_id;
      setChatMessages((prev) => [...prev, {
        id: data.id || Date.now(),
        senderId: userId || 'guest',
        sender: data.display_name || 'User',
        text: data.content || data.text,
        time: new Date(data.timestamp || Date.now()),
      }]);
    });

    return () => listeners.forEach((fn) => fn?.());
  }, [wsSocket]);

  // Load chat history
  useEffect(() => {
    if (!roomId || !visible) return;
    setLoadingHistory(true);
    fetchJson(`/messages/rooms/${roomId}`)
      .then((msgs) => {
        if (Array.isArray(msgs)) {
          const chats = [];
          const speech = [];
          const correctionItems = [];
          for (const m of msgs) {
            if (m.message_type === 'ai_expert') {
              chats.push({ id: m.id, senderId: 'assistant', sender: 'assistant', text: m.content, time: new Date(m.created_at) });
            } else if (m.message_type === 'transcript') {
              speech.push({ id: m.id, speaker: m.payload?.display_name || 'You', text: m.content, status: 'final', time: new Date(m.created_at) });
            } else if (m.message_type === 'ai_correction') {
              const p = m.payload || {};
              correctionItems.push({ id: m.id, original: p.original || '', corrected: m.content, explanation: p.explanation || '', pronunciation_feedback: p.pronunciation_feedback || '', errors: p.errors || [], tts_text: p.tts_text || m.content, user_id: m.user_id, time: new Date(m.created_at) });
            } else {
              chats.push({
                id: m.id || Date.now() + Math.random(),
                senderId: m.user_id || 'guest',
                sender: m.payload?.display_name || m.display_name || m.user_id?.slice(0, 8) || 'User',
                text: m.content || m.text,
                time: new Date(m.created_at || Date.now()),
              });
            }
          }
          setChatMessages(chats);
          setTranscripts(speech);
          setCorrections(correctionItems);
        }
      })
      .catch(() => {})
      .finally(() => setLoadingHistory(false));
  }, [roomId, visible]);

  useEffect(() => {
    if (visible) setTimeout(() => inputRef.current?.focus(), 150);
  }, [visible]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, transcripts, corrections]);

  const handleSend = useCallback((e) => {
    e?.preventDefault();
    const text = input.trim();
    if (!text) return;

    setChatMessages((prev) => [...prev, {
      id: Date.now(), senderId: currentUserId, sender: currentUser, text, time: new Date(),
    }]);

    const ws = wsRef.current;
    if (ws && typeof ws.send === 'function') {
      const isRaw = typeof ws.addEventListener === 'function';
      const payload = { type: 'chat_message', content: text, room_id: roomId, timestamp: new Date().toISOString() };
      if (isRaw) {
        ws.send(JSON.stringify(payload));
      } else {
        ws.send(payload);
      }
    }
    setInput('');
  }, [input, currentUserId, currentUser, roomId]);

  const handleTTS = useCallback((text) => {
    const ws = wsRef.current;
    if (ws && typeof ws.send === 'function') {
      const isRaw = typeof ws.addEventListener === 'function';
      if (isRaw) {
        ws.send(JSON.stringify({ type: 'request_tts', text, room_id: roomId }));
      } else {
        ws.send({ type: 'request_tts', text, room_id: roomId });
      }
    }
  }, [roomId]);

  return {
    transcripts, corrections, chatMessages,
    loadingHistory, input, setInput, inputRef, bottomRef,
    handleSend, handleTTS, currentUser, currentUserId,
  };
}
