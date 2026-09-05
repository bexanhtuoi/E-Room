import { useState } from 'react';
import { fetchJson } from '../../lib/api';
import { MAX_TOPICS, TopicPicker } from './TopicPicker';

const SEAT_OPTS = [2, 3, 4];

export function CreateRoomModal({ onClose, onRoomCreated }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [topics, setTopics] = useState([]);
  const [seats, setSeats] = useState(4);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(event) {
    event.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    setError('');
    try {
      const room = await fetchJson('/rooms/', {
        method: 'POST',
        body: JSON.stringify({
          name: name.trim(),
          topics,
          description: description.trim() || undefined,
          max_participants: seats,
        }),
      });
      if (onRoomCreated) onRoomCreated(room);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to create room');
    } finally {
      setSaving(false);
    }
  }

  const full = topics.length >= MAX_TOPICS;

  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
      <div onClick={(e) => e.stopPropagation()} style={{ background: '#fff', border: '2px solid #111', maxWidth: 560, width: '100%', maxHeight: '90svh', overflowY: 'auto', padding: 'clamp(24px,4vw,36px)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16 }}>
          <div>
            <span className="er-tag">New room</span>
            <h3 style={{ fontSize: 26, margin: '12px 0 6px' }}>Create a room</h3>
            <p style={{ color: '#666', fontSize: 14, margin: 0 }}>One name, a few topics, and the room opens immediately.</p>
          </div>
          <button onClick={onClose} aria-label="Close" style={{ background: '#fff', border: '1px solid #111', width: 36, height: 36, fontWeight: 800, cursor: 'pointer', flexShrink: 0 }}>✕</button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 16, marginTop: 22 }}>
          <div>
            <label className="er-label">Room name *</label>
            <input className="er-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. AI Agents & Automation" autoFocus />
          </div>

          <div>
            <label className="er-label">Description</label>
            <textarea className="er-textarea" rows={3} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What will you talk about? Any house rules?" />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <label className="er-label" style={{ margin: 0 }}>Topics</label>
              <span style={{ fontSize: 12, fontWeight: 800, color: topics.length >= MAX_TOPICS ? '#111' : '#999' }}>{topics.length}/{MAX_TOPICS}</span>
            </div>
            <TopicPicker topics={topics} onChange={setTopics} />
          </div>

          <div>
            <label className="er-label">Seats</label>
            <div style={{ display: 'flex', gap: 8 }}>
              {SEAT_OPTS.map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setSeats(n)}
                  style={{ flex: 1, padding: '12px 0', fontWeight: 800, cursor: 'pointer', background: seats === n ? '#111' : '#fff', color: seats === n ? '#fff' : '#111', border: '1px solid #111' }}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>

          {error && <div className="er-alert er-alert--err">{error}</div>}
          <div style={{ display: 'flex', gap: 10 }}>
            <button type="button" className="er-btn er-btn--ghost" style={{ flex: 1, justifyContent: 'center' }} onClick={onClose}>Cancel</button>
            <button type="submit" className="er-btn" style={{ flex: 2, justifyContent: 'center' }} disabled={saving || !name.trim()}>
              {saving ? 'Creating…' : 'Create room →'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
