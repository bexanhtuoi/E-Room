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
import { HiDocumentText, HiTrash, HiClock, HiBookOpen, HiArrowRight } from 'react-icons/hi2';

export function NotesPage() {
  const { t } = useTranslation();
  const { tier, features } = useSubscriptionStore();
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [deleting, setDeleting] = useState(null);

  const { data: notes = [], isLoading } = useQuery({
    queryKey: ['notes'],
    queryFn: () => fetchJson('/notes'),
    enabled: tier === 'pro_plus',
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => fetchJson(`/notes/${id}`, { method: 'DELETE' }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['notes'] }); setDeleting(null); },
  });

  if (!features.notes) {
    return (
      <>
        <Container className="py-5 text-center" style={{ maxWidth: 600 }}>
          <HiDocumentText size={48} style={{ opacity: 0.3, color: 'var(--color-text-muted)', marginBottom: 12 }} />
          <h3 className="fw-extrabold mb-2" style={{ fontFamily: 'Nunito, sans-serif' }}>{t('notes.upgrade_title')}</h3>
          <p className="text-muted mb-3">{t('notes.upgrade_desc')}</p>
          <Button variant="primary" className="rounded-pill" onClick={() => setShowUpgrade(true)}>{t('notes.upgrade_btn')}</Button>
        </Container>
        <UpgradePrompt feature="Session Notes" visible={showUpgrade} onClose={() => setShowUpgrade(false)} />
      </>
    );
  }

  return (
    <Container className="py-4" style={{ maxWidth: 720 }}>
      <div className="d-flex align-items-center gap-3 mb-4">
        <div style={{ width: 44, height: 44, borderRadius: 12, background: 'var(--color-accent-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <HiBookOpen size={22} style={{ color: 'var(--color-accent)' }} />
        </div>
        <div>
          <h2 className="fw-extrabold mb-0" style={{ fontFamily: 'Nunito, sans-serif' }}>{t('notes.title')}</h2>
          <p className="text-muted small mb-0">{t('notes.description')}</p>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-5"><Spinner animation="border" /></div>
      ) : notes.length === 0 ? (
        <div className="text-center py-5" style={{ color: 'var(--color-text-muted)' }}>
          <HiDocumentText size={36} style={{ opacity: 0.3, marginBottom: 8 }} />
          <h5 className="fw-bold" style={{ fontFamily: 'Nunito, sans-serif' }}>{t('notes.no_notes')}</h5>
          <p className="small">{t('notes.no_notes_desc')}</p>
          <Link to="/learning"><Button variant="outline-primary" size="sm" className="rounded-pill">{t('notes.start_session')}</Button></Link>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {notes.map((note) => (
            <div key={note.id} style={{ padding: '16px', borderRadius: 14, background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)' }}>
              <div className="d-flex justify-content-between align-items-start mb-2">
                <div>
                  <div className="fw-bold" style={{ fontSize: '0.9rem' }}>{note.title || 'Session Summary'}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', display: 'flex', gap: 8, marginTop: 2 }}>
                    <span><HiClock size={12} /> {formatDate(note.created_at)}</span>
                    {note.session_topic && <span>• {note.session_topic}</span>}
                  </div>
                </div>
                <button
                  onClick={() => { setDeleting(note.id); deleteMutation.mutate(note.id); }}
                  disabled={deleting === note.id}
                  style={{ width: 28, height: 28, borderRadius: '50%', border: 'none', flexShrink: 0, background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                >
                  <HiTrash size={14} />
                </button>
              </div>
              <div style={{ fontSize: '0.82rem', lineHeight: 1.6, color: 'var(--color-text-secondary)', whiteSpace: 'pre-wrap', maxHeight: 120, overflow: 'hidden' }}>
                {note.content?.slice(0, 300)}{note.content?.length > 300 ? '...' : ''}
              </div>
              {note.content?.length > 300 && (
                <Link to={`/notes/${note.id}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: 8, fontSize: '0.78rem', color: 'var(--color-accent)', textDecoration: 'none', fontWeight: 600 }}>
                  {t('notes.read_more')} <HiArrowRight size={12} />
                </Link>
              )}
              {note.tags?.length > 0 && (
                <div style={{ display: 'flex', gap: 4, marginTop: 8 }}>
                  {note.tags.map((tag) => (
                    <span key={tag} style={{ padding: '2px 8px', borderRadius: 99, background: 'var(--color-accent-muted)', color: 'var(--color-accent)', fontSize: '0.65rem', fontWeight: 600 }}>
                      {tag}
                    </span>
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
