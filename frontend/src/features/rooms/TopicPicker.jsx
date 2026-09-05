import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchJson } from '../../lib/api';

export const MAX_TOPICS = 5;

export function normalizeTopic(text) {
  return String(text || '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => (/^[a-z]/.test(w) && w === w.toLowerCase() ? w.charAt(0).toUpperCase() + w.slice(1) : w))
    .join(' ');
}

export function TopicPicker({ topics, onChange }) {
  const [customTopic, setCustomTopic] = useState('');

  const { data: rooms } = useQuery({
    queryKey: ['rooms', 'topics'],
    queryFn: () => fetchJson('/rooms/?limit=50'),
    staleTime: 60_000,
  });

  const suggestions = useMemo(() => {
    const seen = new Set();
    (rooms || []).forEach((r) => (Array.isArray(r.topics) ? r.topics : []).forEach((t) => {
      const name = normalizeTopic(t);
      if (name && !seen.has(name.toLowerCase())) seen.add(name);
    }));
    topics.forEach((t) => seen.delete(String(t).toLowerCase()));
    return [...seen].slice(0, 8);
  }, [rooms, topics]);

  function add(raw) {
    const name = normalizeTopic(raw);
    if (!name) return;
    if (topics.some((t) => String(t).toLowerCase() === name.toLowerCase())) return;
    if (topics.length >= MAX_TOPICS) return;
    onChange([...topics, name]);
    setCustomTopic('');
  }

  function remove(name) {
    onChange(topics.filter((t) => t !== name));
  }

  const full = topics.length >= MAX_TOPICS;

  return (
    <div>
      {topics.length > 0 && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
          {topics.map((t) => (
            <span key={t} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: '#111', color: '#fff', fontSize: 13, fontWeight: 700, padding: '7px 8px 7px 12px' }}>
              {t}
              <button type="button" onClick={() => remove(t)} aria-label={`Remove ${t}`} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 800 }}>✕</button>
            </span>
          ))}
        </div>
      )}
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          className="er-input"
          value={customTopic}
          onChange={(e) => setCustomTopic(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); add(customTopic); } }}
          placeholder={full ? 'Topic list is full' : 'Type a topic and press Enter…'}
          disabled={full}
        />
        <button type="button" className="er-btn er-btn--ghost" style={{ flexShrink: 0 }} disabled={full || !customTopic.trim()} onClick={() => add(customTopic)}>+ Add</button>
      </div>
      {suggestions.length > 0 && !full && (
        <div style={{ marginTop: 10 }}>
          <div style={{ fontSize: 12, color: '#999', marginBottom: 6 }}>Or pick from live rooms:</div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {suggestions.map((t) => (
              <button key={t} type="button" onClick={() => add(t)} style={{ background: '#fff', border: '1px solid #e8e8e8', fontSize: 13, fontWeight: 700, padding: '7px 12px', cursor: 'pointer' }}>+ {t}</button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
