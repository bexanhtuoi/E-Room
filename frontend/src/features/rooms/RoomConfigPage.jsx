import { useState } from 'react';
import { Link, Navigate, useParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { HiArrowLeft, HiCheck, HiPlus, HiTrash, HiXMark } from 'react-icons/hi2';
import { useAuth } from '../../app/AuthContext';
import { API_BASE_URL, fetchJson } from '../../lib/api';
import { queryClient } from '../../lib/queryClient';
import { TopicPicker } from './TopicPicker';
import { SeatSlider } from './SeatSlider';
import '../../styles/ProfilePage.css';

function Card({ title, desc, children }) {
  return (
    <section className="portal-panel">
      <div className="portal-panel__head"><h2>{title}</h2></div>
      {desc && <p className="portal-muted" style={{ margin: '0 0 12px' }}>{desc}</p>}
      {children}
    </section>
  );
}

function Switch({ on, onClick, label }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={on} className="portal-switch">
      {label}
      <span className={`portal-switch__track${on ? ' is-on' : ''}`}><span className="portal-switch__thumb" /></span>
    </button>
  );
}

function patchRoom(roomId, data) {
  return fetchJson(`/rooms/${roomId}`, { method: 'PATCH', body: JSON.stringify(data) });
}

function BasicsCard({ room }) {
  const [name, setName] = useState(room.name || '');
  const [description, setDescription] = useState(room.description || '');
  const [topics, setTopics] = useState(Array.isArray(room.topics) ? room.topics : []);
  const [seats, setSeats] = useState(room.max_participants || 4);
  const [heartbeat, setHeartbeat] = useState(room.enable_heartbeat !== false);
  const [transcript, setTranscript] = useState(room.enable_transcript !== false);
  const [agent, setAgent] = useState(room.enable_agent !== false);
  const [notice, setNotice] = useState(null);

  const saveMutation = useMutation({
    mutationFn: () => patchRoom(room.id, {
      name: name.trim(), description: description.trim() || null, topics,
      max_participants: seats, enable_heartbeat: heartbeat,
      enable_transcript: transcript, enable_agent: agent,
    }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['rooms', 'list'] });
      queryClient.invalidateQueries({ queryKey: ['room', room.id] });
      setNotice({ ok: true, text: `Saved. ${updated.name}` });
      setTimeout(() => setNotice(null), 3000);
    },
    onError: (err) => setNotice({ ok: false, text: err?.message || 'Could not save.' }),
  });

  return (
    <Card title="Basics" desc="Name, topics and room behaviour.">
      {notice && <div className={`er-alert ${notice.ok ? 'er-alert--ok' : 'er-alert--err'}`}>{notice.text}</div>}
      <div style={{ display: 'grid', gap: 12 }}>
        <div>
          <label className="er-label" htmlFor="cfg-name">Room name</label>
          <input id="cfg-name" className="er-input" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label className="er-label" htmlFor="cfg-desc">Description</label>
          <textarea id="cfg-desc" className="er-textarea" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div>
          <span className="er-label">Topics</span>
          <TopicPicker topics={topics} onChange={setTopics} />
        </div>
        <SeatSlider value={seats} onChange={setSeats} id="cfg-seats" />
        <div className="portal-switchlist">
          <Switch on={heartbeat} onClick={() => setHeartbeat((v) => !v)} label="Heartbeat (auto-close empty rooms)" />
          <Switch on={transcript} onClick={() => setTranscript((v) => !v)} label="Live transcript" />
          <Switch on={agent} onClick={() => setAgent((v) => !v)} label="AI companion (@ai)" />
        </div>
        <div className="portal-actions">
          <button className="er-btn" disabled={saveMutation.isPending || !name.trim()} onClick={() => saveMutation.mutate()}>
            {saveMutation.isPending ? 'Saving…' : 'Save basics'}
          </button>
        </div>
      </div>
    </Card>
  );
}

