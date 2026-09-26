import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { HiAcademicCap } from 'react-icons/hi2';
import { fetchJson } from '../../lib/api';
import { SessionScoringView } from './SessionScoringView';

/**
 * Mục Assessment (thay thế AssessmentSection cũ): chấm điểm + nhận xét AI
 * trên session — mặc định session mới nhất, chọn lại được.
 * Nội dung chấm điểm dùng chung SessionScoringView với trang session.
 */
export function SessionAssessmentSection() {
  const mineQuery = useQuery({
    queryKey: ['sessions', 'mine'],
    queryFn: () => fetchJson('/sessions/mine').then((r) => r?.sessions ?? []),
    retry: false,
  });
  const sessions = useMemo(
    () => (Array.isArray(mineQuery.data) ? mineQuery.data : []),
    [mineQuery.data],
  );
  const [picked, setPicked] = useState(null);
  const activeId = picked || sessions[0]?.session?.id || null;

  return (
    <div className="portal-stack">
      <section className="pf-hero">
        <div className="pf-hero__body">
          <div className="pf-hero__hello">English assessment</div>
          <div className="pf-hero__title">Replay what you said, level up how you say it.</div>
          <div className="pf-hero__sub">
            Chấm điểm phát âm từng câu, xem nhận xét AI và nghe lại mẫu đọc đúng.
          </div>
        </div>
        <HiAcademicCap size={40} aria-hidden="true" />
      </section>

      {mineQuery.isLoading ? (
        <section className="portal-panel"><div className="portal-skeleton"><span /><span /></div></section>
      ) : sessions.length === 0 ? (
        <section className="portal-panel">
          <div className="portal-empty">Chưa có session nào — vào phòng nói vài câu rồi quay lại.</div>
        </section>
      ) : (
        <>
          {sessions.length > 1 && (
            <section className="portal-panel">
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
                Session
                <select
                  aria-label="Choose session"
                  value={activeId || ''}
                  onChange={(e) => setPicked(Number(e.target.value) || null)}
                  style={{ border: '1px solid #111', padding: '4px 6px', fontSize: 13, cursor: 'pointer', background: '#fff' }}
                >
                  {sessions.map((s) => (
                    <option key={s.session.id} value={s.session.id}>
                      #{s.session.id} — {s.room?.name || `Room ${s.session.room_id}`} ({s.message_count ?? 0} lines)
                    </option>
                  ))}
                </select>
              </label>
            </section>
          )}
          {activeId && <SessionScoringView key={activeId} sessionId={String(activeId)} />}
        </>
      )}
    </div>
  );
}
