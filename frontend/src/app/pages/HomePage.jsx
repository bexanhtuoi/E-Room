import { useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { HiMicrophone, HiChatBubbleLeftRight, HiSpeakerWave, HiSparkles, HiClock, HiShieldCheck } from 'react-icons/hi2';
import { Section, Eyebrow, Card, FaqList, Container } from '../../components/common/UI';
import { Face } from '../../components/common/Faces';
import { RoomMock } from '../../components/room/RoomMock';
import { RoomRow } from '../../features/rooms/RoomRow';
import { sortRooms } from '../../features/rooms/roomSort';
import { FEATURES, HOW_STEPS, TESTIMONIALS, FAQS, HERO_STATS, SITE } from '../../data/site';
import { fetchJson } from '../../lib/api';

const FEATURE_ICONS = [HiChatBubbleLeftRight, HiSparkles, HiMicrophone, HiChatBubbleLeftRight, HiClock, HiShieldCheck];

function ReviewWheel({ items }) {
  const trackRef = useRef(null);
  const [index, setIndex] = useState(0);

  function goTo(i) {
    const el = trackRef.current;
    if (!el) return;
    const next = Math.max(0, Math.min(items.length - 1, i));
    el.scrollTo({ left: next * el.clientWidth, behavior: 'smooth' });
  }

  function onWheel(e) {
    const el = trackRef.current;
    if (!el) return;
    if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
      e.preventDefault();
      el.scrollLeft += e.deltaY;
    }
  }

  function onScroll() {
    const el = trackRef.current;
    if (!el || !el.clientWidth) return;
    setIndex(Math.round(el.scrollLeft / el.clientWidth));
  }

  return (
    <div style={{ marginTop: 36 }}>
      <div
        ref={trackRef}
        onWheel={onWheel}
        onScroll={onScroll}
        className="er-wheel"
        style={{ display: 'flex', overflowX: 'auto', scrollSnapType: 'x mandatory', scrollbarWidth: 'none' }}
      >
        {items.map((t) => (
          <div key={t.name} style={{ flex: '0 0 100%', scrollSnapAlign: 'center', padding: '12px 4px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 28, alignItems: 'start', maxWidth: 900, margin: '0 auto' }} className="er-review-slide">
              <Face name={t.name} size={96} variant={t.face} />
              <div>
                <div style={{ fontSize: 64, lineHeight: 0.6, fontWeight: 800, color: '#111' }}>“</div>
                <p style={{ fontSize: 'clamp(20px,2.8vw,30px)', lineHeight: 1.45, fontWeight: 700, color: '#000', margin: '12px 0 0' }}>{t.quote}</p>
                <p style={{ marginTop: 18, fontSize: 15 }}><strong>{t.name}</strong> <span style={{ color: '#666' }}>• {t.role}</span> <span style={{ color: '#111', fontWeight: 800 }}>★★★★★</span></p>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16, marginTop: 24 }}>
        <button className="er-btn er-btn--ghost" style={{ padding: '10px 18px' }} onClick={() => goTo(index - 1)} disabled={index === 0} aria-label="Previous review">←</button>
        <span style={{ display: 'flex', gap: 8 }}>
          {items.map((t, i) => (
            <button key={t.name} onClick={() => goTo(i)} aria-label={`Review ${i + 1}`} style={{ width: i === index ? 28 : 10, height: 10, background: i === index ? '#111' : '#ddd', border: 'none', cursor: 'pointer', padding: 0 }} />
          ))}
        </span>
        <button className="er-btn er-btn--ghost" style={{ padding: '10px 18px' }} onClick={() => goTo(index + 1)} disabled={index === items.length - 1} aria-label="Next review">→</button>
      </div>
      <p style={{ textAlign: 'center', color: '#999', fontSize: 12, marginTop: 12 }}>Scroll or use arrows — {index + 1} / {items.length}</p>
    </div>
  );
}

function RoomsSection() {
  const { data: rooms, isLoading, isError } = useQuery({
    queryKey: ['rooms', 'home'],
    queryFn: () => fetchJson('/rooms/?limit=10'),
    staleTime: 10_000,
    refetchInterval: 10_000,
  });

  const openRooms = sortRooms((rooms || []).filter((r) => r.status !== 'ended')).slice(0, 4);

  return (
    <Section soft id="rooms">
      <Eyebrow>Find your room</Eyebrow>
      <h2 className="er-h2">Rooms for every obsession.</h2>
      <p className="er-sub">Live topics right now — pulled straight from open rooms. See who is talking before you join.</p>
      {isLoading && <p style={{ marginTop: 32, color: '#666' }}>Loading open rooms…</p>}
      {isError && <div className="er-alert er-alert--err" style={{ marginTop: 32 }}>Could not load rooms. Please refresh or try again later.</div>}
      {!isLoading && !isError && openRooms.length === 0 && <div className="er-alert" style={{ marginTop: 32 }}>No open rooms right now — check back soon.</div>}
      {!isLoading && !isError && openRooms.length > 0 && (
        <div style={{ marginTop: 36, borderTop: '2px solid #111' }}>
          {openRooms.map((r, i) => <RoomRow key={r.id} room={r} index={i} detailed />)}
        </div>
      )}
        <p style={{ marginTop: 20, color: '#666', fontSize: 14 }}>New topics open every week. Small tables — everyone talks.</p>
    </Section>
  );
}

const TICKER_TOPICS = ['AI Agents', 'Digital Art', 'Startups', 'Cinema', 'Tech News', 'Music', 'Photography', 'Indie Hacking', 'Design', 'Culture'];

export function HomePage() {
  const navigate = useNavigate();
  const [matching, setMatching] = useState(false);
  const [matchNote, setMatchNote] = useState('');

  async function quickMatch() {
    setMatching(true);
    setMatchNote('');
    try {
      const res = await fetchJson('/rooms/match', { method: 'POST', body: JSON.stringify({}) });
      if (res?.room?.id) navigate(`/rooms/${res.room.id}`);
      else setMatchNote('No open rooms right now — browse below or create one.');
    } catch (err) {
      const msg = String(err?.message || '');
      if (msg.includes('404') || msg.toLowerCase().includes('no open rooms')) {
        setMatchNote('No open rooms right now — browse below or create one.');
      } else {
        navigate('/login');
      }
    } finally {
      setMatching(false);
    }
  }

  return (
    <div>
      {/* HERO — full screen, text trên hình dưới */}
      <Section>
        <div className="er-center">
          <Eyebrow>Topic video rooms + AI companion</Eyebrow>
          <h1 className="er-title">Meet people.<br />Talk ideas.</h1>
          <p className="er-lead">Small video rooms about the topics you love — AI agents, art, startups, cinema. An AI companion transcribes, answers @ai questions and recaps every session.</p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginTop: 28, flexWrap: 'wrap' }}>
            <button className="er-btn" onClick={quickMatch} disabled={matching}>{matching ? 'Finding a room…' : 'Quick match →'}</button>
            <a className="er-btn er-btn--ghost" href="#rooms">Browse rooms</a>
          </div>
          {matchNote && <p style={{ marginTop: 12, fontSize: 13, fontWeight: 700 }}>{matchNote}</p>}
          <div style={{ display: 'flex', gap: 0, justifyContent: 'center', marginTop: 26, border: '1px solid #111', maxWidth: 680, marginLeft: 'auto', marginRight: 'auto' }}>
            {HERO_STATS.map((s, i) => (
              <div key={s.label} style={{ flex: 1, padding: '16px 8px', borderLeft: i ? '1px solid #e8e8e8' : 'none', background: '#fff' }}>
                <div style={{ fontWeight: 800, fontSize: 22, color: '#000' }}>{s.value}</div>
                <div style={{ fontSize: 12, color: '#666' }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>
        <div style={{ marginTop: 48 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
            <strong style={{ fontSize: 14 }}>● LIVE PREVIEW — inside a real E-Room session</strong>
            <span className="er-tag">4 members • one shared chat</span>
          </div>
          <RoomMock />
          <p style={{ textAlign: 'center', color: '#666', fontSize: 13, marginTop: 12 }}>Video grid on the left, one shared chat on the right — transcripts and @ai answers together. Detailed feedback lives in your session history.</p>
        </div>
      </Section>

      {/* FEATURES */}
      <Section soft id="features">
        <Eyebrow>Everything you need</Eyebrow>
        <h2 className="er-h2">One room. Transcript.<br />Recap.</h2>
        <p className="er-sub">No classrooms and no silent audiences. Every feature below works inside the same live room — join once and use them all.</p>
        <div className="er-grid er-grid--3" style={{ marginTop: 36 }}>
          {FEATURES.map((f, i) => {
            const Icon = FEATURE_ICONS[i % FEATURE_ICONS.length];
            return (
              <Card key={f.title} style={{ padding: 28 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ width: 46, height: 46, border: '1px solid #111', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: '#f7f7f7' }}><Icon size={22} /></span>
                  <span className="er-num">{String(i + 1).padStart(2, '0')}</span>
                </div>
                <h3 style={{ fontSize: 21 }}>{f.title}</h3>
                <p>{f.desc}</p>
                <ul style={{ margin: '16px 0 0', paddingLeft: 18, fontSize: 14, color: '#333', display: 'grid', gap: 8 }}>
                  {f.points.map((p) => <li key={p}>{p}</li>)}
                </ul>
                <div style={{ marginTop: 18, paddingTop: 14, borderTop: '1px solid #e8e8e8', fontSize: 13, fontWeight: 700 }}>
                  <Link to="/login" style={{ color: '#111' }}>Try it in a room →</Link>
                </div>
              </Card>
            );
          })}
        </div>
      </Section>

      {/* HOW IT WORKS */}
      <Section id="how">
        <Eyebrow>How it works</Eyebrow>
        <h2 className="er-h2">Your first room<br />in 4 steps.</h2>
        <p className="er-sub">A fixed room routine keeps every session focused: warm-up, discussion, wrap-up. The timer is always visible, so nobody stays silent for long.</p>
        <div className="er-grid er-grid--4" style={{ marginTop: 36 }}>
          {HOW_STEPS.map((s) => (
            <Card key={s.num} style={{ padding: 26 }}>
              <span className="er-num">{s.num}</span>
              <h3>{s.title}</h3>
              <p>{s.desc}</p>
            </Card>
          ))}
        </div>
        <div style={{ marginTop: 28, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <Link className="er-btn" to="/login">Try a room now →</Link>
          <Link className="er-btn er-btn--ghost" to="/pricing">Compare plans</Link>
        </div>
      </Section>

      <RoomsSection />

      {/* VOICES — scroll wheel, one review per view */}
      <Section>
        <div className="er-center">
          <Eyebrow>Voices</Eyebrow>
          <h2 className="er-h2">People keep<br />coming back.</h2>
          <p className="er-sub" style={{ marginTop: 10 }}>4.8/5 average from 2,300+ reviews — hosts, regulars and first-timers.</p>
        </div>
        <ReviewWheel items={TESTIMONIALS} />
      </Section>

      {/* FAQ */}
      <Section soft id="faq">
        <div style={{ maxWidth: 820 }}>
          <Eyebrow>FAQ</Eyebrow>
          <h2 className="er-h2">Common questions.</h2>
          <p className="er-sub">Everything about rooms, AI and plans. Still curious? Email <strong style={{ color: '#111' }}>{SITE.supportEmail}</strong> or call <strong style={{ color: '#111' }}>{SITE.hotline}</strong> ({SITE.hotlineHours}).</p>
          <div style={{ marginTop: 24 }}><FaqList items={FAQS} /></div>
        </div>
      </Section>

      {/* CTA */}
      <Section>
        <Container>
          <div style={{ background: '#111', color: '#fff', padding: 'clamp(36px,6vw,72px)', display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 40, alignItems: 'center' }} className="er-cta-grid">
            <div>
              <Eyebrow>Open seats tonight</Eyebrow>
              <h2 style={{ fontSize: 'clamp(32px,4.6vw,56px)', lineHeight: 1.02, letterSpacing: '-0.02em', margin: '0 0 14px' }}>Your next conversation is 30 seconds away.</h2>
              <p style={{ color: '#bbb', maxWidth: 480, margin: '0 0 8px' }}>Pick a topic. Take a seat. Say hi — the room and the AI do the rest.</p>
              <ol style={{ color: '#ddd', fontSize: 14, paddingLeft: 20, display: 'grid', gap: 6, margin: '16px 0 26px' }}>
                <li>Choose one of tonight's open rooms</li>
                <li>Turn on mic — 4 seats, everyone talks</li>
                <li>Leave with a transcript + recap</li>
              </ol>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                <Link className="er-btn" style={{ background: '#fff', color: '#111', borderColor: '#fff' }} to="/login">Claim a seat →</Link>
                <Link className="er-btn er-btn--ghost" style={{ borderColor: '#fff', color: '#fff', background: 'transparent' }} to="/pricing">See pricing</Link>
              </div>
              <p style={{ color: '#888', fontSize: 12, marginTop: 16 }}>Free forever tier • No credit card • 50,000+ members</p>
            </div>
            <div style={{ border: '1px solid #fff', padding: 24 }}>
              <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.14em', color: '#bbb' }}>TONIGHT'S TOPICS</div>
              <div style={{ overflow: 'hidden', marginTop: 12, borderTop: '1px solid #333' }}>
                <div className="er-ticker">
                  {[...TICKER_TOPICS, ...TICKER_TOPICS].map((t, i) => (
                    <span key={`${t}-${i}`} style={{ display: 'flex', justifyContent: 'space-between', padding: '11px 0', borderBottom: '1px solid #333', fontSize: 15, fontWeight: 700, whiteSpace: 'nowrap' }}>
                      <span>{t}</span><span style={{ color: '#888' }}>● open</span>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </Container>
      </Section>
    </div>
  );
}
