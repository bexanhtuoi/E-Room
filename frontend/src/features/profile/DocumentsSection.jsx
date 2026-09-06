import { useMutation, useQuery } from '@tanstack/react-query';
import { HiDocumentText } from 'react-icons/hi2';
import { fetchJson } from '../../lib/api';
import { queryClient } from '../../lib/queryClient';
import { formatDateTime } from '../../lib/formatters';

export function DocumentsSection({ userId }) {
  const docsQuery = useQuery({
    queryKey: ['documents', 'list'],
    queryFn: () => fetchJson('/documents/?limit=100'),
  });
  const all = Array.isArray(docsQuery.data) ? docsQuery.data : [];
  const mine = all.filter((d) => String(d.user_id) === String(userId));

  const delMutation = useMutation({
    mutationFn: (id) => fetchJson(`/documents/${id}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents', 'list'] }),
  });

  return (
    <section className="portal-panel">
      <div className="portal-panel__head">
        <h2>Documents</h2>
        <span className="portal-muted">{mine.length} files</span>
      </div>
      {docsQuery.isLoading && <p className="portal-muted">Loading documents…</p>}
      {docsQuery.isError && (
        <div className="er-alert er-alert--err">
          Could not load documents. <button type="button" onClick={() => docsQuery.refetch()} className="portal-linkbtn">Try again</button>
        </div>
      )}
      {!docsQuery.isLoading && !docsQuery.isError && mine.length === 0 && (
        <div className="portal-empty">No documents yet. Files attached to your learning will show up here.</div>
      )}
      {mine.length > 0 && (
        <div className="portal-list">
          {mine.map((d) => (
            <div key={d.id} className="portal-row">
              <span className="portal-fileicon"><HiDocumentText size={18} /></span>
              <span className="portal-row__main">
                <span className="portal-row__text">{d.file_name}</span>
                <span className="portal-row__sub">{d.file_type}{d.created_at ? ` · ${formatDateTime(d.created_at)}` : ''}</span>
              </span>
              <button
                type="button"
                className="er-btn er-btn--ghost portal-mini-btn"
                disabled={delMutation.isPending}
                onClick={() => { if (window.confirm(`Delete "${d.file_name}"?`)) delMutation.mutate(d.id); }}
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}
      {delMutation.isError && <div className="er-alert er-alert--err">Could not delete this document.</div>}
    </section>
  );
}
