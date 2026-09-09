import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { HiAcademicCap, HiChatBubbleLeftRight } from 'react-icons/hi2';

export function AssessmentSection({ rooms, messagesByRoom }) {
  const practiced = useMemo(() => {
    const list = [];
    for (const room of rooms) {
      const mine = messagesByRoom.get(room.id) || [];
      if (mine.length > 0) list.push({ room, count: mine.length });
    }
    return list.sort((a, b) => b.count - a.count);
  }, [rooms, messagesByRoom]);

  const [roomId, setRoomId] = useState(null);
  const active = practiced.find((p) => String(p.room.id) === String(roomId)) || practiced[0] || null;
  const lines = active ? (messagesByRoom.get(active.room.id) || []) : [];

  return (
    <div className="portal-stack">
      <section className="pf-hero">
        <div className="pf-hero__body">
          <div className="pf-hero__hello">English assessment</div>
          <div className="pf-hero__title">Replay what you said, level up how you say it.</div>
          <div className="pf-hero__sub">
            Pick a room you spoke in, review your lines, then re-speak them.
            Automatic pronunciation and grammar scoring lands here next.
          </div>
        </div>
        <HiAcademicCap size={40} aria-hidden="true" />
      </section>

      {practiced.length === 0 ? (
        <section className="portal-panel">
          <div className="portal-empty">
            <HiChatBubbleLeftRight size={28} />
            <span>Speak in a room first — your lines will show up here to review.</span>
            <Link className="er-btn portal-mini-btn" style={{ textDecoration: 'none' }} to="/rooms">Find a room</Link>
          </div>
        </section>
      ) : (
        <div className="portal-grid2">
          <section className="portal-panel">
            <div className="portal-panel__head"><h2>Your rooms to review <span className="portal-count">{practiced.length}</span></h2></div>
            <div className="portal-list">
              {practiced.map(({ room, count }) => (
                <button
                  key={room.id}
                  type="button"
                  className={`portal-row portal-row--btn${active && active.room.id === room.id ? ' is-active' : ''}`}
                  onClick={() => setRoomId(room.id)}
                  aria-pressed={active && active.room.id === room.id}
                >
                  <span className="portal-row__main">
                    <span className="portal-row__text">{room.name}</span>
                    <span className="portal-row__sub">{count} your lines</span>
                  </span>
                  <span className="portal-table__num">{count}</span>
                </button>
              ))}
            </div>
          </section>

          <section className="portal-panel">
            <div className="portal-panel__head"><h2>{active ? active.room.name : 'Your lines'}</h2></div>
            {lines.length === 0 ? (
              <div className="portal-empty">Nothing said here yet.</div>
            ) : (
              <ul className="portal-lines">
                {lines.slice(0, 10).map((m) => (
                  <li key={m.id}><span>{m.text}</span></li>
                ))}
              </ul>
            )}
            {lines.length > 10 && <span className="portal-muted">+ {lines.length - 10} more lines</span>}
          </section>
        </div>
      )}
    </div>
  );
}
