import { useMutation, useQuery } from '@tanstack/react-query';
import { fetchJson } from '../../lib/api';
import { queryClient } from '../../lib/queryClient';
import { formatDateTime } from '../../lib/formatters';

const TYPE_LABEL = { match: 'MATCH', session: 'SESSION', review: 'REVIEW', system: 'SYSTEM' };

export function NotificationsSection() {
  const notifQuery = useQuery({
    queryKey: ['notifications', 'mine'],
    queryFn: () => fetchJson('/notifications/?limit=50'),
  });
  const items = Array.isArray(notifQuery.data) ? notifQuery.data : [];
  const unread = items.filter((n) => !n.is_read);

  const readMutation = useMutation({
    mutationFn: (ids) => Promise.all(ids.map((id) => fetchJson(`/notifications/${id}`, { method: 'PATCH', body: JSON.stringify({ is_read: true }) }))),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications', 'mine'] }),
  });

  return (
    <section className="portal-panel">
      <div className="portal-panel__head">
        <h2>Notifications {unread.length > 0 && <span className="portal-count">{unread.length} new</span>}</h2>
        {unread.length > 0 && (
          <button type="button" className="er-btn er-btn--ghost portal-mini-btn" disabled={readMutation.isPending} onClick={() => readMutation.mutate(unread.map((n) => n.id))}>
            {readMutation.isPending ? 'Marking…' : 'Mark all read'}
          </button>
        )}
      </div>
      {notifQuery.isLoading && <p className="portal-muted">Loading notifications…</p>}
      {notifQuery.isError && (
        <div className="er-alert er-alert--err">
          Could not load notifications. <button type="button" onClick={() => notifQuery.refetch()} className="portal-linkbtn">Try again</button>
        </div>
      )}
      {!notifQuery.isLoading && !notifQuery.isError && items.length === 0 && (
        <div className="portal-empty">All quiet. Room matches, recaps and reviews will notify you here.</div>
      )}
      {items.length > 0 && (
        <div className="portal-list">
          {items.map((n) => (
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
