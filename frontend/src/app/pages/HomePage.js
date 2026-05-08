import { useState } from 'react';
import { Link } from 'react-router-dom';
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Card from 'react-bootstrap/Card';
import Button from 'react-bootstrap/Button';
import Badge from 'react-bootstrap/Badge';
import Spinner from 'react-bootstrap/Spinner';
import { HiHome, HiAcademicCap, HiUserGroup, HiLightBulb, HiShieldCheck, HiTrophy, HiGlobeAlt, HiSparkles, HiArrowRight, HiPlayCircle } from 'react-icons/hi2';
import { FiCheck } from 'react-icons/fi';
import { useAuth } from '../AuthContext';

function FeatureCard({ icon: Icon, title, description }) {
  return (
    <Col md={4} className="mb-4">
      <Card className="h-100 border-0 shadow-sm text-center p-3 feature-card fade-in">
        <Card.Body>
          <div className="d-inline-flex align-items-center justify-content-center rounded-3 mb-3" style={{ width: 56, height: 56, background: 'var(--color-accent-muted)' }}>
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
    MATCHING: { variant: 'warning', label: 'Matching', icon: HiUserGroup, color: 'var(--color-warning)' },
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
            <Badge key={tag} className="rounded-pill fw-medium" style={{ background: 'var(--color-accent-muted)', color: 'var(--color-accent)', fontSize: '0.65rem' }}>#{tag}</Badge>
          ))}
        </div>
        <div className="d-flex justify-content-between align-items-center mt-auto pt-2 border-top" style={{ borderColor: 'var(--color-border)' }}>
          <small className="text-muted">👤 {room.current_participants || 0}/{room.max_participants || 5}</small>
          <Link to={`/rooms/${room.id}`}>
            <Button variant="outline-primary" size="sm" className="rounded-pill px-3 fw-semibold">Join</Button>
          </Link>
        </div>
      </Card.Body>
    </Card>
  );
}

