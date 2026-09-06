import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { HiArrowRightOnRectangle } from 'react-icons/hi2';
import { fetchJson } from '../../lib/api';
import { AvatarPicker } from './AvatarPicker';

const LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];

function Switch({ on, onClick, label }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={on} className="portal-switch">
      {label}
      <span className={`portal-switch__track${on ? ' is-on' : ''}`}><span className="portal-switch__thumb" /></span>
    </button>
  );
}

export function SettingsSection({ user, onSaved, onSignOut }) {
  const [name, setName] = useState(user?.full_name || '');
  const [level, setLevel] = useState(user?.english_level || '');
  const [avatar, setAvatar] = useState(user?.avatar_url || null);
  const [match, setMatch] = useState(true);
  const [reminders, setReminders] = useState(true);
  const [showProfile, setShowProfile] = useState(true);
  const [notice, setNotice] = useState(null);

  const saveMutation = useMutation({
    mutationFn: (data) => fetchJson(`/users/${user.id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    onSuccess: (updated) => {
      onSaved?.(updated);
      setNotice({ ok: true, text: 'Profile updated.' });
      setTimeout(() => setNotice(null), 3000);
    },
    onError: (err) => setNotice({ ok: false, text: err?.message || 'Failed to update profile.' }),
  });

  const dirty = name.trim() !== (user?.full_name || '') || (level || null) !== (user?.english_level || null) || (avatar || null) !== (user?.avatar_url || null);

  function handleSave() {
    saveMutation.mutate({
      full_name: name.trim(),
      english_level: level || null,
      avatar_url: avatar || null,
    });
  }

  function handleReset() {
    setName(user?.full_name || '');
    setLevel(user?.english_level || '');
    setAvatar(user?.avatar_url || null);
  }

  return (
    <div className="portal-stack">
      <section className="portal-panel">
        <div className="portal-panel__head"><h2>Profile settings</h2></div>
        {notice && <div className={`er-alert ${notice.ok ? 'er-alert--ok' : 'er-alert--err'}`}>{notice.text}</div>}
        <div className="er-grid er-grid--2 portal-formgrid">
          <div>
            <label className="er-label" htmlFor="portal-name">Full name</label>
            <input id="portal-name" className="er-input" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label className="er-label" htmlFor="portal-level">English level</label>
            <select id="portal-level" className="er-input" value={level} onChange={(e) => setLevel(e.target.value)}>
              <option value="">Not set yet</option>
              {LEVELS.map((l) => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label className="er-label">Email</label>
          <input className="er-input" value={user?.email || ''} disabled />
        </div>
        <div style={{ marginTop: 18 }}>
          <AvatarPicker value={avatar} name={name || user?.email} onPick={setAvatar} />
        </div>
        <div className="portal-actions">
          <button className="er-btn" disabled={saveMutation.isPending || !name.trim() || !dirty} onClick={handleSave}>
            {saveMutation.isPending ? 'Saving…' : 'Save changes'}
          </button>
          <button className="er-btn er-btn--ghost" disabled={!dirty} onClick={handleReset}>Reset</button>
        </div>
      </section>

      <section className="portal-panel">
        <div className="portal-panel__head"><h2>Preferences</h2></div>
        <div className="portal-switchlist">
          <Switch on={match} onClick={() => setMatch((v) => !v)} label="Room match notifications" />
          <Switch on={reminders} onClick={() => setReminders((v) => !v)} label="Session reminders" />
          <Switch on={showProfile} onClick={() => setShowProfile((v) => !v)} label="Show profile in rooms" />
        </div>
        <p className="portal-muted">Notification and privacy switches are stored on this device for now.</p>
        <div className="portal-actions">
          <button className="er-btn er-btn--ghost" onClick={onSignOut}>
            <HiArrowRightOnRectangle size={15} /> Sign out
          </button>
        </div>
      </section>
    </div>
  );
}
