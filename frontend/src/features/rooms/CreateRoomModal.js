import { useState } from 'react';
import { fetchJson } from '../../lib/api';
import {
  HiXMark, HiPlusCircle, HiLanguage, HiUserGroup,
  HiDocumentText, HiTag, HiAcademicCap
} from 'react-icons/hi2';

const ENGLISH_LEVELS = [
  { value: 'A1', label: 'A1', desc: 'Beginner' },
  { value: 'A2', label: 'A2', desc: 'Elementary' },
  { value: 'B1', label: 'B1', desc: 'Intermediate' },
  { value: 'B2', label: 'B2', desc: 'Upper-Int' },
  { value: 'C1', label: 'C1', desc: 'Advanced' },
  { value: 'C2', label: 'C2', desc: 'Proficient' },
];

const PARTICIPANT_OPTS = [2, 3, 4, 5, 6, 8, 10, 15];

const SUGGESTED_TAGS = [
  'Business', 'Technology', 'Travel', 'Education',
  'IELTS', 'Daily Life', 'Pronunciation', 'Interview',
  'Culture', 'Science', 'Food', 'Music',
];

const labelStyle = {
  display: 'flex', alignItems: 'center', gap: 6,
  fontSize: '0.78rem', fontWeight: 600,
  color: 'var(--color-text-secondary)', marginBottom: 8,
};

const inputBase = {
  width: '100%', padding: '10px 14px', fontSize: '0.88rem',
  borderRadius: 12, border: '1px solid var(--color-border)',
  background: 'var(--color-bg-surface)',
  color: 'var(--color-text-primary)',
  outline: 'none', fontFamily: 'inherit', boxSizing: 'border-box',
  transition: 'border-color 0.15s, box-shadow 0.15s',
};

function focusIn(e) {
  e.currentTarget.style.borderColor = 'var(--color-accent)';
  e.currentTarget.style.boxShadow = '0 0 0 3px var(--color-accent-muted)';
}
function focusOut(e) {
  e.currentTarget.style.borderColor = 'var(--color-border)';
  e.currentTarget.style.boxShadow = 'none';
}