export function HomePage() {
  const { user } = useAuth();
  const [rooms] = useState([
    { id: '1', topic: 'Beginner Friendly Chat', description: 'Relaxed English for beginners about daily life.', status: 'ACTIVE', current_participants: 3, max_participants: 5, tags: ['beginner', 'daily'] },
    { id: '2', topic: 'Business English Pro', description: 'Professional vocabulary, presentations, meetings.', status: 'ACTIVE', current_participants: 4, max_participants: 4, tags: ['business', 'advanced'] },
    { id: '3', topic: 'IELTS Speaking Prep', description: 'Mock IELTS speaking tests with peer feedback.', status: 'MATCHING', current_participants: 2, max_participants: 3, tags: ['ielts', 'exam'] },
    { id: '4', topic: 'Tech Talk & Trends', description: 'AI, software dev, tech industry news in English.', status: 'ACTIVE', current_participants: 5, max_participants: 6, tags: ['technology', 'ai-ml'] },
    { id: '5', topic: 'Casual Weekend Vibes', description: 'Chat about hobbies, travel, food, music.', status: 'IDLE', current_participants: 0, max_participants: 8, tags: ['casual', 'travel'] },
    { id: '6', topic: 'Pronunciation Perfection', description: 'Accent reduction, intonation, clear speech.', status: 'ACTIVE', current_participants: 2, max_participants: 3, tags: ['education', 'psychology'] },
  ]);

  return (
    <div className="home-page fade-in" style={{ minHeight: '100vh' }}>
      {/* Hero */}
      <section className="hero-section py-5" style={{ background: 'linear-gradient(180deg, var(--color-bg-elevated) 0%, var(--color-bg) 100%)' }}>
        <Container>
          <Row className="align-items-center">
            <Col lg={6} className="mb-4 mb-lg-0">
              <div className="d-inline-flex align-items-center gap-2 px-3 py-1 rounded-pill mb-3" style={{ background: 'var(--color-accent-muted)' }}>
                <HiSparkles size={16} style={{ color: 'var(--color-accent)' }} />
                <small className="fw-semibold" style={{ color: 'var(--color-accent)' }}>AI-Powered English Practice</small>
              </div>
              <h1 className="display-4 fw-extrabold mb-3" style={{ fontFamily: 'Nunito, sans-serif' }}>
                Speak English,<br />
                <span style={{ background: 'linear-gradient(135deg, var(--color-accent), #0891b2)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                  Connect Globally
                </span>
              </h1>
              <p className="lead text-muted mb-4">
                Practice English in structured video rooms with AI-powered feedback.
                Join real conversations, get instant corrections, and build your confidence.
              </p>
              <div className="d-flex gap-2 flex-wrap mb-4">
                <Link to={user ? '/learning' : '/login'}>
                  <Button variant="primary" size="lg" className="rounded-pill px-4 fw-semibold d-flex align-items-center gap-2">
                    <HiPlayCircle size={20} /> Start Speaking
                  </Button>
                </Link>
                <Link to="/learning">
                  <Button variant="outline-secondary" size="lg" className="rounded-pill px-4 fw-semibold d-flex align-items-center gap-2">
                    <HiAcademicCap size={20} /> Browse Rooms
                  </Button>
                </Link>
              </div>
              <div className="d-flex flex-wrap gap-3 text-muted small">
                {['No downloads', 'AI feedback', 'Free to start'].map((t, i) => (
                  <span key={i} className="d-flex align-items-center gap-1"><FiCheck size={14} style={{ color: 'var(--color-success)' }} /> {t}</span>
                ))}
              </div>
            </Col>
            <Col lg={6} className="text-center d-none d-lg-block">
              <div className="hero-visual mx-auto position-relative" style={{ width: 320, height: 320 }}>
                <div className="position-absolute top-50 start-50 translate-middle d-flex align-items-center justify-content-center rounded-4" style={{
                  width: 240, height: 240, background: 'linear-gradient(135deg, var(--color-accent-muted), var(--color-bg-surface))',
                  border: '3px solid var(--color-border)', zIndex: 2,
                }}>
                  <div className="text-center">
                    <HiGlobeAlt size={48} style={{ color: 'var(--color-accent)' }} />
                    <h5 className="fw-bold mt-2">E-Room</h5>
                    <small className="text-muted">Your English Hub</small>
                  </div>
                </div>
                <div className="position-absolute rounded-circle" style={{ width: 80, height: 80, top: 10, right: 10, background: 'var(--color-accent-muted)', zIndex: 1, opacity: 0.5 }} />
                <div className="position-absolute rounded-circle" style={{ width: 60, height: 60, bottom: 20, left: 20, background: 'var(--color-success-muted)', zIndex: 3, opacity: 0.6 }} />
              </div>
            </Col>
          </Row>
        </Container>
      </section>

      {/* Features */}
      <section className="features-section py-5" style={{ background: 'var(--color-bg-surface)' }}>
        <Container>
          <div className="text-center mb-5">
            <h2 className="fw-extrabold mb-2" style={{ fontFamily: 'Nunito, sans-serif' }}>Why E-Room?</h2>
            <p className="text-muted">Everything you need to master spoken English</p>
          </div>
          <Row>
            <FeatureCard icon={HiAcademicCap} title="Structured Rooms" description="Topic-based rooms with guided conversations and clear learning objectives." />
            <FeatureCard icon={HiLightBulb} title="AI Feedback" description="Real-time pronunciation and grammar corrections powered by advanced AI." />
            <FeatureCard icon={HiUserGroup} title="Smart Matching" description="Get paired with learners at your level based on shared interests." />
            <FeatureCard icon={HiGlobeAlt} title="Live Audio & Video" description="Crystal clear communication with LiveKit-powered rooms." />
            <FeatureCard icon={HiTrophy} title="Track Progress" description="Monitor your improvement with leaderboards and skill tracking." />
            <FeatureCard icon={HiShieldCheck} title="Safe Environment" description="Moderated rooms with NSFW detection and anti-misuse protection." />
          </Row>
        </Container>
      </section>

      {/* Active Rooms */}
      <section className="rooms-section py-5">
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

      {/* CTA */}
      <section className="cta-section py-5" style={{ background: 'linear-gradient(135deg, var(--color-accent-muted), var(--color-bg-surface))' }}>
        <Container className="text-center">
          <HiGlobeAlt size={48} className="mb-3" style={{ color: 'var(--color-accent)' }} />
          <h2 className="fw-extrabold mb-3" style={{ fontFamily: 'Nunito, sans-serif' }}>Ready to improve your English?</h2>
          <p className="text-muted mb-4">Join thousands of learners practicing in E-Room every day.</p>
          <Link to={user ? '/learning' : '/login'}>
            <Button variant="primary" size="lg" className="rounded-pill px-5 fw-semibold d-flex align-items-center gap-2 mx-auto" style={{ width: 'fit-content' }}>
              <HiPlayCircle size={20} /> Get Started Free
            </Button>
          </Link>
        </Container>
      </section>

      {/* Footer */}
      <footer className="py-4 border-top" style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg-elevated)' }}>
        <Container>
          <Row>
            <Col md={6} className="mb-3 mb-md-0">
              <span className="fw-extrabold fs-5 d-flex align-items-center gap-2" style={{ fontFamily: 'Nunito, sans-serif' }}>
                <HiHome size={20} style={{ color: 'var(--color-accent)' }} /> E-Room
              </span>
              <small className="text-muted d-block mt-1">Speak English, Connect Globally</small>
            </Col>
            <Col md={6} className="text-md-end d-flex align-items-center justify-content-md-end gap-3">
              <Link to="/learning" className="text-muted small text-decoration-none">Rooms</Link>
              <Link to="/profile" className="text-muted small text-decoration-none">Profile</Link>
              <Link to="/payment" className="text-muted small text-decoration-none">Pricing</Link>
              <small className="text-muted">© 2026 E-Room</small>
            </Col>
          </Row>
        </Container>
      </footer>

      <style>{`
        .home-page .feature-card { transition: transform 0.2s ease, box-shadow 0.2s ease; }
        .home-page .feature-card:hover { transform: translateY(-4px); box-shadow: var(--shadow-lg); }
        .home-page .room-card { transition: transform 0.2s ease, box-shadow 0.2s ease; }
        .home-page .room-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
      `}</style>
    </div>
  );
}
