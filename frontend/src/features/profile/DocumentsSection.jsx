import { useMutation, useQuery } from '@tanstack/react-query';
import { HiDocumentText, HiFolderOpen } from 'react-icons/hi2';
import { fetchJson } from '../../lib/api';
import { queryClient } from '../../lib/queryClient';
import { formatDateTime } from '../../lib/formatters';

function docMeta(doc) {
  const bits = [doc.file_type];
  try {
    const meta = JSON.parse(doc.metadata_json || '{}');
    if (meta.chunks) bits.push(`${meta.chunks} chunks`);
    if (meta.language) bits.push(String(meta.language).toUpperCase());
  } catch {
    // metadata_json tuy chon, bo qua khi khong parse duoc
  }
  if (doc.created_at) bits.push(formatDateTime(doc.created_at));
  return bits.filter(Boolean).join(' · ');
}

export function DocumentsSection({ userId }) {
  const docsQuery = useQuery({
    queryKey: ['documents', 'list'],
    queryFn: () => fetchJson('/documents/?limit=100'),
  });
  const all = Array.isArray(docsQuery.data) ? docsQuery.data : [];
  const mine = all.filter((d) => String(d.user_id) === String(userId));

  const typeCount = new Map();
  for (const d of mine) typeCount.set(d.file_type || 'file', (typeCount.get(d.file_type || 'file') || 0) + 1);

  const delMutation = useMutation({
    mutationFn: (id) => fetchJson(`/documents/${id}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents', 'list'] }),
  });

  return (
    <div className="portal-stack">
      {mine.length > 0 && (
        <div className="portal-stats">
          <div className="portal-stat">
            <span className="portal-stat__tile"><HiFolderOpen size={20} /></span>
            <span className="portal-stat__body">
              <span className="portal-stat__value">{mine.length}</span>
              <span className="portal-stat__label">Documents</span>
              <span className="portal-stat__sub">{typeCount.size} file types</span>
            </span>
          </div>
          {[...typeCount.entries()].slice(0, 3).map(([type, count]) => (
            <div key={type} className="portal-stat">
              <span className="portal-stat__tile"><HiDocumentText size={20} /></span>
              <span className="portal-stat__body">
                <span className="portal-stat__value">{count}</span>
                <span className="portal-stat__label">{type}</span>
                <span className="portal-stat__sub">files</span>
              </span>
            </div>
          ))}
        </div>
      )}

      <section className="portal-panel">
        <div className="portal-panel__head"><h2>All files</h2></div>
        {docsQuery.isLoading && <div className="portal-skeleton"><span /><span /></div>}
        {docsQuery.isError && (
          <div className="er-alert er-alert--err">
            Could not load documents. <button type="button" onClick={() => docsQuery.refetch()} className="portal-linkbtn">Try again</button>
          </div>
        )}
        {!docsQuery.isLoading && !docsQuery.isError && mine.length === 0 && (
          <div className="portal-empty">
            <HiDocumentText size={28} />
            <span>No documents yet. Files attached to your learning will show up here.</span>
          </div>
        )}
        {mine.length > 0 && (
          <div className="portal-docgrid">
            {mine.map((d) => (
              <div key={d.id} className="portal-doc">
                <span className="portal-doc__icon"><HiDocumentText size={20} /></span>
                <span className="portal-doc__name">{d.file_name}</span>
                <div className="portal-doc__foot">
                  <span className="portal-muted">{docMeta(d)}</span>
                  <button
                    type="button"
                    className="er-btn er-btn--ghost portal-mini-btn"
                    disabled={delMutation.isPending}
                    onClick={() => { if (window.confirm(`Delete "${d.file_name}"?`)) delMutation.mutate(d.id); }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        {delMutation.isError && <div className="er-alert er-alert--err">Could not delete this document.</div>}
      </section>
    </div>
  );
}
