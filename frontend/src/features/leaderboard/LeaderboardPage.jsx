import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import Container from 'react-bootstrap/Container';
import Button from 'react-bootstrap/Button';
import Spinner from 'react-bootstrap/Spinner';
import { fetchJson } from '../../lib/api';
import { useSubscriptionStore } from '../../stores/subscriptionStore';
import { UpgradePrompt } from '../subscription/UpgradePrompt';
import { HiTrophy, HiArrowRight, HiClock, HiUserGroup } from 'react-icons/hi2';

const TIME_RANGES = ['weekly', 'monthly', 'all'];

export function LeaderboardPage() {
  const { t } = useTranslation();
  const { tier, features } = useSubscriptionStore();
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [period, setPeriod] = useState('weekly');
  const [tagFilter, setTagFilter] = useState('');

  const { data: leaderboardData = null, isLoading } = useQuery({
    queryKey: ['leaderboard', period, tagFilter],
    queryFn: () => fetchJson(`/leaderboard?period=${period}${tagFilter ? `&tag_id=${tagFilter}` : ''}`),
    enabled: tier === 'pro_plus',
  });
  const leaderboard = leaderboardData?.entries || [];

  if (!features.leaderboard) {
    return (
      <>
        <Container className="py-5 text-center" style={{ maxWidth: 600 }}>
          <HiTrophy size={48} style={{ opacity: 0.3, color: 'var(--color-text-muted)', marginBottom: 12 }} />
          <h3 className="fw-extrabold mb-2" style={{ fontFamily: 'Nunito, sans-serif' }}>{t('leaderboard.upgrade_title')}</h3>
          <p className="text-muted mb-3">{t('leaderboard.upgrade_desc')}</p>
          <Button variant="primary" className="rounded-pill" onClick={() => setShowUpgrade(true)}>{t('leaderboard.upgrade_btn')}</Button>
        </Container>
        <UpgradePrompt feature="Leaderboard" visible={showUpgrade} onClose={() => setShowUpgrade(false)} />
      </>
    );
  }

  return (
    <Container className="py-4" style={{ maxWidth: 600 }}>
      <div className="d-flex align-items-center gap-3 mb-4">
        <div style={{
          width: 44, height: 44, borderRadius: 12,
          background: 'linear-gradient(135deg, #f59e0b, #d97706)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <HiTrophy size={22} color="#fff" />
        </div>
        <div>
          <h2 className="fw-extrabold mb-0" style={{ fontFamily: 'Nunito, sans-serif' }}>{t('leaderboard.title')}</h2>
          <p className="text-muted small mb-0">{t('leaderboard.description', { period: period })}</p>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap' }}>
        <button
          key="weekly"
          onClick={() => setPeriod('weekly')}
          style={{
            padding: '6px 14px', borderRadius: 99,
            background: period === 'weekly' ? 'var(--color-accent-gradient)' : 'var(--color-bg-surface)',
            color: period === 'weekly' ? '#fff' : 'var(--color-text-secondary)',
            border: period === 'weekly' ? 'none' : '1px solid var(--color-border)',
            cursor: 'pointer', fontWeight: 600, fontSize: '0.78rem', fontFamily: 'inherit',
          }}
        >
          {t('leaderboard.period_weekly')}
        </button>
        <button
          key="monthly"
          onClick={() => setPeriod('monthly')}
          style={{
            padding: '6px 14px', borderRadius: 99,
            background: period === 'monthly' ? 'var(--color-accent-gradient)' : 'var(--color-bg-surface)',
            color: period === 'monthly' ? '#fff' : 'var(--color-text-secondary)',
            border: period === 'monthly' ? 'none' : '1px solid var(--color-border)',
            cursor: 'pointer', fontWeight: 600, fontSize: '0.78rem', fontFamily: 'inherit',
          }}
        >
          {t('leaderboard.period_monthly')}
        </button>
        <button
          key="all"
          onClick={() => setPeriod('all')}
          style={{
            padding: '6px 14px', borderRadius: 99,
            background: period === 'all' ? 'var(--color-accent-gradient)' : 'var(--color-bg-surface)',
            color: period === 'all' ? '#fff' : 'var(--color-text-secondary)',
            border: period === 'all' ? 'none' : '1px solid var(--color-border)',
            cursor: 'pointer', fontWeight: 600, fontSize: '0.78rem', fontFamily: 'inherit',
          }}
        >
          {t('leaderboard.period_all_time')}
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-5"><Spinner animation="border" /></div>
      ) : leaderboard.length === 0 ? (
        <div className="text-center py-5" style={{ color: 'var(--color-text-muted)' }}>
          <HiTrophy size={36} style={{ opacity: 0.3, marginBottom: 8 }} />
          <h5 className="fw-bold" style={{ fontFamily: 'Nunito, sans-serif' }}>{t('leaderboard.no_rankings')}</h5>
          <p className="small">{t('leaderboard.no_rankings_desc')}</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {leaderboard.map((entry, i) => {
            const rank = i + 1;
            const medal = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : `#${rank}`;
            const isEven = i % 2 === 0;

            return (
              <div key={entry.user_id || i} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '12px 14px', borderRadius: 14,
                background: isEven ? 'var(--color-bg-elevated)' : 'transparent',
                border: '1px solid var(--color-border)',
              }}>
                {/* Rank */}
                <div style={{
                  width: 36, textAlign: 'center',
                  fontSize: rank <= 3 ? '1.2rem' : '0.82rem',
                  fontWeight: 800, flexShrink: 0,
                  color: rank <= 3 ? undefined : 'var(--color-text-muted)',
                }}>
                  {medal}
                </div>
                {/* Avatar */}
                <div style={{
                  width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
                  background: `hsl(${i * 72}, 70%, 55%)`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: '#fff', fontWeight: 700, fontSize: '0.8rem',
                }}>
                  {(entry.display_name || '?')[0].toUpperCase()}
                </div>
                {/* Info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="fw-bold" style={{ fontSize: '0.88rem' }}>
                    {entry.display_name || 'Anonymous'}
                  </div>
                  <div style={{ display: 'flex', gap: 10, fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
                    <span><HiClock size={11} /> {Math.round((entry.speaking_time_seconds || 0) / 60)}m</span>
                    <span><HiUserGroup size={11} /> {entry.sessions_count || 0} sessions</span>
                  </div>
                </div>
                {/* Score */}
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--color-accent)', fontFamily: 'Nunito, sans-serif' }}>
                    {entry.avg_score != null ? Math.round(entry.avg_score) : 0}
                  </div>
                  <div style={{ fontSize: '0.6rem', color: 'var(--color-text-muted)', fontWeight: 600 }}>PTS</div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Container>
  );
}
