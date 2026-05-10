import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Card from 'react-bootstrap/Card';
import Button from 'react-bootstrap/Button';
import Spinner from 'react-bootstrap/Spinner';
import Badge from 'react-bootstrap/Badge';
import Form from 'react-bootstrap/Form';
import {
  HiHome, HiAcademicCap, HiUserGroup, HiLightBulb, HiShieldCheck,
  HiTrophy, HiGlobeAlt, HiSparkles, HiArrowRight, HiPlayCircle,
  HiClock, HiUser, HiStar, HiChartBar, HiHeart, HiCheckCircle,
  HiVideoCamera, HiMicrophone, HiChatBubbleLeftRight, HiRocketLaunch,
  HiPuzzlePiece, HiMagnifyingGlass, HiBolt, HiEnvelope
} from 'react-icons/hi2';
import { FiCheck } from 'react-icons/fi';
import { useAuth } from '../AuthContext';
import { fetchJson } from '../../lib/api';

function FeatureCard({ icon: Icon, title, description, delay = 0 }) {
  return (
    <Col md={4} className="mb-4">
      <Card className="h-100 border-0 shadow-sm text-center p-3 feature-card fade-in-up"
        style={{ animationDelay: `${delay}s` }}>
        <Card.Body>
          <div className="feature-icon-circle d-inline-flex align-items-center justify-content-center rounded-3 mb-3"
            style={{ width: 56, height: 56 }}>
            <Icon size={28} style={{ color: 'var(--color-accent)' }} />
          </div>
          <Card.Title className="fw-bold fs-5">{title}</Card.Title>
          <Card.Text className="text-muted small">{description}</Card.Text>
        </Card.Body>
      </Card>
    </Col>
  );
}

function RoomCard({ room }) {
  const statusMap = {
    ACTIVE: { variant: 'success', label: 'Live', icon: HiPlayCircle, color: 'var(--color-success)' },
    IDLE: { variant: 'info', label: 'Waiting', icon: HiClock, color: 'var(--color-text-muted)' },
    END: { variant: 'secondary', label: 'Ended', icon: HiClock, color: 'var(--color-text-muted)' },
  };
  const status = statusMap[room.status] || statusMap.IDLE;
  const StatusIcon = status.icon;
  return (
    <Card className="h-100 border-0 shadow-sm room-card fade-in">
      <Card.Body className="d-flex flex-column p-3">
        <div className="d-flex justify-content-between align-items-start mb-2">
          <div className="d-flex align-items-center gap-2">
            <StatusIcon size={16} style={{ color: status.color }} />
            <Card.Title className="fw-bold mb-0 fs-6">{room.topic || room.name || 'Untitled'}</Card.Title>
          </div>
          <Badge bg={status.variant} pill style={{ fontSize: '0.6rem' }}>{status.label}</Badge>
        </div>
        <Card.Text className="text-muted small mb-3 flex-grow-1">{room.description || 'Join this room.'}</Card.Text>
        <div className="d-flex flex-wrap gap-1 mb-2">
          {room.tags?.slice(0, 2).map(tag => (
            <span key={tag} className="rounded-pill fw-medium"
              style={{ display: 'inline-block', padding: '0.25em 0.65em', background: 'var(--color-accent-muted)', color: 'var(--color-accent)', fontSize: '0.65rem', fontWeight: 600 }}>
              #{tag}
            </span>
          ))}
        </div>
        <div className="d-flex justify-content-between align-items-center mt-auto pt-2 border-top"
          style={{ borderColor: 'var(--color-border)' }}>
          <small className="text-muted d-flex align-items-center gap-1">
            <HiUser size={14} /> {room.current_participants || 0}/{room.max_participants || 5}
          </small>
          <Link to={`/rooms/${room.id}`}>
            <Button variant="outline-primary" size="sm" className="rounded-pill px-3 fw-semibold">Join</Button>
          </Link>
        </div>
      </Card.Body>
    </Card>
  );
}

