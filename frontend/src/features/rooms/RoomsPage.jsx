import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { HiArrowPath, HiMagnifyingGlass } from 'react-icons/hi2';
import { Section, Eyebrow } from '../../components/common/UI';
import { RoomRow } from './RoomRow';
import { CreateRoomModal } from './CreateRoomModal';
import { sortRooms } from './roomSort';
import { fetchJson } from '../../lib/api';

const FILTERS = [
  { key: 'all', label: 'All rooms' },
  { key: 'active', label: 'Live now' },
  { key: 'idle', label: 'Open' },
  { key: 'ended', label: 'Ended' },
];

// So room hien moi window khi scroll (khop server pagination skip/limit)
const PAGE_WINDOW = 10;

export function RoomsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [visibleCount, setVisibleCount] = useState(PAGE_WINDOW);
  const sentinelRef = useRef(null);

  const { data: rooms, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['rooms', 'list'],
    queryFn: () => fetchJson('/rooms/?limit=100'),
    staleTime: 10_000,
    // List tuoi lien tuc: status doi (live/open/ended) thay ngay
    refetchInterval: 10_000,
  });

  const openRooms = useMemo(() => {
    let list = rooms || [];
    if (filter !== 'all') list = list.filter((r) => r.status === filter);
    const q = search.trim().toLowerCase();
    if (q) {
      list = list.filter((r) => {
        const haystack = [r.name, r.description, ...((Array.isArray(r.topics) ? r.topics : []))].filter(Boolean).join(' ').toLowerCase();
        return haystack.includes(q);
      });
    }
    // Live truoc, open sau, ended cuoi; moi trang thai moi nhat len dau
    return sortRooms(list);
  }, [rooms, filter, search]);

  // Doi filter/search → ve window dau
  useEffect(() => {
    setVisibleCount(PAGE_WINDOW);
  }, [filter, search]);

  // Scroll toi day → render them 1 window
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setVisibleCount((c) => (c < openRooms.length ? c + PAGE_WINDOW : c));
        }
      },
      { rootMargin: '400px' },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [openRooms.length, visibleCount]);

  const visibleRooms = openRooms.slice(0, visibleCount);

  function handleReload() {
    setVisibleCount(PAGE_WINDOW);
    refetch();
  }

  const liveCount = (rooms || []).filter((r) => r.status === 'active').length;
  const openCount = (rooms || []).filter((r) => r.status === 'idle').length;
  const endedCount = (rooms || []).filter((r) => r.status === 'ended').length;
  const topicCount = useMemo(() => {
    const set = new Set();
    (rooms || []).forEach((r) => (Array.isArray(r.topics) ? r.topics : []).forEach((t) => set.add(String(t).toLowerCase())));
    return set.size;
  }, [rooms]);

  function surpriseMe() {
    if (openRooms.length === 0) return;
    const pick = openRooms[Math.floor(Math.random() * openRooms.length)];
    navigate(`/rooms/${pick.id}`);
  }

  return (
    <div>
      <Section>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 20, flexWrap: 'wrap' }}>
          <div>
            <Eyebrow>Rooms</Eyebrow>
            <h1 style={{ fontSize: 'clamp(32px,4.6vw,54px)', lineHeight: 1.02, letterSpacing: '-0.02em', margin: '0 0 12px', color: '#000' }}>
              Pick a topic.<br />Take a seat.
            </h1>
            <p className="er-sub">Small tables, hot topics. See who is talking before you join.</p>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button className="er-btn er-btn--ghost" onClick={surpriseMe} disabled={openRooms.length === 0}>Surprise me →</button>
            <button className="er-btn" onClick={() => setShowCreate(true)}>+ Create room</button>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 0, marginTop: 28, border: '1px solid #111', maxWidth: 560 }}>
          {[
            [`${liveCount}`, 'live now'],
            [`${openCount}`, 'open'],
            [`${endedCount}`, 'ended'],
            [`${topicCount}`, 'topics live'],
          ].map(([v, l], i) => (
            <div key={l} style={{ flex: 1, padding: '14px 8px', textAlign: 'center', borderLeft: i ? '1px solid #e8e8e8' : 'none' }}>
              <div style={{ fontWeight: 800, fontSize: 20 }}>{v}</div>
              <div style={{ fontSize: 12, color: '#666' }}>{l}</div>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 8, marginTop: 24, flexWrap: 'wrap', alignItems: 'center' }}>
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              style={{ padding: '10px 16px', fontWeight: 800, fontSize: 13, cursor: 'pointer', background: filter === f.key ? '#111' : '#fff', color: filter === f.key ? '#fff' : '#111', border: '1px solid #111' }}
            >
              {f.label}
            </button>
          ))}
          <span style={{ marginLeft: 'auto', display: 'inline-flex', gap: 8, alignItems: 'center' }}>
            <button
              onClick={handleReload}
              title="Reload rooms"
              aria-label="Reload rooms"
              style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '10px 14px', fontWeight: 800, fontSize: 13, cursor: 'pointer', background: '#fff', color: '#111', border: '1px solid #111' }}
            >
              <HiArrowPath size={15} style={{ animation: isFetching ? 'er-spin 0.9s linear infinite' : 'none' }} />
              Reload
            </button>
            <span style={{ position: 'relative', maxWidth: 260, flex: 1, minWidth: 200, display: 'inline-block' }}>
              <HiMagnifyingGlass size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#999' }} />
              <input
                className="er-input"
                style={{ paddingLeft: 36 }}
                placeholder="Search topics…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </span>
          </span>
        </div>

        <div style={{ marginTop: 12 }}>
          {isLoading && <p style={{ color: '#666', padding: '32px 0' }}>Loading rooms…</p>}
          {isError && (
            <div className="er-alert er-alert--err" style={{ marginTop: 24 }}>
              Couldn't load rooms. The server may be starting — <button onClick={() => refetch()} style={{ fontWeight: 800, textDecoration: 'underline', background: 'none', border: 'none', cursor: 'pointer' }}>try again</button>.
            </div>
          )}
          {!isLoading && !isError && openRooms.length === 0 && (
            <div className="er-alert" style={{ marginTop: 24 }}>No rooms match. Clear filters or create the first one.</div>
          )}
          {!isLoading && !isError && openRooms.length > 0 && (
            <div style={{ borderTop: '2px solid #111' }}>
              {visibleRooms.map((r, i) => <RoomRow key={r.id} room={r} index={i} detailed />)}
              <div ref={sentinelRef} style={{ padding: '14px 0', textAlign: 'center', fontSize: 12, fontWeight: 700, color: '#666' }}>
                {visibleCount < openRooms.length
                  ? `Showing ${visibleRooms.length} of ${openRooms.length} — scroll for more…`
                  : `Showing all ${openRooms.length} rooms`}
              </div>
            </div>
          )}
        </div>
      </Section>

      {showCreate && (
        <CreateRoomModal
          onClose={() => setShowCreate(false)}
          onRoomCreated={(room) => {
            setShowCreate(false);
            // List phai thay phong moi ngay — khong doi cache 30s het han
            queryClient.invalidateQueries({ queryKey: ['rooms', 'list'] });
            navigate(`/rooms/${room.id}`);
          }}
        />
      )}
    </div>
  );
}
