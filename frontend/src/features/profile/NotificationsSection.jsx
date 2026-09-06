import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { HiBell } from 'react-icons/hi2';
import { fetchJson } from '../../lib/api';
import { queryClient } from '../../lib/queryClient';
import { formatDateTime } from '../../lib/formatters';

const TYPE_LABEL = { match: 'MATCH', session: 'SESSION', review: 'REVIEW', system: 'SYSTEM' };

export function NotificationsSection() {
  const [tab, setTab] = useState('all');
  const notifQuery = useQuery({
    queryKey: ['notifications', 'mine'],
    queryFn: () => fetchJson('/notifications/?limit=50'),
  });
  const items = Array.isArray(notifQuery.data) ? notifQuery.data : [];
  const unread = items.filter((n) => !n.is_read);
  const shown = tab === 'unread' ? unread : items;

  const readMutation = useMutation({
    mutationFn: (ids) => Promise.all(ids.map((id) => fetchJson(`/notifications/${id}`, { method: 'PATCH', body: JSON.stringify({ is_read: true }) }))),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications', 'mine'] }),
  });

  return (
    <section className="portal-panel">
      <div className="portal-panel__head">
        <h2>Inbox {unread.length > 0 && <span className="portal-count">{unread.length} new</span>}</h2>
        <div className="portal-toolbar" style={{ justifyContent: 'flex-end' }}>
          <div className="portal-tabs" role="tablist" aria-label="Notification filter">
            {[{ key: 'all', label: `All (${items.length})` }, { key: 'unread', label: `Unread (${unread.length})` }].map((t) => (
              <button key={t.key} type="button" role="tab" aria-selected={tab === t.key} onClick={() => setTab(t.key)} className={`portal-tab${tab === t.key ? ' is-active' : ''}`}>
                {t.label}
              </button>
            ))}
          </div>
          {unread.length > 0 && (
            <button type="button" className="er-btn er-btn--ghost portal-mini-btn" disabled={readMutation.isPending} onClick={() => readMutation.mutate(unread.map((n) => n.id))}>
              {readMutation.isPending ? 'Marking…' : 'Mark all read'}
            </button>
          )}
        </div>
      </div>
      {notifQuery.isLoading && <div className="portal-skeleton"><span /><span /><span /></div>}
      {notifQuery.isError && (
        <div className="er-alert er-alert--err">
          Could not load notifications. <button type="button" onClick={() => notifQuery.refetch()} className="portal-linkbtn">Try again</button>
        </div>
      )}
      {!notifQuery.isLoading && !notifQuery.isError && shown.length === 0 && (
        <div className="portal-empty">
          <HiBell size={28} />
          <span>{tab === 'unread' ? 'Inbox zero. Everything is read.' : 'All quiet. Room matches, recaps and reviews will notify you here.'}</span>
        </div>
      )}
      {shown.length > 0 && (
        <div className="portal-list">
          {shown.map((n) => (
            <div key={n.id} className={`portal-row${n.is_read ? '' : ' is-unread'}`}>
              <span className="portal-badge">{TYPE_LABEL[n.notification_type] || 'INFO'}</span>
              <span className="portal-row__main">
                <span className="portal-row__text">{n.title}</span>
                {n.body && <span className="portal-row__sub">{n.body}</span>}
                <span className="portal-row__sub">{n.created_at ? formatDateTime(n.created_at) : ''}</span>
              </span>
              {!n.is_read && (
                <button
                  type="button"
                  className="er-btn er-btn--ghost portal-mini-btn"
                  disabled={readMutation.isPending}
                  onClick={() => readMutation.mutate([n.id])}
                >
                  Mark read
                </button>
              )}
            </div>
          ))}
        </div>
      )}
      {readMutation.isError && <div className="er-alert er-alert--err">Could not update notifications.</div>}
    </section>
  );
}