function CounterStat({ icon: Icon, value, label, suffix = '', delay = 0 }) {
  const [count, setCount] = useState(0);
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        let start = 0;
        const end = value;
        const duration = 1500;
        const startTime = Date.now();
        const tick = () => {
          const elapsed = Date.now() - startTime;
          const progress = Math.min(elapsed / duration, 1);
          const eased = 1 - Math.pow(1 - progress, 3);
          setCount(Math.floor(eased * end));
          if (progress < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
        observer.unobserve(el);
      }
    }, { threshold: 0.3 });
    observer.observe(el);
    return () => observer.disconnect();
  }, [value]);

  return (
    <Col xs={6} md={3} className="mb-3" ref={ref}>
      <Card className="h-100 border-0 shadow-sm text-center p-3 stat-card scale-in"
        style={{ animationDelay: `${delay}s` }}>
        <Card.Body>
          <Icon size={24} className="mb-2" style={{ color: 'var(--color-accent)' }} />
          <div className="fw-extrabold display-6 mb-0" style={{ fontFamily: 'Nunito, sans-serif', color: 'var(--color-text-primary)', lineHeight: 1 }}>
            {count.toLocaleString()}{suffix}
          </div>
          <small className="text-muted">{label}</small>
        </Card.Body>
      </Card>
    </Col>
  );
}

function TestimonialCard({ quote, name, role, avatar, delay = 0 }) {
  return (
    <Col md={6} lg={3} className="mb-4">
      <Card className="h-100 border-0 shadow-sm testimonial-card fade-in-up"
        style={{ animationDelay: `${delay}s` }}>
        <Card.Body className="d-flex flex-column p-4">
          <div className="d-flex gap-1 mb-3">
            {[...Array(5)].map((_, i) => (
              <HiStar key={i} size={14} style={{ color: 'var(--color-warning)' }} />
            ))}
          </div>
          <p className="text-muted flex-grow-1" style={{ fontSize: '0.85rem', fontStyle: 'italic', lineHeight: 1.7 }}>
            "{quote}"
          </p>
          <div className="d-flex align-items-center gap-3 mt-3 pt-3 border-top" style={{ borderColor: 'var(--color-border)' }}>
            <div className="rounded-circle d-flex align-items-center justify-content-center flex-shrink-0"
              style={{
                width: 40, height: 40,
                background: 'var(--color-accent-gradient)',
                color: '#fff', fontWeight: 700, fontSize: '0.85rem'
              }}>
              {avatar}
            </div>
            <div>
              <div className="fw-bold" style={{ fontSize: '0.85rem', color: 'var(--color-text-primary)' }}>{name}</div>
              <small className="text-muted">{role}</small>
            </div>
          </div>
        </Card.Body>
      </Card>
    </Col>
  );
}

const STEP_ITEMS = [
  { icon: HiPuzzlePiece, title: 'Choose Your Level', desc: 'Select your English level and interests so we can match you with the right rooms.' },
  { icon: HiMagnifyingGlass, title: 'Find a Room', desc: 'Browse topic-based rooms or use Quick Match to get paired instantly with learners.' },
  { icon: HiVideoCamera, title: 'Join & Speak', desc: 'Enter a live video room, start speaking, and get real-time AI feedback on your English.' },
  { icon: HiChartBar, title: 'Track Progress', desc: 'Review your AI feedback, track improvement over time, and unlock new levels.' },
];

const TESTIMONIALS = [
  { quote: 'E-Room helped me go from shy to confident in just 3 months. The AI feedback is incredibly accurate!', name: 'Minh Trang', role: 'IELTS 7.5 · Member since 2025', avatar: 'MT' },
  { quote: 'The smart matching paired me with people at exactly my level. No more awkward conversations!', name: 'John Park', role: 'Software Engineer · Korea', avatar: 'JP' },
  { quote: 'I love how the rooms are structured. Every session has a clear goal and the moderators are fantastic.', name: 'Linh Chi', role: 'University Student · Vietnam', avatar: 'LC' },
  { quote: 'As a teacher, I use E-Room with my students. The progress tracking is a game-changer.', name: 'Sarah Chen', role: 'ESL Teacher · Singapore', avatar: 'SC' },
];