function AccessCard({ room }) {
  const [isPrivate, setIsPrivate] = useState(Boolean(room.is_private));
  const [emails, setEmails] = useState(Array.isArray(room.allowed_emails) ? room.allowed_emails : []);
  const [draft, setDraft] = useState('');
  const [notice, setNotice] = useState(null);

  const saveMutation = useMutation({
    mutationFn: () => patchRoom(room.id, { is_private: isPrivate, allowed_emails: emails }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['rooms', 'list'] });
      queryClient.setQueryData(['room', String(room.id)], updated);
      setNotice({ ok: true, text: isPrivate ? 'Room is private now.' : 'Room is public now.' });
      setTimeout(() => setNotice(null), 3000);
    },
    onError: (err) => setNotice({ ok: false, text: err?.message || 'Could not save.' }),
  });

  function addEmail() {
    const email = draft.trim().toLowerCase();
    if (!email || !email.includes('@') || emails.includes(email)) return;
    setEmails((list) => [...list, email]);
    setDraft('');
  }

  return (
    <Card title="Access" desc="Public rooms appear on /rooms and home. Private rooms are invisible to everyone except you and the emails below.">
      {notice && <div className={`er-alert ${notice.ok ? 'er-alert--ok' : 'er-alert--err'}`}>{notice.text}</div>}
      <div className="portal-switchlist">
        <Switch on={!isPrivate} onClick={() => setIsPrivate((v) => !v)} label={isPrivate ? 'Private room' : 'Public room'} />
      </div>
      {isPrivate && (
        <div style={{ marginTop: 12 }}>
          <label className="er-label" htmlFor="cfg-email">Allowed emails ({emails.length})</label>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              id="cfg-email" className="er-input" value={draft} placeholder="friend@example.com"
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addEmail(); } }}
            />
            <button type="button" className="er-btn er-btn--ghost" onClick={addEmail}><HiPlus size={14} /> Add</button>
          </div>
          {emails.length > 0 && (
            <div className="portal-topics" style={{ marginTop: 8 }}>
              {emails.map((email) => (
                <span key={email} className="portal-topic">
                  {email}
                  <button
                    type="button" aria-label={`Remove ${email}`} title={`Remove ${email}`}
                    onClick={() => setEmails((list) => list.filter((x) => x !== email))}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '0 0 0 6px', font: 'inherit' }}
                  >
                    <HiXMark size={12} />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      )}
      <div className="portal-actions">
        <button className="er-btn" disabled={saveMutation.isPending} onClick={() => saveMutation.mutate()}>
          {saveMutation.isPending ? 'Saving…' : 'Save access'}
        </button>
      </div>
    </Card>
  );
}

function PromptCard({ room }) {
  const [prompt, setPrompt] = useState(room.system_prompt || '');
  const [notice, setNotice] = useState(null);

  const saveMutation = useMutation({
    mutationFn: () => patchRoom(room.id, { system_prompt: prompt.trim() || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['room', room.id] });
      setNotice({ ok: true, text: 'AI prompt saved.' });
      setTimeout(() => setNotice(null), 3000);
    },
    onError: (err) => setNotice({ ok: false, text: err?.message || 'Could not save.' }),
  });

  return (
    <Card title="AI prompt" desc="Extra instructions for @ai in this room. Empty means default behaviour.">
      {notice && <div className={`er-alert ${notice.ok ? 'er-alert--ok' : 'er-alert--err'}`}>{notice.text}</div>}
      <textarea
        className="er-textarea" rows={4} value={prompt}
        placeholder="e.g. Correct my grammar gently after each answer. Explain new words with examples."
        onChange={(e) => setPrompt(e.target.value)}
      />
      <div className="portal-actions">
        <button className="er-btn" disabled={saveMutation.isPending} onClick={() => saveMutation.mutate()}>
          {saveMutation.isPending ? 'Saving…' : 'Save prompt'}
        </button>
      </div>
    </Card>
  );
}

