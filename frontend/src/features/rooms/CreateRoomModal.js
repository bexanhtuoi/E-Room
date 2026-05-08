import { useState } from 'react';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1';

export function CreateRoomModal({ onClose, onRoomCreated }) {
  const [topic, setTopic] = useState('');
  const [tagIds, setTagIds] = useState('');
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!topic.trim()) return;

    const tagList = tagIds
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    if (tagList.length === 0) return;

    setSaving(true);
    try {
      const response = await fetch(`${API_BASE_URL}/rooms`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: topic.trim(), tag_ids: tagList, max_participants: 5 }),
      });
      const room = await response.json();
      if (response.ok && onRoomCreated) onRoomCreated(room);
    } finally {
      setSaving(false);
      onClose();
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>Create a room</h3>
        <p>Start a new English-speaking room with topic tags.</p>
        <form onSubmit={handleSubmit}>
          <div className="form-stack">
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Room topic (e.g. AI job interview)"
              autoFocus
            />
            <input
              value={tagIds}
              onChange={(e) => setTagIds(e.target.value)}
              placeholder="Tag IDs, comma separated (e.g. AI/ML, DevOps)"
            />
          </div>
          <div className="form-row" style={{ marginTop: 16 }}>
            <button type="button" className="outline" onClick={onClose}>Cancel</button>
            <button type="submit" disabled={saving || !topic.trim()}>
              {saving ? 'Creating...' : 'Create Room'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
