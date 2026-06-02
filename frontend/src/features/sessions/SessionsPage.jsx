import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import Container from 'react-bootstrap/Container';
import Button from 'react-bootstrap/Button';
import Spinner from 'react-bootstrap/Spinner';
import Form from 'react-bootstrap/Form';
import { fetchJson } from '../../lib/api';
import { formatDate, formatDuration } from '../../lib/formatters';
import { HiClock, HiCheckCircle, HiAcademicCap, HiMagnifyingGlass, HiArrowRight } from 'react-icons/hi2';

export function SessionsPage() {
  const { t } = useTranslation();
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');

  const { data: sessions = [], isLoading } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => fetchJson('/sessions'),
  });

  const filtered = sessions.filter((s) => {
    const topic = (s.topic || s.name || '').toLowerCase();
    const tags = (s.tags || []).join(' ').toLowerCase();
    const query = search.toLowerCase();
    const matchesSearch = !search || topic.includes(query) || tags.includes(query);
    if (filter === 'recent') return matchesSearch && new Date(s.created_at || Date.now()) > new Date(Date.now() - 7 * 86400000);
    if (filter === 'reviewed') return matchesSearch && s.review;
    return matchesSearch;
  });

  return (
    <Container className="py-4" style={{ maxWidth: 800 }}>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="fw-extrabold mb-1 d-flex align-items-center gap-2" style={{ fontFamily: 'Nunito, sans-serif' }}>
            <HiClock size={24} style={{ color: 'var(--color-accent)' }} />
            {t('sessions.title')}
          </h2>
          <p className="text-muted mb-0 small">{t('sessions.practice_history')}</p>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 200, position: 'relative' }}>
          <HiMagnifyingGlass size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }} />
          <Form.Control
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('sessions.search')}
            className="rounded-3 ps-5"
            style={{ fontSize: '0.85rem' }}
          />
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          {[
            { key: 'all', label: t('sessions.all') },
            { key: 'recent', label: t('sessions.recent') },
            { key: 'reviewed', label: t('sessions.reviewed') },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              style={{
                padding: '6px 14px', borderRadius: 99,
                background: filter === key ? 'var(--color-accent-gradient)' : 'var(--color-bg-surface)',
                color: filter === key ? '#fff' : 'var(--color-text-secondary)',
                border: filter === key ? 'none' : '1px solid var(--color-border)',
                cursor: 'pointer', fontWeight: 600, fontSize: '0.78rem',
                fontFamily: 'inherit', transition: 'all 0.12s',
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Sessions list */}
      {isLoading ? (
        <div className="text-center py-5"><Spinner animation="border" /></div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-5" style={{ color: 'var(--color-text-muted)' }}>
          <HiAcademicCap size={48} style={{ opacity: 0.3, marginBottom: 12 }} />
          <h5 className="fw-bold" style={{ fontFamily: 'Nunito, sans-serif' }}>{t('sessions.no_sessions')}</h5>
          <p className="small">{t('sessions.no_sessions_desc')}</p>
          <Link to="/learning">
            <Button variant="primary" size="sm" className="rounded-pill">{t('sessions.find_room')}</Button>
          </Link>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {filtered.map((session) => {
            const score = session.review?.overall_score || session.score;
            return (
              <Link
                key={session.id}
                to={`/sessions/${session.id}`}
                style={{
                  display: 'flex', alignItems: 'center', gap: 14,
                  padding: '14px 16px', borderRadius: 14,
                  background: 'var(--color-bg-elevated)',
                  border: '1px solid var(--color-border)',
                  textDecoration: 'none', color: 'inherit',
                  transition: 'all 0.15s',
                }}
                onMouseOver={(e) => { e.currentTarget.style.borderColor = 'var(--color-border-strong)'; e.currentTarget.style.transform = 'translateY(-1px)'; }}
                onMouseOut={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)'; e.currentTarget.style.transform = 'translateY(0)'; }}
              >
                {/* Score circle */}
                <div style={{
                  width: 44, height: 44, borderRadius: '50%', flexShrink: 0,
                  background: score ? 'var(--color-accent-muted)' : 'var(--color-bg-surface)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontWeight: 800, fontSize: '0.9rem',
                  color: score ? 'var(--color-accent)' : 'var(--color-text-muted)',
                }}>
                  {score != null ? `${Math.round(score)}` : '—'}
                </div>
                {/* Info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="fw-bold" style={{ fontSize: '0.9rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {session.topic || session.name || session.room_name || 'Practice Session'}
                  </div>
                  <div style={{ display: 'flex', gap: 10, marginTop: 2, fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                    <span>{formatDate(session.created_at)}</span>
                    <span>•</span>
                    <span>{formatDuration(session.duration)}</span>
                    {session.review && (
                      <>
                        <span>•</span>
                        <span style={{ color: 'var(--color-success)' }}>✅ Reviewed</span>
                      </>
                    )}
                  </div>
                  {session.tags && session.tags.length > 0 && (
                    <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
                      {session.tags.slice(0, 3).map((tag) => (
                        <span key={tag} style={{
                          padding: '1px 8px', borderRadius: 99,
                          background: 'var(--color-accent-muted)',
                          color: 'var(--color-accent)', fontSize: '0.65rem', fontWeight: 600,
                        }}>
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <HiArrowRight size={16} style={{ color: 'var(--color-text-muted)', flexShrink: 0 }} />
              </Link>
            );
          })}
        </div>
      )}
    </Container>
  );
}
