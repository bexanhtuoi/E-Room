import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import Container from 'react-bootstrap/Container';
import Button from 'react-bootstrap/Button';
import Spinner from 'react-bootstrap/Spinner';
import { fetchJson } from '../../lib/api';
import { formatDateTime, formatDuration } from '../../lib/formatters';
import { HiArrowLeft, HiClock, HiCheckCircle, HiAcademicCap, HiSparkles } from 'react-icons/hi2';
import { CorrectionCard } from '../chat/CorrectionCard';
import { ExpertResponse } from '../chat/ExpertResponse';
import { TagBadge } from '../../components/tags/TagBadge';

export function SessionDetailPage() {
  const { sessionId } = useParams();
  const { t } = useTranslation();

  const { data: session, isLoading, error } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => fetchJson(`/sessions/${sessionId}`),
  });

  if (isLoading) {
    return (
      <div className="text-center py-5"><Spinner animation="border" /></div>
    );
  }

  if (error || !session) {
    return (
      <Container className="py-5 text-center" style={{ maxWidth: 600 }}>
        <HiAcademicCap size={48} style={{ opacity: 0.3, marginBottom: 12, color: 'var(--color-text-muted)' }} />
        <h4 className="fw-bold" style={{ fontFamily: 'Nunito, sans-serif' }}>{t('sessions.not_found')}</h4>
        <p className="text-muted small mb-3">{t('sessions.session_deleted')}</p>
        <Link to="/sessions"><Button variant="outline-primary" size="sm" className="rounded-pill"><HiArrowLeft size={14} className="me-1" /> {t('sessions.back_to_sessions')}</Button></Link>
      </Container>
    );
  }

  const review = session.review;
  const score = review?.overall_score || session.score;
  const corrections = review?.corrections || session.corrections || [];
  const expertResponses = review?.expert_responses || session.expert_responses || [];

  return (
    <Container className="py-4" style={{ maxWidth: 720 }}>
      {/* Back */}
      <Link to="/sessions" style={{
        display: 'inline-flex', alignItems: 'center', gap: 4,
        color: 'var(--color-text-muted)', fontSize: '0.82rem', fontWeight: 600,
        marginBottom: 16, textDecoration: 'none', cursor: 'pointer',
      }}
        onMouseOver={(e) => { e.currentTarget.style.color = 'var(--color-accent)'; }}
        onMouseOut={(e) => { e.currentTarget.style.color = 'var(--color-text-muted)'; }}
      >
        <HiArrowLeft size={14} /> {t('sessions.back_to_sessions')}
      </Link>

      {/* Header */}
      <div style={{
        padding: '24px', borderRadius: 16,
        background: 'var(--color-bg-elevated)',
        border: '1px solid var(--color-border)',
        marginBottom: 20,
      }}>
        <div className="d-flex align-items-start gap-4">
          {/* Score */}
          {score != null && (
            <div style={{
              width: 72, height: 72, borderRadius: '50%', flexShrink: 0,
              background: 'var(--color-accent-gradient)',
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              color: '#fff', fontWeight: 800,
            }}>
              <span style={{ fontSize: '1.4rem', lineHeight: 1 }}>{Math.round(score)}</span>
              <span style={{ fontSize: '0.55rem', fontWeight: 600, opacity: 0.8 }}>/10</span>
            </div>
          )}
          <div style={{ flex: 1 }}>
            <h3 className="fw-extrabold mb-1" style={{ fontFamily: 'Nunito, sans-serif' }}>
              {session.topic || session.name || 'Practice Session'}
            </h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, fontSize: '0.82rem', color: 'var(--color-text-muted)' }}>
              <span className="d-flex align-items-center gap-1"><HiClock size={14} /> {formatDuration(session.duration)}</span>
              <span>{formatDateTime(session.created_at)}</span>
              {session.participants && <span>{session.participants} participants</span>}
            </div>
            {session.tags && session.tags.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 8 }}>
                {session.tags.map((tag) => (
                  <TagBadge key={tag} label={typeof tag === 'string' ? tag : tag.name || tag} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Review section */}
      {review && (
        <div style={{ marginBottom: 20 }}>
          <h5 className="fw-bold mb-3 d-flex align-items-center gap-2" style={{ fontFamily: 'Nunito, sans-serif' }}>
            <HiSparkles size={18} style={{ color: 'var(--color-accent)' }} />
            {t('sessions.review')}
          </h5>
          {review.strengths && review.strengths.length > 0 && (
            <div style={{ padding: '12px 14px', borderRadius: 12, background: 'var(--color-success-muted)', marginBottom: 8 }}>
              <div className="fw-bold small text-muted mb-2" style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>💪 Strengths</div>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: '0.88rem' }}>
                {review.strengths.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          )}
          {review.improvements && review.improvements.length > 0 && (
            <div style={{ padding: '12px 14px', borderRadius: 12, background: 'var(--color-accent-muted)' }}>
              <div className="fw-bold small text-muted mb-2" style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>🎯 Areas to Improve</div>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: '0.88rem' }}>
                {review.improvements.map((imp, i) => <li key={i}>{imp}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Corrections */}
      {corrections.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <h5 className="fw-bold mb-3" style={{ fontFamily: 'Nunito, sans-serif' }}>Corrections ({corrections.length})</h5>
          <div>
            {corrections.map((c, i) => (
              <CorrectionCard key={c.id || i} correction={c} />
            ))}
          </div>
        </div>
      )}

      {/* Expert responses */}
      {expertResponses.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <h5 className="fw-bold mb-3" style={{ fontFamily: 'Nunito, sans-serif' }}>Expert Answers ({expertResponses.length})</h5>
          <div>
            {expertResponses.map((r, i) => (
              <ExpertResponse key={r.id || i} response={r} />
            ))}
          </div>
        </div>
      )}

      {/* Transcript */}
      {session.transcript && (
        <div>
          <h5 className="fw-bold mb-3 d-flex align-items-center gap-2" style={{ fontFamily: 'Nunito, sans-serif' }}>
            <HiCheckCircle size={18} style={{ color: 'var(--color-success)' }} />
            Transcript
          </h5>
          <div style={{
            padding: '16px', borderRadius: 12,
            background: 'var(--color-bg-surface)',
            border: '1px solid var(--color-border)',
            fontSize: '0.85rem', lineHeight: 1.7,
            whiteSpace: 'pre-wrap', fontFamily: 'inherit',
          }}>
            {typeof session.transcript === 'string' ? session.transcript :
              Array.isArray(session.transcript) ? session.transcript.map(m => `[${m.speaker || '?'}] ${m.text}`).join('\n') :
              'Transcript not available'}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="text-center mt-4 mb-4">
        <Link to="/learning">
          <Button variant="primary" className="rounded-pill px-4">Find another room</Button>
        </Link>
      </div>
    </Container>
  );
}
