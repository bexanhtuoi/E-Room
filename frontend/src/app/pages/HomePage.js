import { useState } from 'react';
import { Link } from 'react-router-dom';
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Card from 'react-bootstrap/Card';
import Button from 'react-bootstrap/Button';
import Badge from 'react-bootstrap/Badge';
import Spinner from 'react-bootstrap/Spinner';
import { useAuth } from '../AuthContext';

function RoomCard({ room }) {
  const statusMap = {
    ACTIVE: { variant: 'success', label: 'Live' },
    MATCHING: { variant: 'warning', label: 'Matching' },
    IDLE: { variant: 'info', label: 'Waiting' },
    END: { variant: 'secondary', label: 'Ended' },
  };
  const status = statusMap[room.status] || statusMap.IDLE;

  return (
    <Card className="h-100 shadow-sm border-0 room-card">
      <Card.Body className="d-flex flex-column">
        <div className="d-flex justify-content-between align-items-start mb-2">
          <Card.Title className="fw-bold mb-0 fs-6 text-truncate">
            {room.name || room.room_name || 'Untitled Room'}
          </Card.Title>
          <Badge bg={status.variant} pill className="text-uppercase" style={{ fontSize: '0.65rem' }}>
            {status.label}
          </Badge>
        </div>
        <Card.Text className="text-muted small mb-3 flex-grow-1">
          {room.description || room.topic || 'Join this room to practice English speaking with others.'}
        </Card.Text>
        <div className="d-flex justify-content-between align-items-center mt-auto">
          <small className="text-muted">
            <span className="me-2">👤 {room.current_participants || 0}/{room.max_participants || 5}</span>
            {room.tags && room.tags.slice(0, 2).map(tag => (
              <Badge bg="light" text="dark" className="me-1" key={tag} style={{ fontSize: '0.65rem' }}>
                {tag}
              </Badge>
            ))}
          </small>
          <Link to={`/rooms/${room.id}`}>
            <Button variant="outline-primary" size="sm" className="rounded-pill px-3">
              Join
            </Button>
          </Link>
        </div>
      </Card.Body>
    </Card>
  );
}

function FeatureCard({ icon, title, description }) {
  return (
    <Col md={4} className="mb-4">
      <Card className="h-100 border-0 shadow-sm text-center p-3 feature-card">
        <Card.Body>
          <div className="display-4 mb-3">{icon}</div>
          <Card.Title className="fw-bold fs-5">{title}</Card.Title>
          <Card.Text className="text-muted small">{description}</Card.Text>
        </Card.Body>
      </Card>
    </Col>
  );
}

