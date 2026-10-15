import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { HiAcademicCap } from 'react-icons/hi2';
import { fetchJson } from '../../lib/api';
import { SessionScoringView } from './SessionScoringView';

/**
 * Mục Assessment: chấm điểm phát âm + nhận xét AI ngay tại chỗ.
 * Mặc định session mới nhất, chọn lại được qua dropdown.
 * Scoring (nút Chấm điểm AI, 4 tiêu chí, Nhận xét AI, sửa câu, loa mẫu)
 * CHỈ nằm ở đây — trang Session không có scoring.
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
            Score each sentence, read AI feedback, and listen to the correct pronunciation.
          </div>
        </div>
        <HiAcademicCap size={40} aria-hidden="true" />
      </section>

      {mineQuery.isLoading ? (
        <section className="portal-panel"><div className="portal-skeleton"><span /><span /></div></section>
      ) : mineQuery.isError ? (
        <section className="portal-panel">
          <div className="er-alert er-alert--err">
            Could not load sessions. <button type="button" onClick={() => mineQuery.refetch()} className="portal-linkbtn">Try again</button>
          </div>
        </section>
      ) : sessions.length === 0 ? (
        <section className="portal-panel">
          <div className="portal-empty">No sessions yet — join a room and say a few sentences, then come back.</div>
        </section>
      ) : (
        <>
          {sessions.length > 1 && (
            <section className="portal-panel">
              <label className="pf-sessionpick">
                Session
                <select
                  className="pf-sessionpick__select"
                  aria-label="Choose session"
                  value={activeId || ''}
                  onChange={(e) => setPicked(Number(e.target.value) || null)}
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
