import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { HiCalendarDays, HiUserCircle } from 'react-icons/hi2';
import { FaceStack } from '../../components/common/Faces';
import { STATUS_LABEL } from '../../data/site';
import { fetchJson } from '../../lib/api';

export function useRoomMembers(roomId) {
  return useQuery({
    queryKey: ['room-members', roomId],
    queryFn: async () => {
      // Nguoi DANG O TRONG phong (live) — khong phai lich su chat.
      // Backend da loai AI (ai_*) khoi set nay qua webhook.
      const data = await fetchJson(`/rooms/${roomId}/participants`).catch(() => null);
      const ids = [...(data?.participants || [])]
        .filter((id) => !String(id).startsWith('ai_'))
        .slice(0, 4);
      const users = await Promise.all(ids.map((id) => fetchJson(`/users/${id}`).catch(() => null)));
      return users.filter(Boolean);
    },
    staleTime: 5_000,
    // Cap nhat lien tuc: nguoi ra/vao thay ngay tren list
    refetchInterval: 5_000,
  });
}

export function useRoomHost(hostId) {
  return useQuery({
    queryKey: ['room-host', hostId],
    queryFn: () => fetchJson(`/users/${hostId}`).catch(() => null),
    enabled: !!hostId,
    staleTime: 300_000,
  });
}

export function formatRoomDate(iso) {
  if (!iso) return '';
  try {
    return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric' }).format(new Date(iso));
  } catch {
    return '';
  }
}

export function RoomRow({ room, index, detailed }) {
  const { data: members } = useRoomMembers(room.id);
  const { data: host } = useRoomHost(detailed ? room.host_id : null);
  const topics = Array.isArray(room.topics) ? room.topics : [];

  return (
    <Link
      to={`/rooms/${room.id}`}
      style={{ display: 'grid', gridTemplateColumns: '64px 1fr auto', gap: 20, padding: '26px 4px', borderBottom: '1px solid #e8e8e8', alignItems: 'center', textDecoration: 'none', color: '#111' }}
      className="er-room-row"
    >
      <span style={{ fontSize: 15, fontWeight: 800, color: '#999' }}>{String(index + 1).padStart(2, '0')}</span>
      <span>
        <span style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <strong style={{ fontSize: 21 }}>{room.name}</strong>
          <span style={{ fontSize: 12, fontWeight: 700, color: room.status === 'active' ? '#15803d' : '#666' }}>
            ● {STATUS_LABEL[room.status] || room.status}
          </span>
        </span>
        {room.description && (
          <span style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden', color: '#333', fontSize: 14, marginTop: 6 }}>
            {room.description}
          </span>
        )}
        {topics.length > 0 && (
          <span style={{ display: 'flex', gap: 6, marginTop: 10, flexWrap: 'wrap' }}>
            {topics.slice(0, 4).map((t) => (
              <span key={t} style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.06em', border: '1px solid #111', padding: '4px 8px', background: '#fff' }}>
                {t.toUpperCase()}
              </span>
            ))}
            {topics.length > 4 && <span style={{ fontSize: 11, fontWeight: 800, padding: '4px 8px', background: '#111', color: '#fff' }}>+{topics.length - 4}</span>}
          </span>
        )}
        <span style={{ display: 'flex', gap: 14, marginTop: 10, fontSize: 13, color: '#666', flexWrap: 'wrap', alignItems: 'center' }}>
          {detailed && host && (
            <span style={{ display: 'inline-flex', gap: 5, alignItems: 'center' }}><HiUserCircle size={14} /> Host {host.full_name}</span>
          )}
          {detailed && room.created_at && (
            <span style={{ display: 'inline-flex', gap: 5, alignItems: 'center' }}><HiCalendarDays size={14} /> {formatRoomDate(room.created_at)}</span>
          )}
          {!detailed && <span>{room.name}</span>}
        </span>
        <span style={{ display: 'block', marginTop: 12 }}>
          {members && members.length > 0 ? (
            <FaceStack names={members.map((m) => m.full_name)} size={30} />
          ) : (
            <span style={{ fontSize: 13, color: '#999' }}>Be the first to join →</span>
          )}
        </span>
      </span>
      <span style={{ fontSize: 28, fontWeight: 800 }} aria-hidden="true">→</span>
    </Link>
  );
}