export function HomePage() {
  const { user } = useAuth();
  const [rooms] = useState([
    { id: '1', name: 'Beginner Chat', topic: 'Daily conversations for beginners', status: 'ACTIVE', current_participants: 3, max_participants: 5, tags: ['beginner', 'daily'] },
    { id: '2', name: 'Business English', topic: 'Practice professional vocabulary and meetings', status: 'ACTIVE', current_participants: 4, max_participants: 5, tags: ['business', 'advanced'] },
    { id: '3', name: 'IELTS Speaking Prep', topic: 'Mock IELTS speaking test practice', status: 'MATCHING', current_participants: 2, max_participants: 5, tags: ['ielts', 'exam'] },
    { id: '4', name: 'Casual Chat', topic: 'Relaxed conversation about hobbies and life', status: 'IDLE', current_participants: 0, max_participants: 5, tags: ['casual', 'fun'] },
    { id: '5', name: 'Pronunciation Workshop', topic: 'Focus on accent reduction and clarity', status: 'ACTIVE', current_participants: 5, max_participants: 5, tags: ['pronunciation', 'intermediate'] },
    { id: '6', name: 'Tech Talk', topic: 'Discuss technology trends in English', status: 'IDLE', current_participants: 1, max_participants: 5, tags: ['tech', 'advanced'] },
  ]);
  const [loading] = useState(false);

  return (
    <div className="home-page fade-in">
      {/* Hero Section */}
      <section className="hero-section py-5">
        <Container>
          <Row className="align-items-center">
            <Col lg={6} className="mb-4 mb-lg-0">
              <h1 className="display-4 fw-extrabold mb-3" style={{ fontFamily: 'Nunito, sans-serif', fontWeight: 800 }}>
                Speak English,<br />
                <span style={{ color: 'var(--color-accent)' }}>Connect Globally</span>
              </h1>
              <p className="lead text-muted mb-4">
                Practice English in structured video rooms with AI-powered feedback.
                Join real conversations, get instant corrections, and build your confidence.
              </p>
              <div className="d-flex gap-2 flex-wrap">
                <Link to={user ? '/rooms' : '/login'}>
                  <Button variant="primary" size="lg" className="rounded-pill px-4 fw-semibold">
                    Start Speaking
                  </Button>
                </Link>
                <Button variant="outline-secondary" size="lg" className="rounded-pill px-4 fw-semibold">
                  How It Works
                </Button>
              </div>
              <div className="d-flex gap-3 mt-3 text-muted small">
                <span>✅ No download needed</span>
                <span>✅ AI feedback</span>
                <span>✅ Free to start</span>
              </div>
            </Col>
            <Col lg={6} className="text-center d-none d-lg-block">
              <div className="hero-illustration p-5">
                <div className="hero-circle mx-auto d-flex align-items-center justify-content-center" style={{
                  width: '280px', height: '280px', borderRadius: '50%',
                  background: 'linear-gradient(135deg, var(--color-accent-muted), var(--color-bg-surface))',
                  border: '3px solid var(--color-border)'
                }}>
                  <div className="text-center">
                    <div className="display-3 mb-2">🌐</div>
                    <h5 className="fw-bold">E-Room</h5>
                    <small className="text-muted">Your English Practice Hub</small>
                  </div>
                </div>
              </div>
            </Col>
          </Row>
        </Container>
      </section>

      {/* Features */}
      <section className="features-section py-5" style={{ background: 'var(--color-bg-surface)' }}>
        <Container>
          <div className="text-center mb-5">
            <h2 className="fw-bold mb-2">Why E-Room?</h2>
            <p className="text-muted">Everything you need to master spoken English</p>
          </div>
          <Row>
            <FeatureCard icon="🎯" title="Structured Rooms" description="Topic-based rooms with guided conversations and learning objectives" />
            <FeatureCard icon="🤖" title="AI Feedback" description="Real-time pronunciation and grammar corrections powered by AI" />
            <FeatureCard icon="👥" title="Smart Matching" description="Get paired with learners at your level based on shared interests" />
            <FeatureCard icon="🔊" title="Live Audio & Video" description="Crystal clear communication with LiveKit-powered rooms" />
            <FeatureCard icon="📝" title="Session Notes" description="Auto-generated summaries and corrections after each session" />
            <FeatureCard icon="🏆" title="Track Progress" description="Monitor your improvement with leaderboards and skill tracking" />
          </Row>
        </Container>
      </section>

      {/* Live Rooms */}
      <section className="rooms-section py-5">
        <Container>
          <div className="d-flex justify-content-between align-items-center mb-4">
            <div>
              <h2 className="fw-bold mb-1">Active Rooms</h2>
              <p className="text-muted mb-0">Join a conversation happening right now</p>
            </div>
            <Link to="/rooms">
              <Button variant="outline-primary" size="sm" className="rounded-pill">View All</Button>
            </Link>
          </div>
          {loading ? (
            <div className="text-center py-5">
              <Spinner animation="border" variant="primary" />
              <p className="text-muted mt-2">Loading rooms...</p>
            </div>
          ) : rooms.length === 0 ? (
            <div className="text-center py-5">
              <div className="display-1 mb-3">🏠</div>
              <h5 className="fw-bold">No rooms yet</h5>
              <p className="text-muted">Be the first to create a practice room!</p>
              <Button variant="primary" className="rounded-pill px-4">Create Room</Button>
            </div>
          ) : (
            <Row>
              {rooms.map((room, idx) => (
                <Col key={room.id} md={6} lg={4} className={`mb-4 stagger-${(idx % 5) + 1}`}>
                  <RoomCard room={room} />
                </Col>
              ))}
            </Row>
          )}
        </Container>
      </section>

      {/* CTA */}
      <section className="cta-section py-5" style={{ background: 'linear-gradient(135deg, var(--color-accent-muted), var(--color-bg-surface))' }}>
        <Container className="text-center">
          <h2 className="fw-bold mb-3">Ready to improve your English?</h2>
          <p className="text-muted mb-4">Join thousands of learners practicing in E-Room every day.</p>
          <Link to={user ? '/rooms' : '/login'}>
            <Button variant="primary" size="lg" className="rounded-pill px-5 fw-semibold">
              Get Started Free
            </Button>
          </Link>
        </Container>
      </section>

      {/* Footer */}
      <footer className="py-4 border-top" style={{ borderColor: 'var(--color-border)' }}>
        <Container>
          <Row>
            <Col md={6} className="mb-3 mb-md-0">
              <span className="fw-extrabold fs-5" style={{ fontFamily: 'Nunito, sans-serif' }}>E-Room</span>
              <small className="text-muted d-block mt-1">Speak English, Connect Globally</small>
            </Col>
            <Col md={6} className="text-md-end">
              <small className="text-muted">© 2026 E-Room. All rights reserved.</small>
            </Col>
          </Row>
        </Container>
      </footer>

      <style>{`
        .home-page { min-height: 100vh; }
        .hero-section { background: var(--color-bg-elevated); }
        .feature-card { transition: transform 0.2s ease, box-shadow 0.2s ease; }
        .feature-card:hover { transform: translateY(-4px); box-shadow: var(--shadow-lg); }
        .room-card { transition: transform 0.2s ease, box-shadow 0.2s ease; }
        .room-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
      `}</style>
    </div>
  );
}
