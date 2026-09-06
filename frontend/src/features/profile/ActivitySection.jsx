import { Link } from 'react-router-dom';
import { formatDateTime } from '../../lib/formatters';

export function ActivitySection({ messages, isLoading, isError, onRetry }) {
  return (
    <section className="portal-panel">
      <div className="portal-panel__head">
        <h2>Activity</h2>
        <span className="portal-muted">{messages.length} messages</span>
      </div>
      {isLoading && <p className="portal-muted">Loading activity…</p>}
      {isError && (
        <div className="er-alert er-alert--err">
          Could not load activity. <button type="button" onClick={onRetry} className="portal-linkbtn">Try again</button>
        </div>
      )}
      {!isLoading && !isError && messages.length === 0 && (
        <div className="portal-empty">No messages yet. Join a room and everything you say will appear here.</div>
      )}
      {!isLoading && !isError && messages.length > 0 && (
        <div className="portal-list">
          {messages.map((m) => (
            <Link key={m.id} to={`/rooms/${m.room_id}`} className="portal-row">
              <span className={`portal-badge${m.role === 'ai' ? ' is-ai' : ''}`}>{m.role === 'ai' ? 'AI' : 'YOU'}</span>
              <span className="portal-row__main">
                <span className="portal-row__text">{m.text}</span>
                <span className="portal-row__sub">{m.created_at ? formatDateTime(m.created_at) : ''}</span>
              </span>
              <span className="portal-row__go" aria-hidden="true">→</span>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
