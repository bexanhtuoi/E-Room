import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { HiCalendarDays, HiChatBubbleLeftRight, HiCheck, HiFire, HiPencil, HiUserGroup } from 'react-icons/hi2';
import { fetchJson } from '../../lib/api';
import { queryClient } from '../../lib/queryClient';
import { formatDateTime } from '../../lib/formatters';
import { Face, avatarFaceProps } from '../../components/common/Faces';
import { AvatarPopup } from './AvatarPopup';

const LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];

function Pencil({ label, onClick }) {
  return (
    <button type="button" className="portal-tool" title={`Edit ${label}`} aria-label={`Edit ${label}`} onClick={onClick}>
      <HiPencil size={14} />
    </button>
  );
}

export function ProfileInfoSection({ user, tierLabel, onSaved, stats, hostedCount = 0, sessionsCount = 0 }) {
  const snapshot = [
    { icon: HiUserGroup, value: hostedCount, label: 'Rooms hosted' },
    { icon: HiCalendarDays, value: sessionsCount, label: 'Sessions done' },
    { icon: HiChatBubbleLeftRight, value: stats?.messages_total ?? 0, label: 'Messages' },
    { icon: HiFire, value: stats?.streak_days ?? 0, label: 'Day streak' },
  ];

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
      <section className="portal-panel pf-resume-card">
        <div className="pf-resume__head">
          <button
            type="button" className="pf-avatarbtn" title="Change avatar" aria-label="Change avatar"
            onClick={() => setShowAvatar(true)}
          >
            <Face {...avatarFaceProps(avatar, name || user?.email)} size={104} />
            <span className="pf-avatarbtn__edit" aria-hidden="true"><HiPencil size={14} /></span>
          </button>
          <div className="pf-resume__id">
            <div className="pf-resume__line">
              {editing === 'name' ? (
                <span className="pf-field__edit">
                  <input className="er-input" value={name} autoFocus onChange={(e) => setName(e.target.value)} aria-label="Full name" />
                  <button type="button" className="portal-tool" title="Done" aria-label="Done editing name" onClick={() => setEditing(null)}>
                    <HiCheck size={15} />
                  </button>
                </span>
              ) : (
                <>
                  <h1>{name || user?.full_name || 'E-Room learner'}</h1>
                  <Pencil label="name" onClick={() => setEditing('name')} />
                </>
              )}
            </div>
            <div className="pf-resume__line">
              {editing === 'email' ? (
                <span className="pf-field__edit">
                  <input className="er-input" type="email" value={email} autoFocus onChange={(e) => setEmail(e.target.value)} aria-label="Email" />
                  <button type="button" className="portal-tool" title="Done" aria-label="Done editing email" onClick={() => setEditing(null)}>
                    <HiCheck size={15} />
                  </button>
                </span>
              ) : (
                <>
                  <span className="portal-muted">{email || user?.email}</span>
                  <Pencil label="email" onClick={() => setEditing('email')} />
                </>
              )}
            </div>
            <div className="pf-resume__line">
              {editing === 'level' ? (
                <span className="pf-field__edit">
                  <select className="er-input" value={level} autoFocus onChange={(e) => setLevel(e.target.value)} aria-label="English level">
                    <option value="">Not set yet</option>
                    {LEVELS.map((l) => <option key={l} value={l}>{l}</option>)}
                  </select>
                  <button type="button" className="portal-tool" title="Done" aria-label="Done editing level" onClick={() => setEditing(null)}>
                    <HiCheck size={15} />
                  </button>
                </span>
              ) : (
                <>
                  <span>
                    <span className="portal-flag is-solid">{tierLabel} plan</span>
                    {' '}
                    <span className="portal-muted">Level {level || user?.english_level || 'not set'}</span>
                  </span>
                  <Pencil label="English level" onClick={() => setEditing('level')} />
                </>
              )}
            </div>
            <div className="portal-muted pf-resume__foot">
              Member since {user?.created_at ? formatDateTime(user.created_at) : '—'} · #{user?.id}
            </div>
          </div>
        </div>
      </section>

      <div className="pf-kpis pf-kpis--4">
        {snapshot.map((k) => (
          <div key={k.label} className="pf-kpi">
            <span className="pf-kpi__tile"><k.icon size={20} /></span>
            <span className="pf-kpi__body">
              <span className="pf-kpi__value">{k.value}</span>
              <span className="pf-kpi__label">{k.label}</span>
            </span>
          </div>
        ))}
      </div>

      <div className="pf-savebar">
        {notice && <div className={`er-alert ${notice.ok ? 'er-alert--ok' : 'er-alert--err'}`}>{notice.text}</div>}
        <button className="er-btn er-btn--ghost pf-savebar__btn" disabled={!dirty || saveMutation.isPending} onClick={handleReset}>
          Reset
        </button>
        <button className="er-btn pf-savebar__btn" disabled={saveMutation.isPending || !name.trim() || !email.trim() || !dirty} onClick={handleSave}>
          {saveMutation.isPending ? 'Saving…' : 'Save changes'}
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
