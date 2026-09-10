import { useEffect, useRef, useState } from 'react';
import { Link, Navigate, useParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { HiArrowLeft, HiCalendarDays, HiChatBubbleLeftRight, HiCloudArrowUp, HiLockClosed, HiPlus, HiTrash, HiUserGroup, HiXMark } from 'react-icons/hi2';
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

function ResumeHeader({ room, messagesTotal }) {
  const topics = Array.isArray(room.topics) ? room.topics : [];
  return (
    <header className="pf-resume__head">
      <span className="portal-room__tile pf-room__tile pf-room__tile--lg">{(room.name || '?').trim().charAt(0).toUpperCase()}</span>
      <div className="pf-resume__id">
        <div className="pf-resume__name">
          <h1>{room.name}</h1>
          {room.is_private
            ? <span className="portal-flag" title="Only you and allowed emails can see this"><HiLockClosed size={11} /> PRIVATE</span>
            : <span className="portal-flag is-solid">PUBLIC</span>}
        </div>
        {room.description && <p className="pf-resume__desc">{room.description}</p>}
        {topics.length > 0 && (
          <div className="portal-topics">{topics.map((t) => <span key={t} className="portal-topic">{t}</span>)}</div>
        )}
        <div className="pf-resume__facts">
          <span className={`portal-status is-${room.status}`}>{room.status}</span>
          <span><HiUserGroup size={13} /> {room.max_participants} seats</span>
          <span><HiChatBubbleLeftRight size={13} /> {messagesTotal} messages</span>
          <span><HiCalendarDays size={13} /> opened {room.created_at ? formatDateTime(room.created_at) : '—'}</span>
          <span className="portal-muted">#{room.id}</span>
        </div>
      </div>
    </header>
  );
}

function DocumentsCard({ room }) {
  const docsQuery = useQuery({
    queryKey: ['rooms', room.id, 'documents'],
    queryFn: () => fetchJson(`/rooms/${room.id}/documents`),
  });
  const docs = (Array.isArray(docsQuery.data) ? docsQuery.data : []).filter((d) => d.kind !== 'skill');
  const [uploading, setUploading] = useState(false);
  const [pendingName, setPendingName] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [notice, setNotice] = useState(null);

  function refresh() {
    queryClient.invalidateQueries({ queryKey: ['rooms', room.id, 'documents'] });
  }

  async function uploadFile(file) {
    if (!file) return;
    setNotice(null);
    setUploading(true);
    setPendingName(file.name);
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
      setPendingName(null);
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
      {(docs.length > 0 || pendingName) && (
        <div className="portal-list" style={{ marginTop: 12 }}>
          {pendingName && (
            <div className="portal-row">
              <span className="pf-spin" aria-hidden="true" />
              <span className="portal-row__main">
                <span className="portal-row__text">{pendingName}</span>
                <span className="portal-row__sub">Indexing for @ai…</span>
              </span>
            </div>
          )}
          {docs.map((doc) => (
            <div key={doc.id} className="portal-row">
              <span className="portal-badge">{(doc.file_type || 'FILE').toUpperCase()}</span>
              <span className="portal-row__main">
                <a
                  className="portal-row__text portal-row__link"
                  href={`${API_BASE_URL}/rooms/${room.id}/documents/${doc.id}/file`}
                  target="_blank" rel="noreferrer" title={`Open ${doc.file_name}`}
                >
                  {doc.file_name}
                </a>
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

function ConfigForm({ room, defaultPrompt, onReset }) {
  const [name, setName] = useState(room.name || '');
  const [description, setDescription] = useState(room.description || '');
  const [topics, setTopics] = useState(Array.isArray(room.topics) ? room.topics : []);
  const [seats, setSeats] = useState(room.max_participants || 4);
  const [isPrivate, setIsPrivate] = useState(Boolean(room.is_private));
  const [emails, setEmails] = useState(Array.isArray(room.allowed_emails) ? room.allowed_emails : []);
  const [draft, setDraft] = useState('');
  const [prompt, setPrompt] = useState(room.system_prompt || defaultPrompt);
  const [notice, setNotice] = useState(null);
  const promptRef = useRef(null);

  useEffect(() => {
    if (!room.system_prompt && defaultPrompt && !prompt) setPrompt(defaultPrompt);
  }, [defaultPrompt]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const el = promptRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = `${el.scrollHeight}px`;
    }
  }, [prompt]);

  const initialPrompt = room.system_prompt || defaultPrompt;
  const dirty = name.trim() !== (room.name || '')
    || description.trim() !== (room.description || '')
    || JSON.stringify(topics) !== JSON.stringify(room.topics || [])
    || seats !== room.max_participants
    || isPrivate !== Boolean(room.is_private)
    || JSON.stringify(emails) !== JSON.stringify(room.allowed_emails || [])
    || prompt.trim() !== (initialPrompt || '').trim();

  const saveMutation = useMutation({
    mutationFn: () => patchRoom(room.id, {
      name: name.trim(),
      description: description.trim() || null,
      topics,
      max_participants: seats,
      is_private: isPrivate,
      allowed_emails: emails,
      system_prompt: prompt.trim() === (defaultPrompt || '').trim() ? null : (prompt.trim() || null),
    }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['rooms', 'list'] });
      queryClient.setQueryData(['room', String(room.id)], updated);
      setNotice({ ok: true, text: 'Room config saved.' });
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
    <>
      <section className="portal-panel">
        <div className="portal-panel__head"><h2>Basics</h2></div>
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
        </div>
      </section>

      <section className="portal-panel">
        <div className="portal-panel__head"><h2>Who can enter</h2></div>
        <div className="portal-switchlist">
          <button type="button" onClick={() => setIsPrivate((v) => !v)} aria-pressed={isPrivate} className="portal-switch">
            {isPrivate ? 'Private room' : 'Public room'}
            <span className={`portal-switch__track${isPrivate ? ' is-on' : ''}`}><span className="portal-switch__thumb" /></span>
          </button>
        </div>
        <p className="portal-muted">
          {isPrivate ? 'Invisible everywhere except for you and the emails below.' : 'Anyone can find this room on /rooms and home.'}
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
              <button
              type="button" className="er-btn er-btn--ghost" title="Add email" aria-label="Add email"
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
                      type="button" aria-label={`Remove ${email}`} title={`Remove ${email}`}
                      onClick={() => setEmails((list) => list.filter((x) => x !== email))}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, font: 'inherit', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
                  >
                    <HiXMark size={10} />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </section>

      <section className="portal-panel">
        <div className="portal-panel__head">
          <h2>AI prompt</h2>
          {prompt.trim() !== (defaultPrompt || '').trim()
            ? <span className="portal-flag is-solid">CUSTOM</span>
            : <span className="portal-flag">DEFAULT</span>}
        </div>
        <p className="portal-muted" style={{ margin: '0 20px 12px' }}>Edit the prompt directly — @ai follows this in your room.</p>
        <textarea
          ref={promptRef}
          className="er-textarea pf-prompt" rows={12} value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          aria-label="AI prompt"
        />
      </section>

      <DocumentsCard room={room} />

      <div className="pf-savebar">
        {notice && <div className={`er-alert ${notice.ok ? 'er-alert--ok' : 'er-alert--err'}`}>{notice.text}</div>}
        <button className="er-btn er-btn--ghost pf-savebar__btn" disabled={!dirty || saveMutation.isPending} onClick={onReset}>
          Reset
        </button>
        <button className="er-btn pf-savebar__btn" disabled={saveMutation.isPending || !name.trim() || !dirty} onClick={() => saveMutation.mutate()}>
          {saveMutation.isPending ? 'Saving…' : 'Save changes'}
        </button>
      </div>
    </>
  );
}

export function RoomConfigPage() {
  const { roomId } = useParams();
  const { user } = useAuth();
  const [formKey, setFormKey] = useState(0);

  const roomQuery = useQuery({
    queryKey: ['room', roomId],
    queryFn: () => fetchJson(`/rooms/${roomId}`),
    enabled: Boolean(roomId),
    retry: false,
  });
  const defaultQuery = useQuery({
    queryKey: ['rooms', 'prompt-default'],
    queryFn: () => fetchJson('/rooms/prompt-default').then((r) => r?.default_system_prompt || ''),
    staleTime: 300_000,
  });
  const countQuery = useQuery({
    queryKey: ['messages', 'count', roomId],
    queryFn: () => fetchJson(`/messages/count?room_id=${roomId}`).then((r) => r?.count ?? 0).catch(() => 0),
    enabled: Boolean(roomId),
    staleTime: 30_000,
  });

  const room = roomQuery.data ?? null;
  const isHost = room && user && String(room.host_id) === String(user.id);

  if (roomQuery.isLoading) {
    return (
      <div className="portal-app portal-app--page"><main className="portal-main"><div className="portal-skeleton"><span /><span /><span /></div></main></div>
    );
  }

  if (roomQuery.isError || !room) {
    return (
      <div className="portal-app portal-app--page">
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
    <div className="portal-app portal-app--page">
      <main className="portal-main pf-center">
        <div className="portal-pagehead">
          <div>
            <div className="pf-crumb"><Link to="/my-rooms">My rooms</Link> / Config</div>
          </div>
        </div>
        <div className="pf-resume">
          <ResumeHeader room={room} messagesTotal={typeof countQuery.data === 'number' ? countQuery.data : 0} />
          <ConfigForm
            key={`${room.id}-${formKey}`}
            room={room}
            defaultPrompt={defaultQuery.data || ''}
            onReset={() => setFormKey((k) => k + 1)}
          />
        </div>
      </main>
    </div>
  );
}
