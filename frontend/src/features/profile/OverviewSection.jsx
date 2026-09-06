import { Link } from 'react-router-dom';
import { HiArrowRight, HiPlusCircle } from 'react-icons/hi2';
import { formatDateTime } from '../../lib/formatters';
import { bucketByDay, WeekBars } from './WeekBars';

function greeting() {
  const h = new Date().getHours();
  if (h < 11) return 'Good morning';
  if (h < 14) return 'Good day';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

export function OverviewSection({ user, hostedRooms, joinedRooms, messages, documentsCount, onCreateRoom, onGo }) {
  const firstName = (user?.full_name || 'learner').split(' ')[0];
  const today = new Intl.DateTimeFormat('en', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date());
  const week = bucketByDay(messages, 7);
  const weekTotal = week.reduce((s, b) => s + b.count, 0);
  const recent = messages.slice(0, 5);
  const resume = [...joinedRooms, ...hostedRooms].find((r) => r.status === 'active') || [...joinedRooms, ...hostedRooms].find((r) => r.status === 'idle');

  const kpis = [
    { value: hostedRooms.length, label: 'Rooms hosted' },
    { value: joinedRooms.length, label: 'Rooms joined' },
    { value: messages.length, label: 'Messages' },
    { value: documentsCount, label: 'Documents' },
  ];

  return (
    <div className="portal-stack">
      <div className="portal-hero">
        <div>
          <div className="portal-hero__date">{today}</div>
          <h2>{greeting()}, {firstName}.</h2>
          <p>{weekTotal > 0 ? `${weekTotal} messages in the last 7 days — nice momentum.` : 'Say your first line this week — pick a room and jump in.'}</p>
        </div>
        <div className="portal-hero__actions">
          <button className="er-btn" onClick={onCreateRoom}><HiPlusCircle size={16} /> New room</button>
          <Link className="er-btn er-btn--ghost" style={{ textDecoration: 'none' }} to="/rooms">Find a room</Link>
        </div>
      </div>

      <div className="portal-stats is-4">
        {kpis.map((k) => (
          <div key={k.label} className="portal-stat">
            <div className="portal-stat__value">{k.value}</div>
            <div className="portal-stat__label">{k.label}</div>
          </div>
        ))}
      </div>

      <div className="portal-grid2">
        <section className="portal-panel">
          <div className="portal-panel__head"><h2>This week</h2><span className="portal-muted">{weekTotal} messages</span></div>
          <div className="portal-block">
            <WeekBars data={week} />
          </div>
          <div className="portal-block">
            <button type="button" className="portal-linkbtn" onClick={() => onGo?.('usage')}>Full usage report <HiArrowRight size={13} /></button>
          </div>
        </section>

        <section className="portal-panel">
          <div className="portal-panel__head"><h2>Continue learning</h2></div>
          {!resume ? (
            <div className="portal-empty">No open room right now. Create one and learners will join you.</div>
          ) : (
            <div className="portal-resume">
              <div>
                <strong>{resume.name}</strong>
                <span className="portal-muted">{resume.status === 'active' ? 'Live now — jump back in' : 'Open — waiting for speakers'}</span>
              </div>
              <Link className="er-btn portal-mini-btn" style={{ textDecoration: 'none' }} to={`/rooms/${resume.id}`}>Open</Link>
            </div>
          )}
          <div className="portal-block">
            <div className="portal-block__label">Latest messages</div>
            {recent.length === 0 ? (
              <p className="portal-muted">Nothing yet.</p>
            ) : (
              <ul className="portal-lines">
                {recent.map((m) => (
                  <li key={m.id}>
                    <span className="portal-muted">{m.created_at ? formatDateTime(m.created_at) : ''}</span>
                    <span className="portal-row__text">{m.text}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
