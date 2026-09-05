import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import Container from 'react-bootstrap/Container';
import Button from 'react-bootstrap/Button';
import Spinner from 'react-bootstrap/Spinner';
import { fetchJson } from '../../lib/api';
import { formatDate, formatDuration } from '../../lib/formatters';
import {
  HiClock, HiAcademicCap, HiMagnifyingGlass, HiArrowRight,
  HiChartBar,
} from 'react-icons/hi2';
import '../../styles/SessionsPage.css';

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

  const avgScore = sessions.length > 0
    ? Math.round(sessions.reduce((sum, s) => sum + ((s.review?.overall_score || s.score) || 0), 0) / sessions.length)
    : 0;

  return (
    <Container className="sessions-page py-4">
      <div className="sessions-page__header">
        <h1>Your sessions</h1>
        <p className="sessions-page__subtitle">Every room you have joined, with scores, duration, and review feedback.</p>
      </div>

      <div className="sessions-page__stats">
        {sessions.length} sessions — {avgScore} avg score — {filtered.length} showing
      </div>

      <div className="sessions-page__toolbar">
        <div className="sessions-page__search-wrap">
          <HiMagnifyingGlass size={15} className="sessions-page__search-icon" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by topic or tag..."
            className="sessions-page__search-input"
          />
        </div>
        <div className="sessions-page__filters">
          {[
            { key: 'all', label: 'All' },
            { key: 'recent', label: 'This week' },
            { key: 'reviewed', label: 'Reviewed' },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`sessions-page__filter-btn${filter === key ? ' is-active' : ''}`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="sessions-page__loading">
          <Spinner animation="border" variant="primary" />
          <span>Loading sessions...</span>
        </div>
      ) : filtered.length === 0 ? (
        <div className="sessions-page__empty">
          <HiClock size={24} />
          <p>No sessions yet</p>
          <Button as={Link} to="/rooms" variant="primary" className="px-3">Open Meeting</Button>
        </div>
      ) : (
        <div className="sessions-page__list">
          {filtered.map((session) => {
            const score = (session.review?.overall_score || session.score);
            return (
              <Link key={session.id} to={`/sessions/${session.id}`} className="sessions-page__row">
                <div className="sessions-page__row-main">
                  <div className="sessions-page__row-title">{session.topic || session.name || session.room_name || 'Practice Session'}</div>
                  <div className="sessions-page__row-meta">
                    <span>{formatDate(session.created_at)}</span>
                    <span className="sessions-page__meta-sep"> &middot; </span>
                    <span>{formatDuration(session.duration)}</span>
                    {session.review && <><span className="sessions-page__meta-sep"> &middot; </span><span className="sessions-page__reviewed">Reviewed</span></>}
                  </div>
                </div>
                <div className="sessions-page__row-score">{score != null ? Math.round(score) : '--'}</div>
              </Link>
            );
          })}
        </div>
      )}
    </Container>
  );
}
