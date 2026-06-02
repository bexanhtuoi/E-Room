import Button from 'react-bootstrap/Button';
import Spinner from 'react-bootstrap/Spinner';
import {
  HiMicrophone, HiSparkles, HiGlobeAlt, HiArrowRight, HiChatBubbleLeftRight,
  HiAcademicCap, HiShieldCheck, HiVideoCamera, HiCheckCircle, HiClock,
  HiUsers, HiBolt, HiDocumentText, HiSpeakerWave, HiBriefcase,
  HiPresentationChartLine, HiCpuChip, HiQueueList, HiChartBar,
} from 'react-icons/hi2';
import { RobotAvatar } from './icons';

const PREVIEW_PARTICIPANTS = [
  { name: 'You', label: 'Speaking', active: true, color: '#ffffff' },
  { name: 'Mina', label: 'B2 · Product', active: false, color: '#e0e0e0' },
  { name: 'Alex', label: 'C1 · AI/ML', active: false, color: '#f59e0b' },
  { name: 'Linh', label: 'B1 · Design', active: false, color: '#ec4899' },
];

const HERO_TRUST_ITEMS = [
  { icon: HiQueueList, label: 'Tag-based matching' },
  { icon: HiUsers, label: '3-5 people rooms' },
  { icon: HiCpuChip, label: 'AI Agent 3-in-1' },
];

