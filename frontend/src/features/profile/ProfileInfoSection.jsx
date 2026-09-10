import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { HiArrowRight, HiCheck, HiPencil, HiFlag, HiPlus, HiXMark } from 'react-icons/hi2';
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

function AddLine({ label, hint, onClick }) {
  return (
    <button type="button" className="pf-addline" aria-label={label} title={label} onClick={onClick}>
      <HiPencil size={13} /> {hint}
    </button>
  );
}

export function ProfileInfoSection({ user, tierLabel, onSaved, topRooms = [] }) {
  const [name, setName] = useState(user?.full_name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [level, setLevel] = useState(user?.english_level || '');
  const [avatar, setAvatar] = useState(user?.avatar_url || null);
  const [headline, setHeadline] = useState(user?.headline || '');
  const [career, setCareer] = useState(user?.career_field || '');
  const [location, setLocation] = useState(user?.location || '');
  const [website, setWebsite] = useState(user?.website || '');
  const [goal, setGoal] = useState(user?.learning_goal || '');
  const [interests, setInterests] = useState(Array.isArray(user?.interests) ? user.interests : []);
  const [interestDraft, setInterestDraft] = useState('');
  const [editing, setEditing] = useState(null);
  const [showAvatar, setShowAvatar] = useState(false);
  const [notice, setNotice] = useState(null);

  const sameList = (a, b) => JSON.stringify(a || []) === JSON.stringify(b || []);
  const dirty = name.trim() !== (user?.full_name || '')
    || email.trim() !== (user?.email || '')
    || (level || null) !== (user?.english_level || null)
    || (avatar || null) !== (user?.avatar_url || null)
    || headline.trim() !== (user?.headline || '')
    || career.trim() !== (user?.career_field || '')
    || location.trim() !== (user?.location || '')
    || website.trim() !== (user?.website || '')
    || goal.trim() !== (user?.learning_goal || '')
    || !sameList(interests, user?.interests);

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
      career_field: career.trim() || null,
      location: location.trim() || null,
      website: website.trim() || null,
      learning_goal: goal.trim() || null,
      interests,
    });
  }

  function handleReset() {
    setName(user?.full_name || '');
    setEmail(user?.email || '');
    setLevel(user?.english_level || '');
    setAvatar(user?.avatar_url || null);
    setHeadline(user?.headline || '');
    setCareer(user?.career_field || '');
    setLocation(user?.location || '');
    setWebsite(user?.website || '');
    setGoal(user?.learning_goal || '');
    setInterests(Array.isArray(user?.interests) ? user.interests : []);
    setEditing(null);
  }

  function addInterest() {
    const interest = interestDraft.trim();
    if (!interest || interests.some((s) => s.toLowerCase() === interest.toLowerCase())) return;
    setInterests((list) => [...list, interest].slice(0, 20));
    setInterestDraft('');
  }

  const shownWork = [headline || user?.headline, career || user?.career_field].filter(Boolean).join(' · ');
  const shownGoal = goal || user?.learning_goal || '';

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
          <div className="pf-resume__id pf-resume__id--cols">
            <div className="pf-resume__line pf-resume__line--span">
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
              {editing === 'work' ? (
                <span className="pf-field__edit">
                  <input className="er-input" value={headline} autoFocus placeholder="Job title" onChange={(e) => setHeadline(e.target.value)} aria-label="Job title" />
                  <input className="er-input" value={career} placeholder="Career field" onChange={(e) => setCareer(e.target.value)} aria-label="Career field" />
                  <Done label="work" onClick={() => setEditing(null)} />
                </span>
              ) : shownWork ? (
                <>
                  <strong>{shownWork}</strong>
                  <Pencil label="work" onClick={() => setEditing('work')} />
                </>
              ) : (
                <AddLine label="Edit work" hint="Add job title & field" onClick={() => setEditing('work')} />
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
                  <span className="portal-muted">Level {level || user?.english_level || 'not set'}</span>
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
              ) : (location || user?.location || website || user?.website) ? (
                <>
                  <span className="portal-muted">
                    {[location || user?.location, website || user?.website].filter(Boolean).join(' · ')}
                  </span>
                  <Pencil label="contact" onClick={() => setEditing('contact')} />
                </>
              ) : (
                <AddLine label="Edit contact" hint="Add location & website" onClick={() => setEditing('contact')} />
              )}
            </div>
            <div className="portal-muted pf-resume__foot pf-resume__line--span">
              Member since {user?.created_at ? formatDateTime(user.created_at) : '—'} · #{user?.id}
            </div>
          </div>
        </div>

        <div className="pf-divider" />

        <div className="pf-section">
          <div className="pf-section__head">
            <h2>Interested in</h2>
            {editing !== 'interests' && <Pencil label="interests" onClick={() => setEditing('interests')} />}
          </div>
          {editing === 'interests' ? (
            <div style={{ display: 'grid', gap: 8 }}>
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  className="er-input" value={interestDraft} autoFocus placeholder="Add a topic and press Enter…"
                  onChange={(e) => setInterestDraft(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addInterest(); } }}
                  aria-label="New interest"
                />
                <button
                  type="button" className="er-btn er-btn--ghost" title="Add interest" aria-label="Add interest"
                  onClick={addInterest} style={{ padding: '8px 12px', flexShrink: 0 }}
                >
                  <HiPlus size={16} />
                </button>
              </div>
              {interests.length > 0 && (
                <div className="portal-topics">
                  {interests.map((interest) => (
                    <span key={interest} className="portal-topic">
                      {interest}
                      <button
                        type="button" aria-label={`Remove interest ${interest}`}
                        onClick={() => setInterests((list) => list.filter((s) => s !== interest))}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, font: 'inherit', display: 'inline-flex', alignItems: 'center' }}
                      >
                        <HiXMark size={10} />
                      </button>
                    </span>
                  ))}
                </div>
              )}
              <div className="portal-actions"><Done label="interests" onClick={() => setEditing(null)} /></div>
            </div>
          ) : interests.length > 0 ? (
            <div className="portal-topics">
              {interests.map((interest) => <span key={interest} className="portal-topic">{interest}</span>)}
            </div>
          ) : (
            <AddLine label="Edit interests" hint="Pick topics you love talking about" onClick={() => setEditing('interests')} />
          )}
        </div>

        <div className="pf-divider" />

        <div className="pf-section">
          <div className="pf-section__head">
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
          ) : shownGoal ? (
            <p className="pf-goal__text">{shownGoal}</p>
          ) : (
            <AddLine label="Edit learning goal" hint="Set one clear goal to stay honest" onClick={() => setEditing('goal')} />
          )}
        </div>

        {topRooms.length > 0 && (
          <>
            <div className="pf-divider" />
            <div className="pf-section">
              <div className="pf-section__head">
                <h2>My top rooms</h2>
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
            </div>
          </>
        )}

        <div className="pf-divider" />

        <div className="pf-section">
          <div className="pf-section__head"><h2>Plan</h2></div>
          <div className="pf-plan">
            <div>
              <strong className="pf-plan__tier">{tierLabel}</strong>
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
