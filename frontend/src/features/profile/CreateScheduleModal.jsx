import { useState } from 'react';
import { HiPlus, HiXMark } from 'react-icons/hi2';
import { fetchJson } from '../../lib/api';
import { queryClient } from '../../lib/queryClient';
import { TopicPicker } from '../rooms/TopicPicker';

function toLocalInputValue(date) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function CreateScheduleModal({ onClose, onCreated }) {
  const [name, setName] = useState('');
  const [topics, setTopics] = useState([]);
  const [isPrivate, setIsPrivate] = useState(false);
  const [emails, setEmails] = useState([]);
  const [draft, setDraft] = useState('');
  const [when, setWhen] = useState(() => {
    const next = new Date(Date.now() + 24 * 3600 * 1000);
    next.setMinutes(0, 0, 0);
    return toLocalInputValue(next);
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  function addEmail() {
    const email = draft.trim().toLowerCase();
    if (!email || !email.includes('@') || emails.includes(email)) return;
    setEmails((list) => [...list, email]);
    setDraft('');
    setIsPrivate(true);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    setError('');
    try {
      const scheduled = when ? new Date(when) : null;
      const room = await fetchJson('/rooms/', {
        method: 'POST',
        body: JSON.stringify({
          name: name.trim(),
          topics,
          is_private: emails.length > 0 ? true : isPrivate,
          allowed_emails: emails,
          scheduled_at: scheduled && !Number.isNaN(scheduled.getTime()) ? scheduled.toISOString() : null,
        }),
      });
      queryClient.invalidateQueries({ queryKey: ['rooms', 'list'] });
      onCreated?.(room);
      onClose();
    } catch (err) {
      setError(err?.message || 'Could not schedule room.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="pf-modal" onClick={onClose}>
      <div className="pf-modal__box" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Schedule a room">
        <div className="pf-modal__head">
          <div>
            <h3>Schedule a room</h3>
            <p className="portal-muted">Pick a time, invite people, @ai reminds the room when it starts.</p>
          </div>
          <button type="button" className="pf-modal__close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 14 }}>
          <div>
            <label className="er-label" htmlFor="sched-name">Room name *</label>
            <input id="sched-name" className="er-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Sunday Speaking Club" autoFocus />
          </div>
          <div>
            <span className="er-label">Topics</span>
            <TopicPicker topics={topics} onChange={setTopics} />
          </div>
          <div>
            <label className="er-label" htmlFor="sched-when">Date & time</label>
            <input id="sched-when" className="er-input" type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} />
          </div>
          <div>
            <button
              type="button" onClick={() => setIsPrivate((v) => !v)} aria-pressed={isPrivate} className="portal-switch"
            >
              {isPrivate ? 'Private room' : 'Public room'}
              <span className={`portal-switch__track${isPrivate ? ' is-on' : ''}`}><span className="portal-switch__thumb" /></span>
            </button>
          </div>
          <div>
            <label className="er-label" htmlFor="sched-email">Invite by email {emails.length > 0 && `(${emails.length} — room becomes private)`}</label>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                id="sched-email" className="er-input" value={draft} placeholder="friend@example.com"
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addEmail(); } }}
              />
              <button
                type="button" className="er-btn er-btn--ghost" title="Invite email" aria-label="Invite email"
                onClick={addEmail} style={{ padding: '8px 12px', flexShrink: 0 }}
              >
                <HiPlus size={16} />
              </button>
            </div>
            {emails.length > 0 && (
              <div className="portal-topics" style={{ marginTop: 8 }}>
                {emails.map((email) => (
                  <span key={email} className="portal-topic">
                    {email}
                    <button
                      type="button" aria-label={`Remove ${email}`}
                      onClick={() => setEmails((list) => list.filter((x) => x !== email))}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, font: 'inherit', display: 'inline-flex', alignItems: 'center' }}
                    >
                      <HiXMark size={10} />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {error && <div className="er-alert er-alert--err">{error}</div>}
          <div style={{ display: 'flex', gap: 10 }}>
            <button type="button" className="er-btn er-btn--ghost" style={{ flex: 1, justifyContent: 'center' }} onClick={onClose}>Cancel</button>
            <button type="submit" className="er-btn" style={{ flex: 2, justifyContent: 'center' }} disabled={saving || !name.trim()}>
              {saving ? 'Scheduling…' : 'Schedule room →'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
