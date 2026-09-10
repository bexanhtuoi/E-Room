import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { HiCheck, HiPencil, HiPlus, HiTrash, HiXMark } from 'react-icons/hi2';
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

function sameList(a, b) {
  return JSON.stringify(a || []) === JSON.stringify(b || []);
}

const emptyExp = { title: '', company: '', time: '', desc: '' };
const emptyEdu = { school: '', degree: '', time: '' };

export function ProfileInfoSection({ user, tierLabel, onSaved }) {
  const [name, setName] = useState(user?.full_name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [level, setLevel] = useState(user?.english_level || '');
  const [avatar, setAvatar] = useState(user?.avatar_url || null);
  const [headline, setHeadline] = useState(user?.headline || '');
  const [bio, setBio] = useState(user?.bio || '');
  const [location, setLocation] = useState(user?.location || '');
  const [website, setWebsite] = useState(user?.website || '');
  const [skills, setSkills] = useState(Array.isArray(user?.skills) ? user.skills : []);
  const [experience, setExperience] = useState(Array.isArray(user?.experience) ? user.experience : []);
  const [education, setEducation] = useState(Array.isArray(user?.education) ? user.education : []);
  const [editing, setEditing] = useState(null);
  const [skillDraft, setSkillDraft] = useState('');
  const [expDraft, setExpDraft] = useState(emptyExp);
  const [expEdit, setExpEdit] = useState(null);
  const [eduDraft, setEduDraft] = useState(emptyEdu);
  const [eduEdit, setEduEdit] = useState(null);
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
    || !sameList(skills, user?.skills)
    || !sameList(experience, user?.experience)
    || !sameList(education, user?.education);

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
      skills,
      experience,
      education,
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
    setSkills(Array.isArray(user?.skills) ? user.skills : []);
    setExperience(Array.isArray(user?.experience) ? user.experience : []);
    setEducation(Array.isArray(user?.education) ? user.education : []);
    setEditing(null);
    setExpEdit(null);
    setEduEdit(null);
  }

  function addSkill() {
    const skill = skillDraft.trim();
    if (!skill || skills.some((s) => s.toLowerCase() === skill.toLowerCase())) return;
    setSkills((list) => [...list, skill].slice(0, 20));
    setSkillDraft('');
  }

  function saveExp() {
    if (!expDraft.title.trim() && !expDraft.company.trim()) return;
    if (expEdit == null) {
      setExperience((list) => [...list, { ...expDraft }].slice(0, 10));
    } else {
      setExperience((list) => list.map((item, i) => (i === expEdit ? { ...expDraft } : item)));
    }
    setExpDraft(emptyExp);
    setExpEdit(null);
  }

  function saveEdu() {
    if (!eduDraft.school.trim() && !eduDraft.degree.trim()) return;
    if (eduEdit == null) {
      setEducation((list) => [...list, { ...eduDraft }].slice(0, 5));
    } else {
      setEducation((list) => list.map((item, i) => (i === eduEdit ? { ...eduDraft } : item)));
    }
    setEduDraft(emptyEdu);
    setEduEdit(null);
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

      <section className="portal-panel">
        <div className="portal-panel__head"><h2>Skills <span className="portal-count">{skills.length}</span></h2></div>
        {skills.length > 0 && (
          <div className="portal-topics" style={{ marginBottom: 12 }}>
            {skills.map((skill) => (
              <span key={skill} className="portal-topic">
                {skill}
                <button
                  type="button" aria-label={`Remove skill ${skill}`} title={`Remove ${skill}`}
                  onClick={() => setSkills((list) => list.filter((s) => s !== skill))}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, font: 'inherit', display: 'inline-flex', alignItems: 'center' }}
                >
                  <HiXMark size={10} />
                </button>
              </span>
            ))}
          </div>
        )}
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            className="er-input" value={skillDraft} placeholder="Add a skill and press Enter…"
            onChange={(e) => setSkillDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addSkill(); } }}
            aria-label="New skill"
          />
          <button type="button" className="er-btn er-btn--ghost" title="Add skill" aria-label="Add skill" onClick={addSkill} style={{ padding: '8px 12px', flexShrink: 0 }}>
            <HiPlus size={16} />
          </button>
        </div>
      </section>

      <section className="portal-panel">
        <div className="portal-panel__head"><h2>Experience <span className="portal-count">{experience.length}</span></h2></div>
        {experience.length > 0 && (
          <div className="portal-list" style={{ marginBottom: 12 }}>
            {experience.map((item, i) => (
              <div key={i} className="portal-row">
                <span className="portal-row__main">
                  <span className="portal-row__text">{item.title || 'Untitled'}{item.company ? ` · ${item.company}` : ''}</span>
                  {(item.time || item.desc) && <span className="portal-row__sub">{[item.time, item.desc].filter(Boolean).join(' — ')}</span>}
                </span>
                <button
                  type="button" className="portal-tool" title="Edit entry" aria-label={`Edit experience ${i + 1}`}
                  onClick={() => { setExpDraft({ ...emptyExp, ...item }); setExpEdit(i); }}
                >
                  <HiPencil size={14} />
                </button>
                <button
                  type="button" className="portal-tool is-danger" title="Delete entry" aria-label={`Delete experience ${i + 1}`}
                  onClick={() => setExperience((list) => list.filter((_, j) => j !== i))}
                >
                  <HiTrash size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
        <div style={{ display: 'grid', gap: 8 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <input className="er-input" value={expDraft.title} placeholder="Title" onChange={(e) => setExpDraft({ ...expDraft, title: e.target.value })} aria-label="Experience title" />
            <input className="er-input" value={expDraft.company} placeholder="Company" onChange={(e) => setExpDraft({ ...expDraft, company: e.target.value })} aria-label="Experience company" />
          </div>
          <input className="er-input" value={expDraft.time} placeholder="Time, e.g. 2023 – now" onChange={(e) => setExpDraft({ ...expDraft, time: e.target.value })} aria-label="Experience time" />
          <input className="er-input" value={expDraft.desc} placeholder="One line about it…" onChange={(e) => setExpDraft({ ...expDraft, desc: e.target.value })} aria-label="Experience description" />
          <div className="portal-actions">
            <button type="button" className="er-btn er-btn--ghost portal-mini-btn" onClick={saveExp}>
              <HiPlus size={14} /> {expEdit == null ? 'Add experience' : 'Update experience'}
            </button>
            {expEdit != null && (
              <button type="button" className="er-btn er-btn--ghost portal-mini-btn" onClick={() => { setExpDraft(emptyExp); setExpEdit(null); }}>
                Cancel
              </button>
            )}
          </div>
        </div>
      </section>

      <section className="portal-panel">
        <div className="portal-panel__head"><h2>Education <span className="portal-count">{education.length}</span></h2></div>
        {education.length > 0 && (
          <div className="portal-list" style={{ marginBottom: 12 }}>
            {education.map((item, i) => (
              <div key={i} className="portal-row">
                <span className="portal-row__main">
                  <span className="portal-row__text">{item.school || 'Untitled'}{item.degree ? ` · ${item.degree}` : ''}</span>
                  {item.time && <span className="portal-row__sub">{item.time}</span>}
                </span>
                <button
                  type="button" className="portal-tool" title="Edit entry" aria-label={`Edit education ${i + 1}`}
                  onClick={() => { setEduDraft({ ...emptyEdu, ...item }); setEduEdit(i); }}
                >
                  <HiPencil size={14} />
                </button>
                <button
                  type="button" className="portal-tool is-danger" title="Delete entry" aria-label={`Delete education ${i + 1}`}
                  onClick={() => setEducation((list) => list.filter((_, j) => j !== i))}
                >
                  <HiTrash size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
        <div style={{ display: 'grid', gap: 8 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <input className="er-input" value={eduDraft.school} placeholder="School" onChange={(e) => setEduDraft({ ...eduDraft, school: e.target.value })} aria-label="School" />
            <input className="er-input" value={eduDraft.degree} placeholder="Degree" onChange={(e) => setEduDraft({ ...eduDraft, degree: e.target.value })} aria-label="Degree" />
          </div>
          <input className="er-input" value={eduDraft.time} placeholder="Time, e.g. 2020 – 2024" onChange={(e) => setEduDraft({ ...eduDraft, time: e.target.value })} aria-label="Education time" />
          <div className="portal-actions">
            <button type="button" className="er-btn er-btn--ghost portal-mini-btn" onClick={saveEdu}>
              <HiPlus size={14} /> {eduEdit == null ? 'Add education' : 'Update education'}
            </button>
            {eduEdit != null && (
              <button type="button" className="er-btn er-btn--ghost portal-mini-btn" onClick={() => { setEduDraft(emptyEdu); setEduEdit(null); }}>
                Cancel
              </button>
            )}
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