function SkillsCard({ room }) {
  const skillsQuery = useQuery({
    queryKey: ['rooms', room.id, 'skills'],
    queryFn: () => fetchJson(`/rooms/${room.id}/skills`),
  });
  const skills = Array.isArray(skillsQuery.data) ? skillsQuery.data : [];
  const [name, setName] = useState('');
  const [prompt, setPrompt] = useState('');
  const [notice, setNotice] = useState(null);

  function refresh() {
    queryClient.invalidateQueries({ queryKey: ['rooms', room.id, 'skills'] });
  }

  const addMutation = useMutation({
    mutationFn: () => fetchJson(`/rooms/${room.id}/skills`, { method: 'POST', body: JSON.stringify({ name: name.trim(), prompt: prompt.trim() }) }),
    onSuccess: () => { setName(''); setPrompt(''); refresh(); },
    onError: (err) => setNotice(err?.message || 'Could not add skill.'),
  });

  const toggleMutation = useMutation({
    mutationFn: (skill) => fetchJson(`/rooms/${room.id}/skills/${skill.id}`, { method: 'PATCH', body: JSON.stringify({ enabled: !skill.enabled }) }),
    onSuccess: refresh,
    onError: (err) => setNotice(err?.message || 'Could not update skill.'),
  });

  const delMutation = useMutation({
    mutationFn: (id) => fetchJson(`/rooms/${room.id}/skills/${id}`, { method: 'DELETE' }),
    onSuccess: refresh,
    onError: (err) => setNotice(err?.message || 'Could not delete skill.'),
  });

  return (
    <Card title="Skills" desc="Reusable prompt fragments the AI follows in this room. Toggle off to pause one without deleting it.">
      {notice && <div className="er-alert er-alert--err">{notice} <button type="button" className="portal-linkbtn" onClick={() => setNotice(null)}>Dismiss</button></div>}
      {skillsQuery.isLoading && <div className="portal-skeleton"><span /><span /></div>}
      {skills.length > 0 && (
        <div className="portal-list" style={{ marginBottom: 12 }}>
          {skills.map((skill) => (
            <div key={skill.id} className="portal-row">
              <button
                type="button" className="portal-tool" title={skill.enabled ? 'Disable' : 'Enable'}
                aria-label={`${skill.enabled ? 'Disable' : 'Enable'} skill ${skill.file_name}`}
                onClick={() => toggleMutation.mutate(skill)}
              >
                {skill.enabled ? <HiCheck size={15} /> : <HiXMark size={15} />}
              </button>
              <span className="portal-row__main">
                <span className="portal-row__text">{skill.file_name} {!skill.enabled && <span className="portal-flag">OFF</span>}</span>
                {skill.content && <span className="portal-row__sub">{skill.content}</span>}
              </span>
              <button
                type="button" className="portal-tool is-danger" title="Delete skill"
                aria-label={`Delete skill ${skill.file_name}`}
                onClick={() => { if (window.confirm(`Delete skill "${skill.file_name}"?`)) delMutation.mutate(skill.id); }}
              >
                <HiTrash size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
      <div style={{ display: 'grid', gap: 8 }}>
        <input className="er-input" value={name} placeholder="Skill name, e.g. Vocab coach" onChange={(e) => setName(e.target.value)} aria-label="Skill name" />
        <textarea className="er-textarea" rows={2} value={prompt} placeholder="What should the AI do? e.g. Explain every new word with one example." onChange={(e) => setPrompt(e.target.value)} aria-label="Skill prompt" />
        <div className="portal-actions">
          <button className="er-btn er-btn--ghost portal-mini-btn" disabled={addMutation.isPending || !name.trim() || !prompt.trim()} onClick={() => addMutation.mutate()}>
            <HiPlus size={14} /> {addMutation.isPending ? 'Adding…' : 'Add skill'}
          </button>
        </div>
      </div>
    </Card>
  );
}

function DocumentsCard({ room }) {
  const docsQuery = useQuery({
    queryKey: ['rooms', room.id, 'documents'],
    queryFn: () => fetchJson(`/rooms/${room.id}/documents`),
  });
  const docs = (Array.isArray(docsQuery.data) ? docsQuery.data : []).filter((d) => d.kind !== 'skill');
  const [uploading, setUploading] = useState(false);
  const [notice, setNotice] = useState(null);

  function refresh() {
    queryClient.invalidateQueries({ queryKey: ['rooms', room.id, 'documents'] });
  }

  async function handleFile(event) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setNotice(null);
    setUploading(true);
    try {
      const form = new FormData();
      form.append('file', file);
      const response = await fetch(`${API_BASE_URL}/rooms/${room.id}/documents`, {
        method: 'POST', credentials: 'include', body: form,
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `Upload failed (${response.status})`);
      }
      refresh();
      setNotice({ ok: true, text: `Indexed "${file.name}" for @ai.` });
      setTimeout(() => setNotice(null), 4000);
    } catch (err) {
      setNotice({ ok: false, text: err?.message || 'Upload failed.' });
    } finally {
      setUploading(false);
    }
  }

  const delMutation = useMutation({
    mutationFn: (id) => fetchJson(`/rooms/${room.id}/documents/${id}`, { method: 'DELETE' }),
    onSuccess: refresh,
    onError: (err) => setNotice({ ok: false, text: err?.message || 'Could not delete document.' }),
  });

  return (
    <Card title="Documents for AI" desc="pdf, md or txt up to 10MB. @ai searches these first when answering in this room.">
      {notice && <div className={`er-alert ${notice.ok ? 'er-alert--ok' : 'er-alert--err'}`}>{notice.text}</div>}
      <div className="portal-actions" style={{ marginBottom: 12 }}>
        <label className="er-btn er-btn--ghost portal-mini-btn" style={{ cursor: uploading ? 'wait' : 'pointer' }}>
          <HiPlus size={14} /> {uploading ? 'Indexing…' : 'Upload document'}
          <input type="file" accept=".pdf,.md,.txt" hidden disabled={uploading} onChange={handleFile} />
        </label>
      </div>
      {docsQuery.isLoading && <div className="portal-skeleton"><span /><span /></div>}
      {!docsQuery.isLoading && docs.length === 0 && (
        <div className="portal-empty">No documents yet. Upload slides, notes or a reading and @ai will use them.</div>
      )}
      {docs.length > 0 && (
        <div className="portal-list">
          {docs.map((doc) => (
            <div key={doc.id} className="portal-row">
              <span className="portal-badge">{(doc.file_type || 'FILE').toUpperCase()}</span>
              <span className="portal-row__main">
                <span className="portal-row__text">{doc.file_name}</span>
                {doc.created_at && <span className="portal-row__sub">{new Date(doc.created_at).toLocaleDateString()}</span>}
              </span>
              <button
                type="button" className="portal-tool is-danger" title="Delete document"
                aria-label={`Delete document ${doc.file_name}`}
                onClick={() => { if (window.confirm(`Delete "${doc.file_name}" from this room's AI?`)) delMutation.mutate(doc.id); }}
              >
                <HiTrash size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export function RoomConfigPage() {
  const { roomId } = useParams();
  const { user } = useAuth();

  const roomQuery = useQuery({
    queryKey: ['room', roomId],
    queryFn: () => fetchJson(`/rooms/${roomId}`),
    enabled: Boolean(roomId),
    retry: false,
  });
  const room = roomQuery.data ?? null;
  const isHost = room && user && String(room.host_id) === String(user.id);

  if (roomQuery.isLoading) {
    return (
      <div className="portal-app"><main className="portal-main"><div className="portal-skeleton"><span /><span /><span /></div></main></div>
    );
  }

  if (roomQuery.isError || !room) {
    return (
      <div className="portal-app">
        <main className="portal-main">
          <div className="er-alert er-alert--err">Room not found or you have no access.</div>
          <Link className="er-btn" style={{ textDecoration: 'none', marginTop: 12 }} to="/my-rooms"><HiArrowLeft size={14} /> My rooms</Link>
        </main>
      </div>
    );
  }

  if (!isHost) {
    return <Navigate to="/rooms" replace />;
  }

  return (
    <div className="portal-app">
      <main className="portal-main">
        <div className="portal-pagehead">
          <div>
            <div className="portal-pagehead__crumb"><Link to="/my-rooms">My rooms</Link> / Config</div>
            <h1>{room.name}</h1>
            <p>Room settings, access, AI prompt, skills and documents.</p>
          </div>
          <div className="portal-pagehead__actions">
            <Link className="er-btn" style={{ textDecoration: 'none' }} to={`/rooms/${room.id}`}>Enter room</Link>
          </div>
        </div>
        <div style={{ height: 16 }} />
        <div className="portal-stack">
          <BasicsCard key={`b-${room.updated_at || room.id}`} room={room} />
          <AccessCard key={`a-${room.updated_at || room.id}`} room={room} />
          <PromptCard key={`p-${room.updated_at || room.id}`} room={room} />
          <SkillsCard room={room} />
          <DocumentsCard room={room} />
        </div>
      </main>
    </div>
  );
}
