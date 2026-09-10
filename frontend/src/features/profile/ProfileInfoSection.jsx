import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { HiArrowRight, HiCheck, HiPencil, HiFlag } from 'react-icons/hi2';
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

function Done({ label, onClick }) {
  return (
    <button type="button" className="portal-tool" title="Done" aria-label={`Done editing ${label}`} onClick={onClick}>
      <HiCheck size={15} />
    </button>
  );
}

export function ProfileInfoSection({ user, tierLabel, onSaved, topRooms = [] }) {
  const [name, setName] = useState(user?.full_name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [level, setLevel] = useState(user?.english_level || '');
  const [avatar, setAvatar] = useState(user?.avatar_url || null);
  const [headline, setHeadline] = useState(user?.headline || '');
  const [bio, setBio] = useState(user?.bio || '');
  const [location, setLocation] = useState(user?.location || '');
  const [website, setWebsite] = useState(user?.website || '');
  const [goal, setGoal] = useState(user?.learning_goal || '');
  const [editing, setEditing] = useState(null);
  const [showAvatar, setShowAvatar] = useState(false);
  const [notice, setNotice] = useState(null);

  const dirty = name.trim() !== (user?.full_name || '')
    || email.trim() !== (user?.email || '')
    || (level || null) !== (user?.english_level || null)
    || (avatar || null) !== (user?.avatar_url || null)
    || headline.trim() !== (user?.headline || '')
    || bio.trim() !== (user?.bio || '')
    || location.trim() !== (user?.location || '')
    || website.trim() !== (user?.website || '')
    || goal.trim() !== (user?.learning_goal || '');

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
      headline: headline.trim() || null,
      bio: bio.trim() || null,
      location: location.trim() || null,
      website: website.trim() || null,
      learning_goal: goal.trim() || null,
    });
  }

  function handleReset() {
    setName(user?.full_name || '');
    setEmail(user?.email || '');
    setLevel(user?.english_level || '');
    setAvatar(user?.avatar_url || null);
    setHeadline(user?.headline || '');
    setBio(user?.bio || '');
    setLocation(user?.location || '');
    setWebsite(user?.website || '');
    setGoal(user?.learning_goal || '');
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
                  <Done label="name" onClick={() => setEditing(null)} />
                </span>
              ) : (
                <>
                  <h1>{name || user?.full_name || 'E-Room learner'}</h1>
                  <Pencil label="name" onClick={() => setEditing('name')} />
                </>
              )}
            </div>
            <div className="pf-resume__line">
              {editing === 'headline' ? (
                <span className="pf-field__edit">
                  <input className="er-input" value={headline} autoFocus placeholder="e.g. Frontend Developer" onChange={(e) => setHeadline(e.target.value)} aria-label="Headline" />
                  <Done label="headline" onClick={() => setEditing(null)} />
                </span>
              ) : (
                <>
                  <strong>{headline || user?.headline || 'Add your headline'}</strong>
                  <Pencil label="headline" onClick={() => setEditing('headline')} />
                </>
              )}
            </div>
            <div className="pf-resume__line">
              {editing === 'email' ? (
                <span className="pf-field__edit">
                  <input className="er-input" type="email" value={email} autoFocus onChange={(e) => setEmail(e.target.value)} aria-label="Email" />
                  <Done label="email" onClick={() => setEditing(null)} />
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
                  <Done label="level" onClick={() => setEditing(null)} />
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
            <div className="pf-resume__line">
              {editing === 'contact' ? (
                <span className="pf-field__edit">
                  <input className="er-input" value={location} autoFocus placeholder="City, Country" onChange={(e) => setLocation(e.target.value)} aria-label="Location" />
                  <input className="er-input" value={website} placeholder="https://…" onChange={(e) => setWebsite(e.target.value)} aria-label="Website" />
                  <Done label="contact" onClick={() => setEditing(null)} />
                </span>
              ) : (
                <>
                  <span className="portal-muted">
                    {[location || user?.location, website || user?.website].filter(Boolean).join(' · ') || 'Add location & website'}
                  </span>
                  <Pencil label="contact" onClick={() => setEditing('contact')} />
                </>
              )}
            </div>
            <div className="portal-muted pf-resume__foot">
              Member since {user?.created_at ? formatDateTime(user.created_at) : '—'} · #{user?.id}
            </div>
          </div>
        </div>
      </section>

      <section className="portal-panel">
        <div className="portal-panel__head">
          <h2>Overview</h2>
          {editing !== 'bio' && <Pencil label="bio" onClick={() => setEditing('bio')} />}
        </div>
        {editing === 'bio' ? (
          <div style={{ display: 'grid', gap: 8 }}>
            <textarea className="er-textarea" rows={4} value={bio} autoFocus placeholder="A few lines about you…" onChange={(e) => setBio(e.target.value)} aria-label="Bio" />
            <div className="portal-actions"><Done label="bio" onClick={() => setEditing(null)} /></div>
          </div>
        ) : (
          <p className="portal-muted" style={{ margin: 0 }}>{bio || user?.bio || 'Tell people who you are and what you want to practice.'}</p>
        )}
      </section>

      <section className="portal-panel pf-goal">
        <div className="portal-panel__head">
          <h2>My learning goal</h2>
          {editing !== 'goal' && <Pencil label="learning goal" onClick={() => setEditing('goal')} />}
        </div>
        {editing === 'goal' ? (
          <div style={{ display: 'grid', gap: 8 }}>
            <textarea
              className="er-textarea" rows={2} value={goal} autoFocus
              placeholder="e.g. Speak 15 minutes every evening for the next 30 days."
              onChange={(e) => setGoal(e.target.value)} aria-label="Learning goal"
            />
            <div className="portal-actions"><Done label="learning goal" onClick={() => setEditing(null)} /></div>
          </div>
        ) : (
          <p className={goal || user?.learning_goal ? 'pf-goal__text' : 'portal-muted'} style={{ margin: 0 }}>
            {goal || user?.learning_goal || 'Set one clear goal — it shows up here to keep you honest.'}
          </p>
        )}
        {(goal || user?.learning_goal) && (
          <div className="portal-muted" style={{ marginTop: 8, fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
            <HiFlag size={13} /> Pinned to the top of your learning week.
          </div>
        )}
      </section>

      {topRooms.length > 0 && (
        <section className="portal-panel">
          <div className="portal-panel__head">
            <h2>Top rooms</h2>
            <Link className="portal-linkbtn" style={{ textDecoration: 'none' }} to="/my-rooms">
              All rooms <HiArrowRight size={13} />
            </Link>
          </div>
          <div className="portal-list">
            {topRooms.map(({ room, lines, live }) => (
              <div key={room.id} className="portal-row">
                <span className={`portal-room__tile${live ? ' is-live' : ''}`} style={{ width: 36, height: 36, fontSize: 15 }}>
                  {(room.name || '?').trim().charAt(0).toUpperCase()}
                </span>
                <span className="portal-row__main">
                  <span className="portal-row__text">{room.name}</span>
                  <span className="portal-row__sub">
                    {live ? 'Live now' : room.status === 'idle' ? 'Open' : 'Ended'} · {lines} your lines
                  </span>
                </span>
                <Link className="er-btn portal-mini-btn" style={{ textDecoration: 'none' }} to={`/rooms/${room.id}`}>
                  {live ? 'Join' : 'Open'}
                </Link>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="portal-panel">
        <div className="portal-panel__head"><h2>Plan</h2><span className="portal-flag is-solid">{tierLabel}</span></div>
        <div className="portal-block">
          <div className="portal-resume">
            <div>
              <strong>You are on {tierLabel}</strong>
              <span className="portal-muted">
                {tierLabel === 'Free'
                  ? 'Create public rooms, join any open room, meet the community.'
                  : 'Thanks for supporting E-Room — enjoy the extra rooms and voice.'}
              </span>
            </div>
            <Link className="er-btn portal-mini-btn" style={{ textDecoration: 'none' }} to="/pricing">
              {tierLabel === 'Free' ? 'Upgrade' : 'Manage plan'}
            </Link>
          </div>
        </div>
      </section>

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