export function CreateRoomModal({ onClose, onRoomCreated }) {
  const [topic, setTopic] = useState('');
  const [description, setDescription] = useState('');
  const [tagIds, setTagIds] = useState('');
  const [level, setLevel] = useState('');
  const [maxParticipants, setMaxParticipants] = useState(5);
  const [saving, setSaving] = useState(false);

  function addTag(tag) {
    const current = tagIds.split(',').map(t => t.trim()).filter(Boolean);
    if (!current.includes(tag)) {
      setTagIds(prev => prev ? `${prev}, ${tag}` : tag);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!topic.trim()) return;

    const tagList = tagIds
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    if (tagList.length === 0) {
      alert('Please enter at least one tag');
      return;
    }

    setSaving(true);
    try {
      const room = await fetchJson('/rooms', {
        method: 'POST',
        body: JSON.stringify({
          topic: topic.trim(),
          tag_ids: tagList,
          max_participants: maxParticipants,
          english_level: level || undefined,
          description: description.trim() || undefined,
        }),
      });
      if (onRoomCreated) onRoomCreated(room);
      onClose();
    } catch (err) {
      alert(err.message || 'Failed to create room');
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0, zIndex: 1050,
          background: 'rgba(0,0,0,0.55)', backdropFilter: 'blur(4px)',
          display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
          padding: '5vh 16px 16px', overflowY: 'auto',
        }}
      >
        <div
          onClick={(e) => e.stopPropagation()}
          style={{
            background: 'var(--color-bg-elevated)',
            border: '1px solid var(--color-border-strong)',
            borderRadius: 20, maxWidth: 520, width: '100%',
            padding: '28px 24px 24px',
            boxShadow: '0 20px 60px rgba(0,0,0,0.45)',
            animation: 'scaleIn 0.22s ease both',
            marginTop: 'auto', marginBottom: 'auto',
          }}
        >
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
            <div>
              <h3 style={{
                fontFamily: "'Nunito', sans-serif", fontWeight: 800,
                fontSize: '1.2rem', margin: 0, color: 'var(--color-text-primary)',
              }}>
                Create a Room
              </h3>
              <p style={{ margin: '4px 0 0', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                Fill in the details to start a new English-speaking session
              </p>
            </div>
            <button
              onClick={onClose}
              style={{
                width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
                background: 'var(--color-bg-hover)', border: 'none',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', color: 'var(--color-text-muted)',
                transition: 'all 0.15s',
              }}
              onMouseOver={(e) => { e.currentTarget.style.background = 'var(--color-border-strong)'; e.currentTarget.style.color = 'var(--color-text-primary)'; }}
              onMouseOut={(e) => { e.currentTarget.style.background = 'var(--color-bg-hover)'; e.currentTarget.style.color = 'var(--color-text-muted)'; }}
            >
              <HiXMark size={16} />
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            {/* Topic */}
            <label style={labelStyle}>
              <HiTag size={14} style={{ color: 'var(--color-accent)' }} />
              Room Topic *
            </label>
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. AI Job Interview Practice"
              autoFocus
              style={{ ...inputBase, marginBottom: 16 }}
              onFocus={focusIn} onBlur={focusOut}
            />

            {/* Description */}
            <label style={labelStyle}>
              <HiDocumentText size={14} style={{ color: 'var(--color-accent)' }} />
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What will you discuss? Any special rules or topics?"
              rows={3}
              style={{ ...inputBase, marginBottom: 16, resize: 'vertical', minHeight: 72 }}
              onFocus={focusIn} onBlur={focusOut}
            />

            {/* English Level */}
            <label style={labelStyle}>
              <HiAcademicCap size={14} style={{ color: 'var(--color-accent)' }} />
              English Level
            </label>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 16 }}>
              {ENGLISH_LEVELS.map((lvl) => (
                <button
                  key={lvl.value}
                  type="button"
                  onClick={() => setLevel(prev => prev === lvl.value ? '' : lvl.value)}
                  title={lvl.desc}
                  style={{
                    padding: '7px 14px', borderRadius: 99,
                    background: level === lvl.value
                      ? 'var(--color-accent-gradient)'
                      : 'var(--color-bg-surface)',
                    color: level === lvl.value ? '#fff' : 'var(--color-text-secondary)',
                    border: level === lvl.value ? 'none' : '1px solid var(--color-border)',
                    cursor: 'pointer', fontWeight: 600, fontSize: '0.78rem',
                    fontFamily: 'inherit', transition: 'all 0.15s',
                    display: 'flex', flexDirection: 'column', alignItems: 'center',
                    gap: 1, minWidth: 44,
                  }}
                >
                  <span style={{ fontSize: '0.85rem' }}>{lvl.label}</span>
                  <span style={{ fontSize: '0.58rem', fontWeight: 400, opacity: 0.8 }}>{lvl.desc}</span>
                </button>
              ))}
            </div>

            {/* Max Participants */}
            <label style={labelStyle}>
              <HiUserGroup size={14} style={{ color: 'var(--color-accent)' }} />
              Max Participants
            </label>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 16 }}>
              {PARTICIPANT_OPTS.map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setMaxParticipants(n)}
                  style={{
                    width: 38, height: 38, borderRadius: '50%',
                    background: maxParticipants === n
                      ? 'var(--color-accent-gradient)'
                      : 'var(--color-bg-surface)',
                    color: maxParticipants === n ? '#fff' : 'var(--color-text-secondary)',
                    border: maxParticipants === n ? 'none' : '1px solid var(--color-border)',
                    cursor: 'pointer', fontWeight: 700, fontSize: '0.82rem',
                    fontFamily: 'inherit', transition: 'all 0.15s',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}
                >
                  {n}
                </button>
              ))}
            </div>

            {/* Tags */}
            <label style={labelStyle}>
              <HiTag size={14} style={{ color: 'var(--color-accent)' }} />
              Tags * <span style={{ fontWeight: 400, fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>(comma separated)</span>
            </label>
            <input
              value={tagIds}
              onChange={(e) => setTagIds(e.target.value)}
              placeholder="e.g. Business, Technology, Travel"
              style={{ ...inputBase, marginBottom: 8 }}
              onFocus={focusIn} onBlur={focusOut}
            />
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 20 }}>
              {SUGGESTED_TAGS.map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => addTag(tag)}
                  style={{
                    padding: '3px 10px', borderRadius: 99,
                    background: tagIds.includes(tag) ? 'var(--color-accent-muted)' : 'var(--color-bg-hover)',
                    color: tagIds.includes(tag) ? 'var(--color-accent)' : 'var(--color-text-muted)',
                    border: tagIds.includes(tag) ? '1px solid var(--color-accent)' : '1px solid transparent',
                    cursor: 'pointer', fontSize: '0.68rem', fontWeight: 600,
                    fontFamily: 'inherit', transition: 'all 0.15s',
                  }}
                >
                  + {tag}
                </button>
              ))}
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', paddingTop: 4, borderTop: '1px solid var(--color-border)' }}>
              <button
                type="button"
                onClick={onClose}
                style={{
                  padding: '10px 22px', borderRadius: 99,
                  background: 'var(--color-bg-surface)', color: 'var(--color-text-secondary)',
                  border: '1px solid var(--color-border)', cursor: 'pointer',
                  fontWeight: 600, fontSize: '0.85rem', fontFamily: 'inherit',
                  transition: 'all 0.15s',
                }}
                onMouseOver={(e) => { e.currentTarget.style.background = 'var(--color-bg-hover)'; }}
                onMouseOut={(e) => { e.currentTarget.style.background = 'var(--color-bg-surface)'; }}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving || !topic.trim()}
                style={{
                  padding: '10px 24px', borderRadius: 99,
                  background: 'var(--color-accent-gradient)', color: '#fff',
                  border: 'none', cursor: saving || !topic.trim() ? 'not-allowed' : 'pointer',
                  fontWeight: 700, fontSize: '0.85rem', fontFamily: 'inherit',
                  display: 'flex', alignItems: 'center', gap: 6,
                  opacity: saving || !topic.trim() ? 0.6 : 1,
                  transition: 'all 0.15s', boxShadow: '0 4px 16px var(--color-accent-glow)',
                }}
              >
                <HiPlusCircle size={17} />
                {saving ? 'Creating...' : 'Create Room'}
              </button>
            </div>
          </form>
        </div>
      </div>
      <style>{`
        @keyframes scaleIn {
          from { opacity: 0; transform: scale(0.95) translateY(8px); }
          to { opacity: 1; transform: scale(1) translateY(0); }
        }
      `}</style>
    </>
  );
}
