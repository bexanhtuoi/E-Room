import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import Container from 'react-bootstrap/Container';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import Modal from 'react-bootstrap/Modal';
import Spinner from 'react-bootstrap/Spinner';
import { fetchJson } from '../../lib/api';
import { queryClient } from '../../lib/queryClient';
import { useSubscriptionStore } from '../../stores/subscriptionStore';
import { UpgradePrompt } from '../subscription/UpgradePrompt';
import { useTagStore } from '../../stores/tagStore';
import { TagBadge } from '../../components/tags/TagBadge';
import { HiCalendarDays, HiPlus, HiPlay, HiTrash } from 'react-icons/hi2';

export function SeriesPage() {
  const { t } = useTranslation();
  const { tier, features } = useSubscriptionStore();
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [showCreate, setShowCreate] = useState(false);

  const { popularTags } = useTagStore();
  const tagMap = Object.fromEntries((popularTags || []).map((t) => [t.id, t.name || t]));
  const { data: series = [], isLoading } = useQuery({
    queryKey: ['series'],
    queryFn: () => fetchJson('/series'),
    enabled: tier === 'pro_plus',
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => fetchJson(`/series/${id}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['series'] }),
  });

  if (!features.series) {  // Series requires Pro+
    return (
      <>
        <Container className="py-5 text-center" style={{ maxWidth: 600 }}>
          <HiCalendarDays size={48} style={{ opacity: 0.3, color: 'var(--color-text-muted)', marginBottom: 12 }} />
          <h3 className="fw-extrabold mb-2" style={{ fontFamily: 'Nunito, sans-serif' }}>{t('series.upgrade_title')}</h3>
          <p className="text-muted mb-3">{t('series.upgrade_desc')}</p>
          <Button variant="primary" className="rounded-pill" onClick={() => setShowUpgrade(true)}>{t('series.upgrade_btn')}</Button>
        </Container>
        <UpgradePrompt feature="Room Series" visible={showUpgrade} onClose={() => setShowUpgrade(false)} />
      </>
    );
  }

  return (
    <Container className="py-4" style={{ maxWidth: 720 }}>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div className="d-flex align-items-center gap-3">
          <div style={{
            width: 44, height: 44, borderRadius: 12,
            background: 'var(--color-accent-muted)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <HiCalendarDays size={22} style={{ color: 'var(--color-accent)' }} />
          </div>
          <div>
            <h2 className="fw-extrabold mb-0" style={{ fontFamily: 'Nunito, sans-serif' }}>{t('series.title')}</h2>
            <p className="text-muted small mb-0">{t('series.description')}</p>
          </div>
        </div>
        <Button variant="primary" size="sm" className="rounded-pill" onClick={() => setShowCreate(true)}>
          <HiPlus size={14} className="me-1" /> {t('series.create')}
        </Button>
      </div>

      {isLoading ? (
        <div className="text-center py-5"><Spinner animation="border" /></div>
      ) : series.length === 0 ? (
        <div className="text-center py-5" style={{ color: 'var(--color-text-muted)' }}>
          <HiCalendarDays size={36} style={{ opacity: 0.3, marginBottom: 8 }} />
          <h5 className="fw-bold" style={{ fontFamily: 'Nunito, sans-serif' }}>{t('series.no_series')}</h5>
          <p className="small">{t('series.no_series_desc')}</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {series.map((s) => {
            const totalSessions = s.total_sessions || 0;
            const pct = 0;

            return (
              <div key={s.id} style={{
                padding: '16px', borderRadius: 14,
                background: 'var(--color-bg-elevated)',
                border: '1px solid var(--color-border)',
              }}>
                <div className="d-flex justify-content-between align-items-start mb-2">
                  <div style={{ flex: 1 }}>
                    <div className="fw-bold" style={{ fontSize: '0.9rem' }}>{s.title}</div>
                    <div className="text-muted" style={{ fontSize: '0.78rem' }}>
                      {s.tag_id && tagMap[s.tag_id] ? <TagBadge label={tagMap[s.tag_id]} /> : s.tag_id ? <span className="badge bg-secondary me-1">{s.tag_id.slice(0, 8)}</span> : null}
                      {s.schedule_cron || 'Scheduled'} • {totalSessions} sessions
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <button style={{
                      padding: '4px 10px', borderRadius: 99, border: 'none',
                      background: 'var(--color-success-muted)', color: 'var(--color-success)',
                      cursor: 'pointer', fontWeight: 600, fontSize: '0.72rem', fontFamily: 'inherit',
                      display: 'flex', alignItems: 'center', gap: 4,
                    }}>
                      <HiPlay size={12} /> {t('series.active')}
                    </button>
                    <button
                      onClick={() => deleteMutation.mutate(s.id)}
                      style={{
                        width: 28, height: 28, borderRadius: '50%', border: 'none',
                        background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer',
                      }}
                    >
                      <HiTrash size={14} />
                    </button>
                  </div>
                </div>
                {/* Progress bar */}
                <div style={{ height: 4, borderRadius: 99, background: 'var(--color-bg-surface)', marginTop: 8, overflow: 'hidden' }} />
                <div className="text-muted text-end" style={{ fontSize: '0.65rem', marginTop: 2 }}>
                  {0}/{totalSessions} sessions
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Modal */}
      <CreateSeriesModal visible={showCreate} onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); queryClient.invalidateQueries({ queryKey: ['series'] }); }} />
    </Container>
  );
}

function CreateSeriesModal({ visible, onClose, onCreated }) {
  const { t } = useTranslation();
  const { popularTags } = useTagStore();
  const [form, setForm] = useState({ title: '', tag_id: '', total_sessions: 4, schedule_cron: '0 0 * * 1' });

  const createMutation = useMutation({
    mutationFn: (data) => fetchJson('/series', { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: onCreated,
  });

  function handleSubmit(e) {
    e.preventDefault();
    createMutation.mutate(form);
  }

  function setFormField(field, value) {
    setForm({ ...form, [field]: value });
  }

  return (
    <Modal show={visible} onHide={onClose} centered className="rounded-4">
      <Modal.Body className="p-4">
        <h5 className="fw-bold mb-3" style={{ fontFamily: 'Nunito, sans-serif' }}>{t('series.modal_title')}</h5>
        <Form onSubmit={handleSubmit}>
          <Form.Group className="mb-3">
            <Form.Label className="small fw-semibold text-muted">{t('series.form_title')}</Form.Label>
            <Form.Control type="text" placeholder={t('series.form_title_placeholder')} value={form.title} onChange={(e) => setFormField('title', e.target.value)} required className="rounded-3" />
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Label className="small fw-semibold text-muted">{t('series.form_topic_tag')}</Form.Label>
            <Form.Select value={form.tag_id} onChange={(e) => setFormField('tag_id', e.target.value)} required className="rounded-3">
              <option value="">{t('series.form_select_tag')}</option>
              {popularTags.map((t) => (
                <option key={t.id || t} value={t.id || t}>{t.name || t}</option>
              ))}
            </Form.Select>
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Label className="small fw-semibold text-muted">{t('series.form_sessions')}</Form.Label>
            <Form.Control type="number" min={1} max={20} value={form.total_sessions} onChange={(e) => setFormField('total_sessions', parseInt(e.target.value) || 4)} className="rounded-3" />
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Label className="small fw-semibold text-muted">{t('series.form_schedule')}</Form.Label>
            <Form.Select value={form.schedule_cron} onChange={(e) => setFormField('schedule_cron', e.target.value)} className="rounded-3">
              <option value="0 0 * * *">{t('series.form_daily')}</option>
              <option value="0 0 * * 1">{t('series.form_weekly')}</option>
              <option value="0 0 1,15 * *">{t('series.form_biweekly')}</option>
              <option value="0 0 1 * *">{t('series.form_monthly')}</option>
            </Form.Select>
          </Form.Group>
          <div className="d-flex gap-2 mt-3">
            <Button variant="outline-secondary" onClick={onClose} className="rounded-pill flex-fill">{t('common.cancel')}</Button>
            <Button type="submit" variant="primary" disabled={createMutation.isPending} className="rounded-pill flex-fill">
              {createMutation.isPending ? t('series.creating') : t('series.create')}
            </Button>
          </div>
        </Form>
      </Modal.Body>
    </Modal>
  );
}
