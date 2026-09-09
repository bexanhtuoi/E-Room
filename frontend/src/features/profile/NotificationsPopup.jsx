import { useMutation, useQuery } from '@tanstack/react-query';
import { HiBell, HiTrash } from 'react-icons/hi2';
import { fetchJson } from '../../lib/api';
import { queryClient } from '../../lib/queryClient';
import { formatDateTime } from '../../lib/formatters';

const TYPE_LABEL = { match: 'MATCH', session: 'SESSION', review: 'REVIEW', system: 'SYSTEM' };

export function NotificationsPopup({ onClose }) {
  const notifQuery = useQuery({
    queryKey: ['notifications', 'mine'],
    queryFn: () => fetchJson('/notifications/?limit=50'),
  });
  const items = Array.isArray(notifQuery.data) ? notifQuery.data : [];
  const unread = items.filter((n) => !n.is_read);

  function refresh() {
    queryClient.invalidateQueries({ queryKey: ['notifications', 'mine'] });
  }

  const readMutation = useMutation({
    mutationFn: (ids) => Promise.all(ids.map((id) => fetchJson(`/notifications/${id}`, { method: 'PATCH', body: JSON.stringify({ is_read: true }) }))),
    onSuccess: refresh,
  });

  const delMutation = useMutation({
    mutationFn: (id) => fetchJson(`/notifications/${id}`, { method: 'DELETE' }),
    onSuccess: refresh,
  });

  return (
    <div className="pf-modal" onClick={onClose}>
      <div className="pf-modal__box" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Notifications">
        <div className="pf-modal__head">
          <div>
            <h3>Notifications {unread.length > 0 && <span className="portal-count">{unread.length} new</span>}</h3>
            <p className="portal-muted">Matches, recaps and reviews.</p>
          </div>
          <button type="button" className="pf-modal__close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        {unread.length > 0 && (
          <div className="portal-actions" style={{ marginBottom: 12 }}>
            <button
              type="button"
              className="er-btn er-btn--ghost portal-mini-btn"
              disabled={readMutation.isPending}
              onClick={() => readMutation.mutate(unread.map((n) => n.id))}
            >
              {readMutation.isPending ? 'Marking…' : 'Mark all read'}
            </button>
          </div>
        )}

        {notifQuery.isLoading && <div className="portal-skeleton"><span /><span /><span /></div>}
        {notifQuery.isError && (
          <div className="er-alert er-alert--err">
            Could not load notifications. <button type="button" onClick={() => notifQuery.refetch()} className="portal-linkbtn">Try again</button>
          </div>
        )}
        {!notifQuery.isLoading && !notifQuery.isError && items.length === 0 && (
          <div className="portal-empty">
            <HiBell size={28} />
            <span>All quiet. Room matches, recaps and reviews will notify you here.</span>
          </div>
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
                <button
                  type="button"
                  className="er-btn er-btn--ghost portal-mini-btn"
                  title="Delete notification"
                  aria-label={`Delete notification ${n.title}`}
                  disabled={delMutation.isPending}
                  onClick={() => delMutation.mutate(n.id)}
                >
                  <HiTrash size={13} />
                </button>
              </div>
            ))}
          </div>
        )}
        {(readMutation.isError || delMutation.isError) && (
          <div className="er-alert er-alert--err">Could not update notifications.</div>
        )}
      </div>
    </div>
  );
}