function ProductPreview() {
  return (
    <div className="home-preview" aria-label="E-Room desktop product preview">
      <div className="home-preview__glow" />
      <div className="home-preview__browserbar">
        <div><i /><i /><i /></div>
        <span>eroom.app/rooms/vibe-coding</span>
        <strong>Pro Agent</strong>
      </div>
      <div className="home-preview__screen">
        <div className="home-preview__topbar">
          <div>
            <span className="home-preview__live">● ACTIVE · VIBE CODING</span>
            <h3>Claude + Product Thinking Practice</h3>
          </div>
          <div className="home-preview__meta">
            <span><HiClock size={13} /> 12:48</span>
            <span><HiUsers size={13} /> 4/5</span>
          </div>
        </div>

        <div className="home-preview__body">
          <div className="home-preview__stage">
            <div className="home-preview__video-grid">
              {PREVIEW_PARTICIPANTS.map((person) => (
                <div className={`home-preview__tile ${person.active ? 'is-speaking' : ''}`} key={person.name}>
                  <div className="home-preview__avatar" style={{ background: person.color }}>{person.name[0]}</div>
                  <div>
                    <strong>{person.name}</strong>
                    <span>{person.label}</span>
                  </div>
                  {person.active && <div className="home-preview__wave"><i /><i /><i /><i /></div>}
                </div>
              ))}
            </div>
            <div className="home-preview__timeline">
              <div><span>00:00</span><strong /><span>15:00</span></div>
              <p>Transcript streams while the agent prepares corrections, expert prompts, and review notes.</p>
            </div>
            <div className="home-preview__controls">
              <span><HiMicrophone size={16} /></span>
              <span><HiVideoCamera size={16} /></span>
              <span><HiChatBubbleLeftRight size={16} /></span>
              <span className="is-hot"><HiBolt size={16} /></span>
            </div>
          </div>

          <aside className="home-preview__coach">
            <div className="home-preview__coach-head">
              <RobotAvatar />
              <div>
                <strong>AI Agent 3-in-1</strong>
                <span>Corrector · Expert · Heartbeat</span>
              </div>
            </div>
            <div className="home-preview__transcript">
              <span>Live transcript</span>
              <p>“I use Claude for build faster product prototype.”</p>
            </div>
            <div className="home-preview__correction">
              <HiCheckCircle size={16} />
              <div>
                <span>Corrector</span>
                <strong>“I use Claude to build product prototypes faster.”</strong>
              </div>
            </div>
            <div className="home-preview__transcript">
              <span>Heartbeat prompt</span>
              <p>What tradeoff did Claude help you make?</p>
            </div>
            <div className="home-preview__score">
              <span>Session review</span>
              <strong>8.6</strong>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}

export function HeroSection({ user, onQuickJoin, quickJoining }) {
  return (
    <section className="home-hero position-relative overflow-hidden">
      <div className="home-hero__backdrop" />
      <div className="home-hero__inner">
        <div className="home-hero__copy fade-in-up">
          <div className="home-hero__eyebrow">
            <RobotAvatar />
            <span>Tag-matched rooms · AI Agent 3-in-1</span>
          </div>
          <h1 className="home-hero__title">
            Speak with people who share your topics. Improve with AI after every sentence.
          </h1>
          <p className="home-hero__subtitle">
            E-Room matches 3-5 learners by tags and level, opens a focused speaking room, and gives live transcript, corrections, expert prompts, pronunciation audio, and session review.
          </p>
          <div className="home-hero__actions">
            {user ? (
              <Button variant="primary" size="lg" className="rounded-pill fw-semibold px-5"
                onClick={onQuickJoin} disabled={quickJoining}
              >
                {quickJoining ? 'Finding a room...' : 'Quick Join Room'}
              </Button>
            ) : (
              <Button variant="primary" size="lg" className="rounded-pill fw-semibold px-5" href="/login">
                Start practicing free
              </Button>
            )}
            <Button variant="outline-secondary" size="lg" className="rounded-pill fw-semibold px-4" href="/learning">
              View live rooms <HiArrowRight size={16} />
            </Button>
          </div>
          <div className="home-hero__trust">
            {HERO_TRUST_ITEMS.map(item => (
              <span key={item.label}><item.icon size={15} />{item.label}</span>
            ))}
          </div>
        </div>
        <ProductPreview />
      </div>
    </section>
  );
}

export function ProblemSection() {
  const items = [
    ['Random partners', 'Most speaking apps pair people without context, so conversations die quickly.'],
    ['No feedback loop', 'You speak for 20 minutes but leave without knowing what to fix.'],
    ['Solo AI practice', 'Bots are useful, but they do not build the pressure and rhythm of real conversation.'],
  ];

  return (
    <section className="home-problem-section">
      <div className="home-section-heading">
        <span>The problem</span>
        <h2>Speaking practice fails when rooms have no context and feedback arrives too late.</h2>
      </div>
      <div className="home-problem-grid">
        {items.map(([title, desc], index) => (
          <article className="home-problem-card" key={title}>
            <strong>{String(index + 1).padStart(2, '0')}</strong>
            <h3>{title}</h3>
            <p>{desc}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export function PremiumFlowSection() {
  const steps = [
    { icon: HiQueueList, label: '01', title: 'Choose tags', desc: 'Pick interests like Vibe Coding, AI/ML, Prompt Engineering, or LLM topics.' },
    { icon: HiUsers, label: '02', title: 'Match into a room', desc: 'A small 3-5 person room forms around shared tags and nearby English level.' },
    { icon: HiMicrophone, label: '03', title: 'Speak in real time', desc: 'LiveKit handles the room while transcript appears in the side panel.' },
    { icon: HiSparkles, label: '04', title: 'Review with AI', desc: 'Corrector, Expert, and Heartbeat turn the session into a repeatable lesson.' },
  ];

  return (
    <section className="home-flow-section">
      <div className="home-section-heading home-section-heading--left">
        <span>Solution</span>
        <h2>Make every room purposeful before anyone turns on the mic.</h2>
        <p>Tags define the topic, level keeps the room comfortable, and the AI agent turns live conversation into reviewable progress.</p>
      </div>
      <div className="home-flow-grid">
        {steps.map((step) => (
          <article className="home-flow-card" key={step.title}>
            <div><step.icon size={22} /><span>{step.label}</span></div>
            <h3>{step.title}</h3>
            <p>{step.desc}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export function AgentSection() {
  const roles = [
    { label: 'Corrector', metric: 'Grammar', desc: 'Turns rough spoken sentences into cleaner phrases without interrupting the room.' },
    { label: 'Expert', metric: 'Context', desc: 'Adds topic-aware explanations when a room needs more depth or examples.' },
    { label: 'Heartbeat', metric: 'Momentum', desc: 'Keeps quiet rooms moving with AI-themed prompts based on tags and recent conversation.' },
  ];

  return (
    <section className="home-agent-section">
      <div className="home-agent-panel">
        <div className="home-agent-copy">
          <span>Guidance layer</span>
          <h2>Feedback appears beside the conversation, not on top of it.</h2>
          <p>E-Room keeps the video room focused on people. The assistant works in the side panel: listening, correcting, answering, and nudging only when it helps.</p>
        </div>
        <div className="home-agent-console">
          <div className="home-agent-console__top">
            <span>Session intelligence</span>
            <strong>Live</strong>
          </div>
          {roles.map(role => (
            <article key={role.label}>
              <div>
                <strong>{role.label}</strong>
                <span>{role.metric}</span>
              </div>
              <p>{role.desc}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

export function AudienceSection() {
  const audiences = [
    { icon: HiBriefcase, title: 'Tech interviews', desc: 'Explain AI projects, model tradeoffs, system architecture, and technical decisions.' },
    { icon: HiPresentationChartLine, title: 'Work meetings', desc: 'Practice standups, demos, client calls, and product discussions.' },
    { icon: HiAcademicCap, title: 'AI discussion', desc: 'Discuss LLMs, prompt engineering, and AI trends with real-time correction.' },
    { icon: HiGlobeAlt, title: 'Daily fluency', desc: 'Meet learners who care about the same topics and speak more often.' },
  ];

  return (
    <section className="home-audience-section">
      <div className="home-section-heading">
        <span>Use cases</span>
        <h2>Practice for the situations where English actually matters.</h2>
      </div>
      <div className="home-audience-grid">
        {audiences.map((item) => (
          <article className="home-audience-card" key={item.title}>
            <div className="home-audience-card__icon"><item.icon size={22} /></div>
            <div>
              <h3>{item.title}</h3>
              <p>{item.desc}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export function RoomsSection({ rooms = [], roomsLoading, navigate }) {
  return (
    <section className="home-rooms-section">
      <div className="home-section-heading">
        <span>Live rooms</span>
        <h2>Jump into active rooms or browse by topic.</h2>
      </div>
      {roomsLoading ? (
        <div className="text-center py-4"><Spinner animation="border" size="sm" /></div>
      ) : rooms.length === 0 ? (
        <p className="text-muted text-center py-4 small">No rooms available right now. Check back soon.</p>
      ) : (
        <div className="home-room-grid">
          {rooms.slice(0, 6).map((room) => (
            <button key={room.id} className="home-room-card" onClick={() => navigate(`/rooms/${room.id}`)}>
              <span>{room.status === 'ACTIVE' ? 'LIVE' : 'Waiting'}</span>
              <h3>{room.topic || room.name}</h3>
              <p>{room.current_participants || 0}/{room.max_participants || 5} participants</p>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

export function StatsSection() {
  const stats = [
    { value: '3-5', label: 'learners per room' },
    { value: '15m', label: 'focused sessions' },
    { value: '3-in-1', label: 'AI agent roles' },
    { value: '50+', label: 'tag categories' },
  ];

  return (
    <section className="home-stats-section">
      {stats.map((s) => (
        <div key={s.label}>
          <strong>{s.value}</strong>
          <span>{s.label}</span>
        </div>
      ))}
    </section>
  );
}

export function FinalShowcaseSection({ user, navigate }) {
  const quotes = [
    { quote: 'The room topics feel closer to my real work than a normal speaking class.', name: 'Minh Anh', role: 'Product Designer' },
    { quote: 'I can see the exact sentence I said, the better version, and what to repeat next.', name: 'Hoang Tran', role: 'Backend Engineer' },
    { quote: 'The AI prompts keep the conversation moving when everyone gets quiet.', name: 'Linh Pham', role: 'IELTS Learner' },
  ];

  return (
    <section className="home-final-section">
      <div className="home-final-header">
        <span><HiChartBar size={16} /> What our users say</span>
        <h2>Useful practice feels specific, not generic.</h2>
        <Button variant="primary" size="lg" className="rounded-pill fw-semibold px-5"
          onClick={() => navigate(user ? '/learning' : '/login')}
        >
          {user ? 'Find a room' : 'Start practicing'} <HiArrowRight size={16} />
        </Button>
      </div>
      <div className="home-testimonial-row">
        {quotes.map((item) => (
          <article key={item.name}>
            <p>“{item.quote}”</p>
            <strong>{item.name}</strong>
            <span>{item.role}</span>
          </article>
        ))}
      </div>
    </section>
  );
}
