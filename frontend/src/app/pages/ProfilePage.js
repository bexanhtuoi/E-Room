import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Card from 'react-bootstrap/Card';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import Alert from 'react-bootstrap/Alert';
import Spinner from 'react-bootstrap/Spinner';
import Badge from 'react-bootstrap/Badge';
import { useAuth } from '../AuthContext';
import { ThemeToggle } from '../../components/ui/ThemeToggle';
import { Avatar } from '../../components/ui/Avatar';

export function ProfilePage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState(user?.display_name || '');
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [activeTab, setActiveTab] = useState('profile');

  function handleSave() {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      setEditing(false);
      setMessage({ type: 'success', text: 'Profile updated successfully!' });
      setTimeout(() => setMessage(null), 3000);
    }, 800);
  }

  function handleLogout() {
    logout();
    navigate('/login');
  }

  if (!user) {
    return (
      <Container className="py-5 text-center">
        <Spinner animation="border" variant="primary" />
        <p className="text-muted mt-2">Loading profile...</p>
      </Container>
    );
  }

  const tabs = [
    { key: 'profile', label: 'Profile', icon: '👤' },
    { key: 'subscription', label: 'Subscription', icon: '💎' },
    { key: 'history', label: 'History', icon: '📋' },
    { key: 'settings', label: 'Settings', icon: '⚙️' },
  ];

  return (
    <div className="profile-page fade-in">
      <Container className="py-5">
        {/* Header */}
        <div className="d-flex flex-column flex-md-row align-items-md-center gap-3 mb-4">
          <Avatar name={user.display_name || user.email} size={72} />
          <div className="flex-grow-1">
            <h2 className="fw-bold mb-1">{user.display_name || 'User'}</h2>
            <p className="text-muted mb-0">{user.email}</p>
            <small className="text-muted">Member since 2026</small>
          </div>
          <div className="d-flex gap-2">
            <ThemeToggle />
            <Button variant="outline-danger" size="sm" onClick={handleLogout} className="rounded-pill">
              Sign Out
            </Button>
          </div>
        </div>

        {message && (
          <Alert variant={message.type} dismissible onClose={() => setMessage(null)}>
            {message.text}
          </Alert>
        )}

        {/* Tabs */}
        <div className="d-flex gap-1 mb-4 border-bottom pb-2" style={{ borderColor: 'var(--color-border)' }}>
          {tabs.map(tab => (
            <Button
              key={tab.key}
              variant={activeTab === tab.key ? 'primary' : 'link'}
              size="sm"
              className={`rounded-pill px-3 ${activeTab === tab.key ? '' : 'text-decoration-none text-muted'}`}
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.icon} {tab.label}
            </Button>
          ))}
        </div>

        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <Row>
            <Col lg={8}>
              <Card className="border-0 shadow-sm mb-4">
                <Card.Body className="p-4">
                  <div className="d-flex justify-content-between align-items-center mb-4">
                    <h5 className="fw-bold mb-0">Personal Information</h5>
                    {!editing && (
                      <Button variant="outline-primary" size="sm" className="rounded-pill" onClick={() => setEditing(true)}>
                        Edit
                      </Button>
                    )}
                  </div>
                  <Form>
                    <Row>
                      <Col md={6} className="mb-3">
                        <Form.Label className="fw-semibold small text-muted">Display Name</Form.Label>
                        <Form.Control
                          type="text"
                          value={displayName}
                          onChange={e => setDisplayName(e.target.value)}
                          disabled={!editing}
                          className="rounded-3"
                        />
                      </Col>
                      <Col md={6} className="mb-3">
                        <Form.Label className="fw-semibold small text-muted">Email</Form.Label>
                        <Form.Control type="email" value={user.email} disabled className="rounded-3" />
                      </Col>
                    </Row>
                    <Row>
                      <Col md={6} className="mb-3">
                        <Form.Label className="fw-semibold small text-muted">Level</Form.Label>
                        <Form.Control type="text" value="Intermediate" disabled className="rounded-3" />
                      </Col>
                      <Col md={6} className="mb-3">
                        <Form.Label className="fw-semibold small text-muted">Native Language</Form.Label>
                        <Form.Select disabled={!editing} className="rounded-3">
                          <option>Vietnamese</option>
                          <option>English</option>
                          <option>Japanese</option>
                          <option>Korean</option>
                          <option>Other</option>
                        </Form.Select>
                      </Col>
                    </Row>
                    {editing && (
                      <div className="d-flex gap-2">
                        <Button variant="primary" size="sm" className="rounded-pill px-4" onClick={handleSave} disabled={saving}>
                          {saving ? <><Spinner animation="border" size="sm" className="me-1" /> Saving...</> : 'Save Changes'}
                        </Button>
                        <Button variant="outline-secondary" size="sm" className="rounded-pill px-4" onClick={() => setEditing(false)}>
                          Cancel
                        </Button>
                      </div>
                    )}
                  </Form>
                </Card.Body>
              </Card>
            </Col>
            <Col lg={4}>
              <Card className="border-0 shadow-sm mb-4">
                <Card.Body className="p-4 text-center">
                  <div className="display-4 mb-2">📊</div>
                  <h5 className="fw-bold">Your Stats</h5>
                  <Row className="mt-3">
                    <Col>
                      <div className="fw-bold fs-4">12</div>
                      <small className="text-muted">Sessions</small>
                    </Col>
                    <Col>
                      <div className="fw-bold fs-4">8h</div>
                      <small className="text-muted">Speaking</small>
                    </Col>
                    <Col>
                      <div className="fw-bold fs-4">🏅</div>
                      <small className="text-muted">Rank</small>
                    </Col>
                  </Row>
                </Card.Body>
              </Card>
              <Card className="border-0 shadow-sm">
                <Card.Body className="p-4">
                  <h6 className="fw-bold mb-3">Your Interests</h6>
                  <div className="d-flex flex-wrap gap-1">
                    {['technology', 'business', 'travel', 'music', 'gaming'].map(tag => (
                      <span key={tag} className="badge rounded-pill px-3 py-2" style={{ background: 'var(--color-accent-muted)', color: 'var(--color-accent)', fontWeight: 600, fontSize: '0.75rem' }}>
                        {tag}
                      </span>
                    ))}
                  </div>
                </Card.Body>
              </Card>
            </Col>
          </Row>
        )}

        {/* Subscription Tab */}
        {activeTab === 'subscription' && (
          <div className="text-center py-5">
            <div className="display-1 mb-3">💎</div>
            <h5 className="fw-bold">Subscription Plans</h5>
            <p className="text-muted mb-4">Upgrade to unlock advanced features</p>
            <Row className="justify-content-center">
              {[
                { name: 'Free', price: '$0', features: ['5 rooms/day', 'Basic AI feedback', 'Standard matching'], color: 'outline-secondary' },
                { name: 'Pro', price: '$9.99/mo', features: ['Unlimited rooms', 'Advanced AI feedback', 'Priority matching', 'Session notes'], color: 'primary', popular: true },
                { name: 'Pro+', price: '$19.99/mo', features: ['Everything in Pro', 'TTS voice feedback', 'Expert RAG insights', 'Leaderboard access'], color: 'outline-primary' },
              ].map((plan, idx) => (
                <Col key={idx} md={4} className="mb-3">
                  <Card className={`h-100 border-0 shadow-sm ${plan.popular ? 'border-primary' : ''}`} style={plan.popular ? { borderTop: '3px solid var(--color-accent)' } : {}}>
                    <Card.Body className="d-flex flex-column text-center p-4">
                      {plan.popular && <Badge bg="primary" className="mb-2 align-self-center rounded-pill">Popular</Badge>}
                      <h5 className="fw-bold">{plan.name}</h5>
                      <div className="display-6 fw-bold my-2">{plan.price}</div>
                      <ul className="list-unstyled text-muted small flex-grow-1 text-start">
                        {plan.features.map(f => <li key={f} className="mb-1">✅ {f}</li>)}
                      </ul>
                      <Link to={`/payment?plan=${plan.name.toLowerCase()}`}>
                        <Button variant={plan.color} className="rounded-pill w-100 mt-auto">
                          {plan.name === 'Free' ? 'Current Plan' : 'Upgrade'}
                        </Button>
                      </Link>
                    </Card.Body>
                  </Card>
                </Col>
              ))}
            </Row>
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <Card className="border-0 shadow-sm">
            <Card.Body className="p-4">
              <h5 className="fw-bold mb-3">Session History</h5>
              <div className="text-center py-4 text-muted">
                <div className="display-1 mb-3">📋</div>
                <p>No session history yet. Start a room to see your progress!</p>
                <Link to="/">
                  <Button variant="primary" className="rounded-pill px-4">Find a Room</Button>
                </Link>
              </div>
            </Card.Body>
          </Card>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <Card className="border-0 shadow-sm">
            <Card.Body className="p-4">
              <h5 className="fw-bold mb-4">Settings</h5>
              <div className="mb-4">
                <h6 className="fw-semibold">Notifications</h6>
                <Form.Check type="switch" id="notify-match" label="Room match notifications" defaultChecked className="mb-2" />
                <Form.Check type="switch" id="notify-session" label="Session reminders" defaultChecked className="mb-2" />
                <Form.Check type="switch" id="notify-email" label="Email updates" className="mb-2" />
              </div>
              <hr style={{ borderColor: 'var(--color-border)' }} />
              <div className="mb-4">
                <h6 className="fw-semibold">Privacy</h6>
                <Form.Check type="switch" id="privacy-profile" label="Show profile to others" defaultChecked className="mb-2" />
                <Form.Check type="switch" id="privacy-leaderboard" label="Show on leaderboard" defaultChecked className="mb-2" />
              </div>
              <hr style={{ borderColor: 'var(--color-border)' }} />
              <div>
                <h6 className="fw-semibold text-danger">Danger Zone</h6>
                <Button variant="outline-danger" size="sm" className="rounded-pill">
                  Delete Account
                </Button>
              </div>
            </Card.Body>
          </Card>
        )}
      </Container>
    </div>
  );
}
