import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import Container from 'react-bootstrap/Container';
import Button from 'react-bootstrap/Button';
import Spinner from 'react-bootstrap/Spinner';
import { fetchJson } from '../../lib/api';
import { formatDate, formatDateTime } from '../../lib/formatters';
import { HiArrowLeft, HiClock, HiBookOpen, HiTag } from 'react-icons/hi2';

export function NoteDetailPage() {
  const { noteId } = useParams();
  const { t } = useTranslation();

  const { data: note, isLoading, error } = useQuery({
    queryKey: ['note', noteId],
    queryFn: () => fetchJson(`/notes/${noteId}`),
  });

  if (isLoading) {
    return (
      <div className="text-center py-5"><Spinner animation="border" variant="primary" /></div>
    );
  }

  if (error || !note) {
    return (
      <Container className="py-5 text-center" style={{ maxWidth: 600 }}>
        <HiBookOpen size={48} style={{ opacity: 0.3, marginBottom: 12, color: 'var(--color-text-muted)' }} />
        <h4 className="fw-bold" style={{ fontFamily: 'Nunito, sans-serif' }}>{t('common.error')}</h4>
        <p className="text-muted small mb-3">{error?.message || t('notes.no_notes')}</p>
        <Link to="/notes"><Button variant="outline-primary" size="sm" className="rounded-pill"><HiArrowLeft size={14} className="me-1" /> {t('notes.back_to_notes')}</Button></Link>
      </Container>
    );
  }

  return (
    <Container className="py-4" style={{ maxWidth: 720 }}>
      {/* Back link */}
      <Link to="/notes" style={{
        display: 'inline-flex', alignItems: 'center', gap: 4,
        color: 'var(--color-text-muted)', fontSize: '0.82rem', fontWeight: 600,
        marginBottom: 16, textDecoration: 'none', cursor: 'pointer',
      }}
        onMouseOver={(e) => { e.currentTarget.style.color = 'var(--color-accent)'; }}
        onMouseOut={(e) => { e.currentTarget.style.color = 'var(--color-text-muted)'; }}
      >
        <HiArrowLeft size={14} /> {t('notes.back_to_notes')}
      </Link>

      {/* Header */}
      <div style={{
        padding: '24px', borderRadius: 16,
        background: 'var(--color-bg-elevated)',
        border: '1px solid var(--color-border)',
        marginBottom: 20,
      }}>
        <div className="d-flex align-items-start gap-3">
          <div style={{
            width: 44, height: 44, borderRadius: 12, flexShrink: 0,
            background: 'var(--color-accent-muted)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <HiBookOpen size={22} style={{ color: 'var(--color-accent)' }} />
          </div>
          <div style={{ flex: 1 }}>
            <h3 className="fw-extrabold mb-2" style={{ fontFamily: 'Nunito, sans-serif' }}>
              {note.title || t('notes.session_summary')}
            </h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, fontSize: '0.82rem', color: 'var(--color-text-muted)' }}>
              <span className="d-flex align-items-center gap-1">
                <HiClock size={14} /> {formatDateTime(note.created_at)}
              </span>
              {note.session_topic && (
                <span>• {note.session_topic}</span>
              )}
            </div>

            {/* Tags */}
            {note.tags && note.tags.length > 0 && (
              <div className="d-flex align-items-center gap-1 mt-3" style={{ flexWrap: 'wrap' }}>
                <HiTag size={13} style={{ color: 'var(--color-text-muted)', flexShrink: 0 }} />
                {note.tags.map((tag) => (
                  <span key={tag} style={{
                    padding: '2px 8px', borderRadius: 99,
                    background: 'var(--color-accent-muted)',
                    color: 'var(--color-accent)', fontSize: '0.72rem', fontWeight: 600,
                  }}>
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      {note.content && (
        <div style={{
          padding: '24px', borderRadius: 16,
          background: 'var(--color-bg-elevated)',
          border: '1px solid var(--color-border)',
          marginBottom: 20,
        }}>
          <h5 className="fw-bold mb-3 d-flex align-items-center gap-2" style={{ fontFamily: 'Nunito, sans-serif', fontSize: '0.95rem' }}>
            <HiBookOpen size={16} style={{ color: 'var(--color-accent)' }} />
            {t('notes.note_content')}
          </h5>
          <div style={{
            fontSize: '0.88rem', lineHeight: 1.7,
            color: 'var(--color-text-secondary)',
            whiteSpace: 'pre-wrap',
            fontFamily: 'inherit',
          }}>
            {note.content}
          </div>
        </div>
      )}

      {/* Session context */}
      {note.session_topic && (
        <div style={{
          padding: '16px 20px', borderRadius: 14,
          background: 'var(--color-bg-surface)',
          border: '1px solid var(--color-border)',
          marginBottom: 20,
        }}>
          <h6 className="fw-bold mb-2 d-flex align-items-center gap-2" style={{ fontFamily: 'Nunito, sans-serif', fontSize: '0.85rem' }}>
            {t('notes.session_context')}
          </h6>
          <p className="text-muted small mb-0">
            <span className="fw-semibold" style={{ color: 'var(--color-text-secondary)' }}>{t('sessions.title')}:</span>{' '}
            {note.session_topic}
          </p>
          <p className="text-muted small mb-0 mt-1">
            <span className="fw-semibold" style={{ color: 'var(--color-text-secondary)' }}>{t('notes.created_at')}:</span>{' '}
            {formatDate(note.created_at)}
          </p>
        </div>
      )}

      {/* Back action */}
      <div className="text-center mt-4 mb-4">
        <Link to="/notes">
          <Button variant="outline-primary" className="rounded-pill px-4">
            <HiArrowLeft size={14} className="me-1" /> {t('notes.back_to_notes')}
          </Button>
        </Link>
      </div>
    </Container>
  );
}