export function HomePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [quickJoining, setQuickJoining] = useState(false);
  const [rooms] = useState([
    { id: '1', topic: 'Beginner Friendly Chat', description: 'Relaxed English for beginners about daily life.', status: 'ACTIVE', current_participants: 3, max_participants: 5, tags: ['beginner', 'daily'] },
    { id: '2', topic: 'Business English Pro', description: 'Professional vocabulary, presentations, meetings.', status: 'ACTIVE', current_participants: 4, max_participants: 4, tags: ['business', 'advanced'] },
    { id: '3', topic: 'IELTS Speaking Prep', description: 'Mock IELTS speaking tests with peer feedback.', status: 'IDLE', current_participants: 2, max_participants: 3, tags: ['ielts', 'exam'] },
    { id: '4', topic: 'Tech Talk & Trends', description: 'AI, software dev, tech industry news in English.', status: 'ACTIVE', current_participants: 5, max_participants: 6, tags: ['technology', 'ai-ml'] },
    { id: '5', topic: 'Casual Weekend Vibes', description: 'Chat about hobbies, travel, food, music.', status: 'IDLE', current_participants: 0, max_participants: 8, tags: ['casual', 'travel'] },
    { id: '6', topic: 'Pronunciation Perfection', description: 'Accent reduction, intonation, clear speech.', status: 'ACTIVE', current_participants: 2, max_participants: 3, tags: ['pronunciation', 'accent'] },
  ]);

  async function handleQuickJoin() {
    if (!user) { navigate('/login'); return; }
    setQuickJoining(true);
    try {
      const roomsData = await fetchJson('/rooms');
      const active = roomsData.filter(r =>
        (r.status === 'ACTIVE' || r.status === 'IDLE')
        && r.current_participants < r.max_participants
      );
      if (active.length > 0) {
        const pick = active[Math.floor(Math.random() * active.length)];
        navigate(`/rooms/${pick.id}`);
      } else {
        navigate('/learning');
      }
    } catch {
      navigate('/learning');
    } finally {
      setQuickJoining(false);
    }
  }

  return (
    <div className="home-page fade-in" style={{ minHeight: '100vh' }}>

      <section className="hero-section py-5"
        style={{ background: 'linear-gradient(180deg, var(--color-bg-elevated) 0%, var(--color-bg) 100%)' }}>
        <Container>
          <div className="text-center mx-auto" style={{ maxWidth: 720 }}>
            <div className="d-inline-flex align-items-center gap-2 px-3 py-1 rounded-pill mb-3"
              style={{ background: 'var(--color-accent-muted)' }}>
              <HiSparkles size={16} style={{ color: 'var(--color-accent)' }} />
              <small className="fw-semibold" style={{ color: 'var(--color-accent)' }}>AI-Powered English Practice</small>
            </div>
            <h1 className="display-4 fw-extrabold mb-3" style={{ fontFamily: 'Nunito, sans-serif' }}>
              Speak English,<br />
              <span className="gradient-text">Connect Globally</span>
            </h1>
            <p className="lead text-muted mb-4" style={{ maxWidth: 560, marginLeft: 'auto', marginRight: 'auto' }}>
              Practice English in structured video rooms with AI-powered feedback.
              Join real conversations, get instant corrections, and build your confidence.
            </p>
            <div className="d-flex gap-2 justify-content-center flex-wrap mb-4">
              <Button variant="primary" size="lg" className="rounded-pill px-4 fw-semibold d-flex align-items-center gap-2"
                onClick={handleQuickJoin} disabled={quickJoining}>
                {quickJoining ? (
                  <><Spinner animation="border" size="sm" /> Finding room...</>
                ) : (
                  <><HiBolt size={20} /> Quick Join Room</>
                )}
              </Button>
              <a href="#contact-us" onClick={(e) => { e.preventDefault(); document.getElementById('contact-section')?.scrollIntoView({ behavior: 'smooth' }); }}>
                <Button variant="outline-secondary" size="lg" className="rounded-pill px-4 fw-semibold d-flex align-items-center gap-2">
                  <HiEnvelope size={20} /> Contact Us
                </Button>
              </a>
            </div>
            <div className="d-flex justify-content-center flex-wrap gap-3 text-muted small">
              {['No downloads', 'AI feedback', 'Free to start'].map((t, i) => (
                <span key={i} className="d-flex align-items-center gap-1">
                  <FiCheck size={14} style={{ color: 'var(--color-success)' }} /> {t}
                </span>
              ))}
            </div>
          </div>
        </Container>
      </section>

      <section className="stats-section py-5" style={{ background: 'var(--color-bg)' }}>
        <Container>
          <div className="text-center mb-4">
            <h2 className="fw-extrabold mb-2" style={{ fontFamily: 'Nunito, sans-serif' }}>Trusted by learners worldwide</h2>
            <p className="text-muted">Numbers that speak for themselves</p>
          </div>
          <Row className="justify-content-center">
            <CounterStat icon={HiUserGroup} value={12500} label="Active Learners" suffix="+" delay={0} />
            <CounterStat icon={HiGlobeAlt} value={85} label="Countries" delay={0.1} />
            <CounterStat icon={HiChatBubbleLeftRight} value={45000} label="Sessions Completed" suffix="+" delay={0.2} />
            <CounterStat icon={HiStar} value={98} label="Satisfaction Rate" suffix="%" delay={0.3} />
          </Row>
        </Container>
      </section>

      <section className="features-section py-5" style={{ background: 'var(--color-bg-surface)' }}>
        <Container>
          <div className="text-center mb-5">
            <h2 className="fw-extrabold mb-2" style={{ fontFamily: 'Nunito, sans-serif' }}>Why E-Room?</h2>
            <p className="text-muted">Everything you need to master spoken English</p>
          </div>
          <Row>
            <FeatureCard icon={HiAcademicCap} title="Structured Rooms" description="Topic-based rooms with guided conversations and clear learning objectives." delay={0} />
            <FeatureCard icon={HiLightBulb} title="AI Feedback" description="Real-time pronunciation and grammar corrections powered by advanced AI." delay={0.08} />
            <FeatureCard icon={HiUserGroup} title="Smart Matching" description="Get paired with learners at your level based on shared interests." delay={0.16} />
            <FeatureCard icon={HiGlobeAlt} title="Live Audio & Video" description="Crystal clear communication with LiveKit-powered rooms." delay={0.24} />
            <FeatureCard icon={HiTrophy} title="Track Progress" description="Monitor your improvement with leaderboards and skill tracking." delay={0.32} />
            <FeatureCard icon={HiShieldCheck} title="Safe Environment" description="Moderated rooms with NSFW detection and anti-misuse protection." delay={0.4} />
          </Row>
        </Container>
      </section>

      <section className="how-section py-5" style={{ background: 'var(--color-bg)' }}>
        <Container>
          <div className="text-center mb-5">
            <div className="d-inline-flex align-items-center gap-2 px-3 py-1 rounded-pill mb-3"
              style={{ background: 'var(--color-success-muted)' }}>
              <HiRocketLaunch size={16} style={{ color: 'var(--color-success)' }} />
              <small className="fw-semibold" style={{ color: 'var(--color-success)' }}>Get Started in Minutes</small>
            </div>
            <h2 className="fw-extrabold mb-2" style={{ fontFamily: 'Nunito, sans-serif' }}>How It Works</h2>
            <p className="text-muted">Four simple steps to start speaking English confidently</p>
          </div>
          <Row>
            {STEP_ITEMS.map((step, i) => {
              const Icon = step.icon;
              return (
                <Col md={6} lg={3} key={i} className="mb-4">
                  <Card className="h-100 border-0 shadow-sm text-center p-3 how-card fade-in-up"
                    style={{ animationDelay: `${i * 0.1}s` }}>
                    <Card.Body className="d-flex flex-column align-items-center">
                      <div className="position-relative mb-3">
                        <div className="feature-icon-circle d-flex align-items-center justify-content-center"
                          style={{ width: 64, height: 64, position: 'relative', zIndex: 1 }}>
                          <Icon size={32} style={{ color: 'var(--color-accent)' }} />
                        </div>
                        <div className="position-absolute top-0 start-100 translate-middle rounded-circle d-flex align-items-center justify-content-center"
                          style={{
                            width: 28, height: 28,
                            background: 'var(--color-accent-gradient)',
                            color: '#fff', fontSize: '0.75rem', fontWeight: 800,
                            marginLeft: -14
                          }}>
                          {i + 1}
                        </div>
                      </div>
                      <Card.Title className="fw-bold fs-5" style={{ color: 'var(--color-text-primary)' }}>{step.title}</Card.Title>
                      <Card.Text className="text-muted small">{step.desc}</Card.Text>
                    </Card.Body>
                  </Card>
                </Col>
              );
            })}
          </Row>
          <div className="text-center mt-3">
            <Link to={user ? '/learning' : '/login'}>
              <Button variant="primary" size="lg" className="rounded-pill px-5 fw-semibold d-inline-flex align-items-center gap-2">
                Start Your First Session <HiArrowRight size={18} />
              </Button>
            </Link>
          </div>
        </Container>
      </section>

      <section className="rooms-section py-5" style={{ background: 'var(--color-bg-elevated)' }}>
        <Container>
          <div className="d-flex justify-content-between align-items-center mb-4">
            <div>
              <h2 className="fw-extrabold mb-1 d-flex align-items-center gap-2" style={{ fontFamily: 'Nunito, sans-serif' }}>
                <HiPlayCircle size={24} style={{ color: 'var(--color-success)' }} />
                Active Rooms
              </h2>
              <p className="text-muted mb-0">Join a conversation happening right now</p>
            </div>
            <Link to="/learning">
              <Button variant="outline-primary" size="sm" className="rounded-pill d-flex align-items-center gap-1">
                View All <HiArrowRight size={14} />
              </Button>
            </Link>
          </div>
          <Row>
            {rooms.map((room, idx) => (
              <Col key={room.id} md={6} lg={4} className="mb-3 stagger-1" style={{ animationDelay: `${idx * 0.08}s` }}>
                <RoomCard room={room} />
              </Col>
            ))}
          </Row>
        </Container>
      </section>

      <section className="testimonials-section py-5" style={{ background: 'var(--color-bg)' }}>
        <Container>
          <div className="text-center mb-5">
            <div className="d-inline-flex align-items-center gap-2 px-3 py-1 rounded-pill mb-3"
              style={{ background: 'var(--color-warning-muted)' }}>
              <HiHeart size={16} style={{ color: 'var(--color-warning)' }} />
              <small className="fw-semibold" style={{ color: 'var(--color-warning)' }}>Loved by Learners</small>
            </div>
            <h2 className="fw-extrabold mb-2" style={{ fontFamily: 'Nunito, sans-serif' }}>What Our Users Say</h2>
            <p className="text-muted">Real stories from real English learners</p>
          </div>
          <Row>
            {TESTIMONIALS.map((t, i) => (
              <TestimonialCard key={i} {...t} delay={i * 0.1} />
            ))}
          </Row>
        </Container>
      </section>

      <section className="pricing-section py-5" style={{ background: 'var(--color-bg-surface)' }}>
        <Container>
          <div className="text-center mb-5">
            <h2 className="fw-extrabold mb-2" style={{ fontFamily: 'Nunito, sans-serif' }}>Simple, Transparent Pricing</h2>
            <p className="text-muted">Start free, upgrade when you're ready</p>
          </div>
          <Row className="justify-content-center">
            <Col md={5} className="mb-3 mb-md-0">
              <Card className="h-100 border-0 shadow-sm p-4 fade-in-up" style={{ animationDelay: '0s' }}>
                <Card.Body className="d-flex flex-column">
                  <h4 className="fw-extrabold mb-2" style={{ fontFamily: 'Nunito, sans-serif' }}>Free</h4>
                  <p className="text-muted mb-3">Perfect for getting started</p>
                  <div className="mb-4">
                    <span className="display-4 fw-extrabold" style={{ fontFamily: 'Nunito, sans-serif', color: 'var(--color-text-primary)' }}>$0</span>
                    <span className="text-muted">/month</span>
                  </div>
                  <ul className="list-unstyled d-flex flex-column gap-2 mb-4 flex-grow-1">
                    {['3 rooms per day', 'Basic AI feedback', 'Text chat', 'Standard audio quality'].map((f, i) => (
                      <li key={i} className="d-flex align-items-center gap-2 text-muted" style={{ fontSize: '0.9rem' }}>
                        <HiCheckCircle size={16} style={{ color: 'var(--color-success)', flexShrink: 0 }} /> {f}
                      </li>
                    ))}
                  </ul>
                  <Link to={user ? '/learning' : '/login'}>
                    <Button variant="outline-primary" className="rounded-pill w-100 fw-semibold">Get Started</Button>
                  </Link>
                </Card.Body>
              </Card>
            </Col>
            <Col md={5}>
              <Card className="h-100 border-0 shadow-lg p-4 fade-in-up glow-border"
                style={{
                  animationDelay: '0.1s',
                  border: '2px solid var(--color-accent) !important',
                  boxShadow: 'var(--shadow-glow)',
                }}>
                <Card.Body className="d-flex flex-column">
                  <div className="d-flex justify-content-between align-items-start mb-2">
                    <h4 className="fw-extrabold mb-0" style={{ fontFamily: 'Nunito, sans-serif' }}>Pro</h4>
                    <span className="badge bg-warning text-dark rounded-pill px-2" style={{ fontSize: '0.7rem' }}>POPULAR</span>
                  </div>
                  <p className="text-muted mb-3">For serious learners</p>
                  <div className="mb-4">
                    <span className="display-4 fw-extrabold" style={{ fontFamily: 'Nunito, sans-serif', color: 'var(--color-accent)' }}>$12</span>
                    <span className="text-muted">/month</span>
                  </div>
                  <ul className="list-unstyled d-flex flex-column gap-2 mb-4 flex-grow-1">
                    {[
                      'Unlimited rooms', 'Advanced AI feedback', 'Video & voice chat',
                      'HD audio quality', 'Progress analytics', 'Priority matching'
                    ].map((f, i) => (
                      <li key={i} className="d-flex align-items-center gap-2" style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
                        <HiCheckCircle size={16} style={{ color: 'var(--color-accent)', flexShrink: 0 }} /> {f}
                      </li>
                    ))}
                  </ul>
                  <Link to="/payment">
                    <Button variant="primary" className="rounded-pill w-100 fw-semibold">Upgrade to Pro</Button>
                  </Link>
                </Card.Body>
              </Card>
            </Col>
          </Row>
        </Container>
      </section>

      <section id="contact-section" className="contact-section py-5" style={{ background: 'var(--color-bg-elevated)' }}>
        <Container>
          <div className="text-center mb-5">
            <div className="d-inline-flex align-items-center gap-2 px-3 py-1 rounded-pill mb-3"
              style={{ background: 'var(--color-accent-muted)' }}>
              <HiEnvelope size={16} style={{ color: 'var(--color-accent)' }} />
              <small className="fw-semibold" style={{ color: 'var(--color-accent)' }}>Get In Touch</small>
            </div>
            <h2 className="fw-extrabold mb-2" style={{ fontFamily: 'Nunito, sans-serif' }}>Contact Us</h2>
            <p className="text-muted">Have questions or feedback? We'd love to hear from you.</p>
          </div>
          <Row className="justify-content-center">
            <Col md={8} lg={6}>
              <Card className="border-0 shadow-sm p-4">
                <Card.Body>
                  <Row className="g-3 mb-3">
                    <Col md={6}>
                      <Form.Label className="fw-semibold small text-muted">Name</Form.Label>
                      <Form.Control type="text" placeholder="Your name" className="rounded-3" />
                    </Col>
                    <Col md={6}>
                      <Form.Label className="fw-semibold small text-muted">Email</Form.Label>
                      <Form.Control type="email" placeholder="you@example.com" className="rounded-3" />
                    </Col>
                  </Row>
                  <div className="mb-3">
                    <Form.Label className="fw-semibold small text-muted">Message</Form.Label>
                    <Form.Control as="textarea" rows={4} placeholder="How can we help?" className="rounded-3" />
                  </div>
                  <Button variant="primary" className="rounded-pill px-4 fw-semibold d-flex align-items-center gap-2">
                    <HiEnvelope size={16} /> Send Message
                  </Button>
                  <div className="d-flex justify-content-center gap-4 mt-4 pt-3 border-top" style={{ borderColor: 'var(--color-border)' }}>
                    <small className="text-muted d-flex align-items-center gap-1"><HiEnvelope size={14} /> hello@e-room.app</small>
                    <small className="text-muted d-flex align-items-center gap-1"><HiGlobeAlt size={14} /> e-room.app</small>
                  </div>
                </Card.Body>
              </Card>
            </Col>
          </Row>
        </Container>
      </section>

      <section className="cta-section py-5"
        style={{ background: 'linear-gradient(135deg, var(--color-accent-muted), var(--color-bg-surface))' }}>
        <Container className="text-center">
          <HiGlobeAlt size={48} className="mb-3" style={{ color: 'var(--color-accent)' }} />
          <h2 className="fw-extrabold mb-3" style={{ fontFamily: 'Nunito, sans-serif' }}>Ready to improve your English?</h2>
          <p className="text-muted mb-4">Join thousands of learners practicing in E-Room every day.</p>
          <Link to={user ? '/learning' : '/login'}>
            <Button variant="primary" size="lg" className="rounded-pill px-5 fw-semibold d-flex align-items-center gap-2 mx-auto pulse-glow"
              style={{ width: 'fit-content' }}>
              <HiPlayCircle size={20} /> Get Started Free
            </Button>
          </Link>
        </Container>
      </section>

      <style>{`
        .home-page .feature-card { transition: transform 0.25s ease, box-shadow 0.25s ease; }
        .home-page .feature-card:hover { transform: translateY(-4px); box-shadow: var(--shadow-lg); }
        .home-page .room-card { transition: transform 0.2s ease, box-shadow 0.2s ease; }
        .home-page .room-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
        .home-page .how-card { transition: transform 0.25s ease, box-shadow 0.25s ease; }
        .home-page .how-card:hover { transform: translateY(-4px); box-shadow: var(--shadow-lg); }
        .home-page .testimonial-card { transition: transform 0.2s ease; }
        .home-page .testimonial-card:hover { transform: translateY(-3px); }
        .home-page .stat-card { transition: transform 0.2s ease, box-shadow 0.2s ease; }
        .home-page .stat-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
      `}</style>
    </div>
  );
}
