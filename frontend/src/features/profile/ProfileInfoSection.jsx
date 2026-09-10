import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { HiCheck, HiPencil, HiXMark } from 'react-icons/hi2';
import { fetchJson } from '../../lib/api';
import { queryClient } from '../../lib/queryClient';
import { formatDateTime } from '../../lib/formatters';
import { Face, avatarFaceProps } from '../../components/common/Faces';
import { AvatarPopup } from './AvatarPopup';

const LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];

function EditableRow({ label, value, editing, onEdit, onDone, children }) {
  return (
    <div className="pf-field">
      <span className="er-label">{label}</span>
      {editing ? (
        <span className="pf-field__edit">
          {children}
          <button type="button" className="portal-tool" title="Done" aria-label={`Done editing ${label}`} onClick={onDone}>
            <HiCheck size={15} />
          </button>
        </span>
      ) : (
        <span className="pf-field__view">
          <span className="pf-field__value">{value || <span className="portal-muted">Not set</span>}</span>
          <button type="button" className="portal-tool" title={`Edit ${label}`} aria-label={`Edit ${label}`} onClick={onEdit}>
            <HiPencil size={14} />
          </button>
        </span>
      )}
    </div>
  );
}

export function ProfileInfoSection({ user, tierLabel, onSaved, onSignOut }) {
  const [name, setName] = useState(user?.full_name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [level, setLevel] = useState(user?.english_level || '');
  const [avatar, setAvatar] = useState(user?.avatar_url || null);
  const [editing, setEditing] = useState(null);
  const [showAvatar, setShowAvatar] = useState(false);
  const [notice, setNotice] = useState(null);

  const dirty = name.trim() !== (user?.full_name || '')
    || email.trim() !== (user?.email || '')
    || (level || null) !== (user?.english_level || null)
    || (avatar || null) !== (user?.avatar_url || null);

  const saveMutation = useMutation({
    mutationFn: (data) => fetchJson(`/users/${user.id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['room-host'] });
      onSaved?.(updated);
      setEditing(null);
      setNotice({ ok: true, text: 'Profile saved.' });
      setTimeout(() => setNotice(null), 3000);
    },
    onError: (err) => setNotice({ ok: false, text: err?.message || 'Could not save profile.' }),
  });

  function handleSave() {
    saveMutation.mutate({
      full_name: name.trim(),
      email: email.trim(),
      english_level: level || null,
      avatar_url: avatar || null,
    });
  }

  function handleReset() {
    setName(user?.full_name || '');
    setEmail(user?.email || '');
    setLevel(user?.english_level || '');
    setAvatar(user?.avatar_url || null);
    setEditing(null);
  }

  return (
    <div className="portal-stack pf-center pf-wide">
      <section className="portal-panel">
        <div className="pf-profile__head">
          <button
            type="button" className="pf-avatarbtn" title="Change avatar" aria-label="Change avatar"
            onClick={() => setShowAvatar(true)}
          >
            <Face {...avatarFaceProps(avatar, name || user?.email)} size={96} />
            <span className="pf-avatarbtn__edit" aria-hidden="true"><HiPencil size={14} /></span>
          </button>
          <div className="pf-profile__id">
            <div className="pf-profile__name">
              <h2>{name || user?.full_name || 'E-Room learner'}</h2>
              <span className="portal-flag is-solid">{tierLabel} plan</span>
            </div>
            <div className="portal-muted">{email || user?.email}</div>
            <div className="portal-muted">
              Level {level || user?.english_level || 'not set'} · Member since {user?.created_at ? formatDateTime(user.created_at) : '—'}
            </div>
          </div>
        </div>
      </section>

      <section className="portal-panel">
        <div className="portal-panel__head"><h2>Details</h2></div>
        {notice && <div className={`er-alert ${notice.ok ? 'er-alert--ok' : 'er-alert--err'}`}>{notice.text}</div>}
        <EditableRow label="Full name" value={name || user?.full_name} editing={editing === 'name'} onEdit={() => setEditing('name')} onDone={() => setEditing(null)}>
          <input className="er-input" value={name} autoFocus onChange={(e) => setName(e.target.value)} aria-label="Full name" />
        </EditableRow>
        <EditableRow label="Email" value={email || user?.email} editing={editing === 'email'} onEdit={() => setEditing('email')} onDone={() => setEditing(null)}>
          <input className="er-input" type="email" value={email} autoFocus onChange={(e) => setEmail(e.target.value)} aria-label="Email" />
        </EditableRow>
        <EditableRow label="English level" value={level || user?.english_level} editing={editing === 'level'} onEdit={() => setEditing('level')} onDone={() => setEditing(null)}>
          <select className="er-input" value={level} autoFocus onChange={(e) => setLevel(e.target.value)} aria-label="English level">
            <option value="">Not set yet</option>
            {LEVELS.map((l) => <option key={l} value={l}>{l}</option>)}
          </select>
        </EditableRow>
        <div className="pf-field">
          <span className="er-label">User ID</span>
          <span className="pf-field__view"><span className="pf-field__value portal-muted">#{user?.id}</span></span>
        </div>
      </section>

      <div className="pf-savebar">
        <button className="er-btn er-btn--ghost pf-savebar__btn" disabled={!dirty || saveMutation.isPending} onClick={handleReset}>
          <HiXMark size={15} /> Reset
        </button>
        <button className="er-btn pf-savebar__btn" disabled={saveMutation.isPending || !name.trim() || !email.trim() || !dirty} onClick={handleSave}>
          <HiCheck size={15} /> {saveMutation.isPending ? 'Saving…' : 'Save changes'}
        </button>
      </div>

      {showAvatar && (
        <AvatarPopup
          name={name || user?.email}
          value={avatar}
          onPick={(picked) => { setAvatar(picked); }}
          onClose={() => setShowAvatar(false)}
        />
      )}
    </div>
  );
}
