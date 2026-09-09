import { useState } from 'react';
import { Link, Navigate, useParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { HiArrowLeft, HiCheck, HiCloudArrowUp, HiLockClosed, HiPlus, HiTrash, HiXMark } from 'react-icons/hi2';
import { useAuth } from '../../app/AuthContext';
import { API_BASE_URL, fetchJson } from '../../lib/api';
import { queryClient } from '../../lib/queryClient';
import { formatDateTime } from '../../lib/formatters';
import { TopicPicker } from './TopicPicker';
import { SeatSlider } from './SeatSlider';
import '../../styles/ProfilePage.css';

function patchRoom(roomId, data) {
  return fetchJson(`/rooms/${roomId}`, { method: 'PATCH', body: JSON.stringify(data) });
}

function ResumeHeader({ room }) {
  const topics = Array.isArray(room.topics) ? room.topics : [];
  return (
    <header className="pf-resume__head">
      <span className="portal-room__tile pf-room__tile">{(room.name || '?').trim().charAt(0).toUpperCase()}</span>
      <div className="pf-resume__id">
        <div className="pf-resume__name">
          <h1>{room.name}</h1>
          {room.is_private
            ? <span className="portal-flag" title="Only you and allowed emails can see this"><HiLockClosed size={11} /> PRIVATE</span>
            : <span className="portal-flag is-solid">PUBLIC</span>}
          <span className={`portal-status is-${room.status}`}>{room.status}</span>
        </div>
        <div className="portal-muted">
          {topics.length > 0 ? `${topics.join(' · ')} — ` : ''}
          opened {room.created_at ? formatDateTime(room.created_at) : '—'}
        </div>
        {room.description && <p className="pf-resume__desc">{room.description}</p>}
      </div>
      <Link className="er-btn" style={{ textDecoration: 'none', flexShrink: 0 }} to={`/rooms/${room.id}`}>Enter room</Link>
    </header>
  );
}

function BasicsCard({ room }) {
  const [name, setName] = useState(room.name || '');
  const [description, setDescription] = useState(room.description || '');
  const [topics, setTopics] = useState(Array.isArray(room.topics) ? room.topics : []);
  const [seats, setSeats] = useState(room.max_participants || 4);
  const [notice, setNotice] = useState(null);

  const saveMutation = useMutation({
    mutationFn: () => patchRoom(room.id, {
      name: name.trim(), description: description.trim() || null, topics, max_participants: seats,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rooms', 'list'] });
      queryClient.invalidateQueries({ queryKey: ['room', room.id] });
      setNotice({ ok: true, text: 'Basics saved.' });
      setTimeout(() => setNotice(null), 3000);
    },
    onError: (err) => setNotice({ ok: false, text: err?.message || 'Could not save.' }),
  });

  return (
    <section className="portal-panel">
      <div className="portal-panel__head"><h2>Basics</h2></div>
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
        <div className="portal-actions">
          <button className="er-btn" disabled={saveMutation.isPending || !name.trim()} onClick={() => saveMutation.mutate()}>
            {saveMutation.isPending ? 'Saving…' : 'Save basics'}
          </button>
        </div>
      </div>
    </section>
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
    <section className="portal-panel">
      <div className="portal-panel__head"><h2>Who can enter</h2></div>
      {notice && <div className={`er-alert ${notice.ok ? 'er-alert--ok' : 'er-alert--err'}`}>{notice.text}</div>}
      <div className="portal-switchlist">
        <button type="button" onClick={() => setIsPrivate((v) => !v)} aria-pressed={isPrivate} className="portal-switch">
          {isPrivate ? 'Private room' : 'Public room'}
          <span className={`portal-switch__track${isPrivate ? ' is-on' : ''}`}><span className="portal-switch__thumb" /></span>
        </button>
      </div>
      <p className="portal-muted">
        {isPrivate
          ? 'Invisible everywhere except for you and the emails below.'
          : 'Anyone can find this room on /rooms and home.'}
      </p>
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
    </section>
  );
}

function PromptCard({ room }) {
  const defaultQuery = useQuery({
    queryKey: ['rooms', 'prompt-default'],
    queryFn: () => fetchJson('/rooms/prompt-default').then((r) => r?.default_system_prompt || ''),
    staleTime: 300_000,
  });
  const [override, setOverride] = useState(room.system_prompt || '');
  const [notice, setNotice] = useState(null);

  const saveMutation = useMutation({
    mutationFn: () => patchRoom(room.id, { system_prompt: override.trim() || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['room', room.id] });
      setNotice({ ok: true, text: override.trim() ? 'Custom prompt saved.' : 'Back to the default prompt.' });
      setTimeout(() => setNotice(null), 3000);
    },
    onError: (err) => setNotice({ ok: false, text: err?.message || 'Could not save.' }),
  });

  return (
    <section className="portal-panel">
      <div className="portal-panel__head"><h2>AI prompt</h2>{override.trim() ? <span className="portal-flag is-solid">OVERRIDDEN</span> : <span className="portal-flag">DEFAULT</span>}</div>
      {notice && <div className={`er-alert ${notice.ok ? 'er-alert--ok' : 'er-alert--err'}`}>{notice.text}</div>}
      <details className="pf-details">
        <summary>See the default E-Room prompt</summary>
        <pre className="pf-pre">{defaultQuery.isLoading ? 'Loading…' : (defaultQuery.data || 'Default prompt unavailable.')}</pre>
      </details>
      <label className="er-label" htmlFor="cfg-prompt" style={{ marginTop: 12 }}>Your override (empty = use default)</label>
      <textarea
        id="cfg-prompt" className="er-textarea" rows={4} value={override}
        placeholder="e.g. Correct my grammar gently after each answer. Explain new words with examples."
        onChange={(e) => setOverride(e.target.value)}
      />
      <div className="portal-actions">
        <button className="er-btn" disabled={saveMutation.isPending} onClick={() => saveMutation.mutate()}>
          {saveMutation.isPending ? 'Saving…' : 'Save prompt'}
        </button>
      </div>
    </section>
  );
}

function DocumentsCard({ room }) {
  const docsQuery = useQuery({
    queryKey: ['rooms', room.id, 'documents'],
    queryFn: () => fetchJson(`/rooms/${room.id}/documents`),
  });
  const docs = (Array.isArray(docsQuery.data) ? docsQuery.data : []).filter((d) => d.kind !== 'skill');
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [notice, setNotice] = useState(null);

  function refresh() {
    queryClient.invalidateQueries({ queryKey: ['rooms', room.id, 'documents'] });
  }

  async function uploadFile(file) {
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
    <section className="portal-panel">
      <div className="portal-panel__head"><h2>Documents for AI <span className="portal-count">{docs.length}</span></h2></div>
      {notice && <div className={`er-alert ${notice.ok ? 'er-alert--ok' : 'er-alert--err'}`}>{notice.text}</div>}
      <div
        className={`pf-drop${dragging ? ' is-drag' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); uploadFile(e.dataTransfer.files?.[0]); }}
        onClick={() => document.getElementById('cfg-file').click()}
        role="button" tabIndex={0} aria-label="Upload document"
        onKeyDown={(e) => { if (e.key === 'Enter') document.getElementById('cfg-file').click(); }}
      >
        <HiCloudArrowUp size={28} />
        <strong>{uploading ? 'Indexing…' : 'Drop a file here or click to browse'}</strong>
        <span className="portal-muted">pdf, md or txt up to 10MB — @ai searches these first</span>
        <input id="cfg-file" type="file" accept=".pdf,.md,.txt" hidden disabled={uploading} onChange={(e) => { uploadFile(e.target.files?.[0]); e.target.value = ''; }} />
      </div>
      {docsQuery.isLoading && <div className="portal-skeleton"><span /><span /></div>}
      {!docsQuery.isLoading && docs.length === 0 && (
        <div className="portal-empty">No documents yet. Upload slides, notes or a reading and @ai will use them.</div>
      )}
      {docs.length > 0 && (
        <div className="portal-list" style={{ marginTop: 12 }}>
          {docs.map((doc) => (
            <div key={doc.id} className="portal-row">
              <span className="portal-badge"><HiCheck size={12} /> {(doc.file_type || 'FILE').toUpperCase()}</span>
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
    </section>
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
      <main className="portal-main pf-center">
        <div className="portal-pagehead">
          <div>
            <div className="portal-pagehead__crumb"><Link to="/my-rooms">My rooms</Link> / Config</div>
          </div>
        </div>
        <div className="pf-resume">
          <ResumeHeader room={room} />
          <BasicsCard key={`b-${room.id}`} room={room} />
          <AccessCard key={`a-${room.id}`} room={room} />
          <PromptCard key={`p-${room.id}`} room={room} />
          <DocumentsCard room={room} />
        </div>
      </main>
    </div>
  );
}
