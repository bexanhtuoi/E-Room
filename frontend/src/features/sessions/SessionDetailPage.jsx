import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import Container from 'react-bootstrap/Container';
import Button from 'react-bootstrap/Button';
import Spinner from 'react-bootstrap/Spinner';
import { fetchJson } from '../../lib/api';
import { formatDateTime, formatDuration } from '../../lib/formatters';
import { HiArrowLeft, HiClock, HiCheckCircle, HiAcademicCap, HiSparkles, HiChatBubbleLeftRight } from 'react-icons/hi2';
import { CorrectionCard } from '../chat/CorrectionCard';
import { ExpertResponse } from '../chat/ExpertResponse';
import { TagBadge } from '../../components/tags/TagBadge';
import '../../styles/SessionDetailPage.css';

export function SessionDetailPage() {
  const { sessionId } = useParams();
  const { t } = useTranslation();

  const { data: session, isLoading, error } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => fetchJson(`/sessions/${sessionId}`),
  });

  if (isLoading) {
    return (
      <Container className="session-detail-page py-4">
        <div className="session-detail-page__loading">
          <Spinner animation="border" variant="primary" />
          <span>Loading session...</span>
        </div>
      </Container>
    );
  }

  if (error || !session) {
    return (
      <Container className="session-detail-page py-4">
        <div className="session-detail-page__error">
          <HiAcademicCap size={48} />
          <h3>Session not found</h3>
          <p>This session may have been deleted or is no longer available.</p>
          <Link to="/sessions"><Button variant="outline-primary" className="px-3">Back to sessions</Button></Link>
        </div>
      </Container>
    );
  }

  const review = session.review;
  const score = review?.overall_score || session.score;
  const corrections = review?.corrections || session.corrections || [];
  const expertResponses = review?.expert_responses || session.expert_responses || [];
  const tags = session.tags || [];

  return (
    <Container className="session-detail-page py-4">
      <Link to="/sessions" className="session-detail-page__back">
        Back to sessions
      </Link>

      <div className="session-detail-page__header">
        <h1>{session.topic || session.name || 'Practice Session'}</h1>
        <div className="session-detail-page__meta">
          <span>{formatDuration(session.duration)}</span>
          <span className="session-detail-page__meta-sep"> &middot; </span>
          <span>{formatDateTime(session.created_at)}</span>
          {session.participants && (
            <>
              <span className="session-detail-page__meta-sep"> &middot; </span>
              <span>{session.participants} participants</span>
            </>
          )}
        </div>
        {score != null && (
          <div className="session-detail-page__score">Score: {Math.round(score)}/10</div>
        )}
        {tags.length > 0 && (
          <div className="session-detail-page__tags">
            {tags.map((tag) => (
              <TagBadge key={tag} label={typeof tag === 'string' ? tag : tag.name || tag} />
            ))}
          </div>
        )}
      </div>

      {review && (
        <div className="session-detail-page__section">
          <h2>AI Review</h2>
          {review.strengths && review.strengths.length > 0 && (
            <div>
              <span className="session-detail-page__section-label">Strengths</span>
              <ul>
                {review.strengths.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          )}
          {review.improvements && review.improvements.length > 0 && (
            <div>
              <span className="session-detail-page__section-label">Areas to improve</span>
              <ul>
                {review.improvements.map((imp, i) => <li key={i}>{imp}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      {corrections.length > 0 && (
        <div className="session-detail-page__section">
          <h2>Corrections ({corrections.length})</h2>
          {corrections.map((c, i) => (
            <CorrectionCard key={c.id || i} correction={c} />
          ))}
        </div>
      )}

      {expertResponses.length > 0 && (
        <div className="session-detail-page__section">
          <h2>Expert answers ({expertResponses.length})</h2>
          {expertResponses.map((r, i) => (
            <ExpertResponse key={r.id || i} response={r} />
          ))}
        </div>
      )}

      {session.transcript && (
        <div className="session-detail-page__section">
          <h2>Transcript</h2>
          <div className="session-detail-page__transcript">
            {typeof session.transcript === 'string' ? session.transcript :
              Array.isArray(session.transcript) ? session.transcript.map(m => `[${m.speaker || '?'}] ${m.text}`).join('\n') :
              'Transcript not available'}
          </div>
        </div>
      )}

      <div className="session-detail-page__cta">
        <Link to="/rooms">Find another room</Link>
      </div>
    </Container>
  );
}
