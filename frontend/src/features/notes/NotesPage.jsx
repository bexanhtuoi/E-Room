import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import Container from 'react-bootstrap/Container';
import Button from 'react-bootstrap/Button';
import Spinner from 'react-bootstrap/Spinner';
import { fetchJson } from '../../lib/api';
import { queryClient } from '../../lib/queryClient';
import { useSubscriptionStore } from '../../stores/subscriptionStore';
import { UpgradePrompt } from '../subscription/UpgradePrompt';
import { formatDate } from '../../lib/formatters';
import { HiDocumentText, HiTrash, HiClock, HiBookOpen, HiArrowRight, HiMagnifyingGlass, HiSparkles } from 'react-icons/hi2';
import '../../styles/NotesPage.css';

export function NotesPage() {
  const { t } = useTranslation();
  const { tier, features } = useSubscriptionStore();
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [deleting, setDeleting] = useState(null);
  const [search, setSearch] = useState('');

  const { data: notes = [], isLoading } = useQuery({
    queryKey: ['notes'],
    queryFn: () => fetchJson('/notes'),
    enabled: tier === 'pro_plus',
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => fetchJson(`/notes/${id}`, { method: 'DELETE' }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['notes'] }); setDeleting(null); },
  });

  const filtered = notes.filter((note) => {
    const query = search.toLowerCase();
    return !search
      || (note.title || '').toLowerCase().includes(query)
      || (note.content || '').toLowerCase().includes(query)
      || (note.tags || []).join(' ').toLowerCase().includes(query);
  });

  if (!features.notes) {
    return (
      <>
        <Container className="notes-page py-4 text-center">
          <div className="notes-page__upgrade">
            <HiSparkles size={24} />
            <h3>Session notes are a Pro+ feature</h3>
            <p>Upgrade to unlock AI-generated session summaries, corrections, and personalized learning notes.</p>
            <Button variant="primary" className="px-3" onClick={() => setShowUpgrade(true)}>Upgrade to Pro+</Button>
          </div>
        </Container>
        <UpgradePrompt feature="Session Notes" visible={showUpgrade} onClose={() => setShowUpgrade(false)} />
      </>
    );
  }

  return (
    <Container className="notes-page py-4">
      <div className="notes-page__header">
        <h1>Notes</h1>
        <p>Session summaries, key corrections, and reminders from every room you have joined.</p>
      </div>

      <div className="notes-page__search-wrap">
        <HiMagnifyingGlass size={15} className="notes-page__search-icon" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search notes by title, content, or tags..."
          className="notes-page__search"
        />
      </div>

      {isLoading ? (
        <div className="notes-page__loading">
          <Spinner animation="border" variant="primary" />
          <span>Loading notes...</span>
        </div>
      ) : filtered.length === 0 ? (
        <div className="notes-page__empty">
          <HiDocumentText size={24} />
          <h3>{search ? 'No matching notes' : 'No notes yet'}</h3>
          <p>{search ? 'Try a different search term.' : 'After a Pro+ session, your notes will appear here automatically.'}</p>
          {!search && <Button as={Link} to="/rooms" variant="outline-primary" className="px-3">Start a session</Button>}
        </div>
      ) : (
        <div className="notes-page__list">
          {filtered.map((note) => (
            <div key={note.id} className="notes-page__row">
              <div className="notes-page__row-top">
                <h2 className="notes-page__row-title">{note.title || 'Session Summary'}</h2>
                <button
                  onClick={() => { setDeleting(note.id); deleteMutation.mutate(note.id); }}
                  disabled={deleting === note.id}
                  className="notes-page__delete"
                >
                  Delete
                </button>
              </div>
              <div className="notes-page__row-meta">
                <span>{formatDate(note.created_at)}</span>
                {note.session_topic && <><span className="notes-page__meta-sep"> &middot; </span><span>{note.session_topic}</span></>}
              </div>
              <div className="notes-page__row-preview">
                {(note.content || '').slice(0, 250)}{(note.content || '').length > 250 ? '...' : ''}
              </div>
              {(note.content || '').length > 250 && (
                <Link to={`/notes/${note.id}`} className="notes-page__read-more">Read full note</Link>
              )}
              {note.tags && note.tags.length > 0 && (
                <div className="notes-page__tags">
                  {note.tags.map((tag) => (
                    <span key={tag} className="notes-page__tag">{tag}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Container>
  );
}
