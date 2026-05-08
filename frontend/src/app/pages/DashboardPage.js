import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppShell } from '../AppShell';
import { useAuth } from '../AuthContext';
import { fetchJson } from '../../lib/api';
import { RoomCard } from '../../components/ui/RoomCard';
import { EmptyState } from '../../components/ui/EmptyState';
import { CardSkeleton } from '../../components/ui/Skeleton';

export function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('all');

  const fetchRooms = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const data = await fetchJson('/rooms');
      setRooms(Array.isArray(data) ? data : data?.items || []);
    } catch (err) {
      setError(err.message);
      setRooms([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchRooms(); }, [fetchRooms]);

  function handleSelectRoom(room) {
    navigate(`/rooms/${room.id}`);
  }

  const filteredRooms = filter === 'all'
    ? rooms
    : rooms.filter((r) => {
        const tags = r.tags || [];
        return tags.some((t) => (typeof t === 'string' ? t : t.name) === filter);
      });

  const activeCount = rooms.filter((r) => r.status === 'active').length;
  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });

  return (
    <AppShell>
      <div className="dashboard fade-in">
        <section className="dashboard-welcome">
          <div>
            <h1 className="dash-welcome-title">Welcome back, {user?.display_name || 'there'}</h1>
            <p className="dash-welcome-date">{today}</p>
          </div>
          <div className="dash-stats">
            <div className="dash-stat">
              <span className="dash-stat-value">{rooms.length}</span>
              <span className="dash-stat-label">Rooms</span>
            </div>
            <div className="dash-stat">
              <span className="dash-stat-value">{activeCount}</span>
              <span className="dash-stat-label">Live now</span>
            </div>
          </div>
        </section>

        <section className="dashboard-rooms">
          <div className="dash-rooms-header">
            <h2 className="dash-section-title">Speaking Rooms</h2>
            <button className="dash-create-btn" onClick={() => navigate('/dashboard')}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
              Create Room
            </button>
          </div>

          <div className="dash-filter-pills">
            <button className={`dash-filter-pill ${filter === 'all' ? 'active' : ''}`} onClick={() => setFilter('all')}>All</button>
            {[...new Set(rooms.flatMap((r) => (r.tags || []).map((t) => typeof t === 'string' ? t : t.name)))].slice(0, 6).map((tag) => (
              <button key={tag} className={`dash-filter-pill ${filter === tag ? 'active' : ''}`} onClick={() => setFilter(tag)}>{tag}</button>
            ))}
          </div>

          {error && (
            <div className="dash-error" role="alert">
              <p>{error}</p>
              <button onClick={fetchRooms}>Retry</button>
            </div>
          )}

          <div className="room-grid">
            {loading ? (
              Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />)
            ) : filteredRooms.length === 0 ? (
              <div className="room-grid-empty">
                <EmptyState
                  icon={
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="9" y1="21" x2="9" y2="9" /></svg>
                  }
                  title="No active rooms"
                  description="Be the first to start a speaking session. Create a room and invite others to join."
                  action={
                    <button className="dash-create-btn" onClick={() => navigate('/dashboard')}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
                      Create your first room
                    </button>
                  }
                />
              </div>
            ) : (
              filteredRooms.map((room) => (
                <RoomCard key={room.id} room={room} onClick={handleSelectRoom} />
              ))
            )}
          </div>
        </section>
      </div>

      <style>{`
        .dashboard {
          max-width: 1280px; margin: 0 auto; padding: 32px 24px;
          display: flex; flex-direction: column; gap: 32px;
        }
        .dashboard-welcome {
          display: flex; align-items: center; justify-content: space-between;
          flex-wrap: wrap; gap: 16px;
        }
        .dash-welcome-title {
          font-family: var(--font-display); font-size: 26px; font-weight: 700;
          color: var(--color-text-primary);
        }
        .dash-welcome-date {
          font-size: 13px; color: var(--color-text-muted); margin-top: 2px;
        }
        .dash-stats { display: flex; gap: 12px; }
        .dash-stat {
          display: flex; flex-direction: column; align-items: center;
          padding: 12px 20px; border-radius: var(--radius-lg);
          background: var(--color-bg-surface); border: 1px solid var(--color-border);
        }
        .dash-stat-value {
          font-family: var(--font-display); font-size: 22px; font-weight: 700;
          color: var(--color-accent);
        }
        .dash-stat-label { font-size: 11px; color: var(--color-text-muted); margin-top: 2px; }

        .dashboard-rooms { display: flex; flex-direction: column; gap: 16px; }
        .dash-rooms-header { display: flex; align-items: center; justify-content: space-between; }
        .dash-section-title {
          font-family: var(--font-display); font-size: 20px; font-weight: 600;
          color: var(--color-text-primary);
        }
        .dash-create-btn {
          display: flex; align-items: center; gap: 6px;
          padding: 8px 16px; border-radius: var(--radius-md);
          background: var(--color-accent); color: #fff;
          font-size: 13px; font-weight: 600; transition: all var(--transition-fast);
        }
        .dash-create-btn:hover { background: var(--color-accent-hover); transform: translateY(-1px); }

        .dash-filter-pills { display: flex; gap: 8px; flex-wrap: wrap; }
        .dash-filter-pill {
          padding: 5px 14px; border-radius: var(--radius-full);
          border: 1px solid var(--color-border);
          color: var(--color-text-secondary); font-size: 12px; font-weight: 500;
          transition: all var(--transition-fast);
        }
        .dash-filter-pill:hover { border-color: var(--color-accent); color: var(--color-accent); }
        .dash-filter-pill.active { background: var(--color-accent); color: #fff; border-color: var(--color-accent); }

        .dash-error {
          padding: 12px 16px; border-radius: var(--radius-md);
          background: var(--color-danger-muted); color: var(--color-danger);
          font-size: 13px; display: flex; align-items: center; gap: 12px;
        }
        .dash-error button {
          padding: 4px 12px; border-radius: var(--radius-sm);
          background: var(--color-danger); color: #fff; font-size: 12px; font-weight: 600;
        }

        .room-grid {
          display: grid;
          grid-template-columns: repeat(1, 1fr);
          gap: 16px;
        }
        .room-grid-empty { grid-column: 1 / -1; }

        @media (min-width: 640px) { .room-grid { grid-template-columns: repeat(2, 1fr); } }
        @media (min-width: 1024px) { .room-grid { grid-template-columns: repeat(3, 1fr); } }
      `}</style>
    </AppShell>
  );
}
