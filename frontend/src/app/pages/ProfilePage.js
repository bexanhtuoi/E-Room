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
import { HiUserCircle, HiCog6Tooth, HiShieldCheck, HiBookOpen, HiCreditCard, HiArrowRightOnRectangle, HiPencil, HiCheckCircle } from 'react-icons/hi2';
import { useAuth } from '../AuthContext';

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
    setTimeout(() => { setSaving(false); setEditing(false); setMessage({ type: 'success', text: 'Profile updated!' }); setTimeout(() => setMessage(null), 3000); }, 800);
  }

  function handleLogout() { logout(); navigate('/login'); }

  if (!user) return <Container className="py-5 text-center"><Spinner animation="border" variant="primary" /><p className="text-muted mt-2">Loading...</p></Container>;

  const tabs = [
    { key: 'profile', label: 'Profile', icon: HiUserCircle },
    { key: 'subscription', label: 'Subscription', icon: HiCreditCard },
    { key: 'history', label: 'History', icon: HiBookOpen },
    { key: 'settings', label: 'Settings', icon: HiCog6Tooth },
  ];

  return (
    <div className="profile-page fade-in">
      <Container className="py-4">
        <div className="d-flex flex-column flex-md-row align-items-md-center gap-3 mb-4">
          <div className="d-flex align-items-center justify-content-center rounded-4 fw-extrabold" style={{ width: 72, height: 72, background: 'linear-gradient(135deg, var(--color-accent), #0891b2)', color: '#fff', fontSize: '1.5rem', fontFamily: 'Nunito, sans-serif' }}>
            {(user.display_name || user.email)[0]?.toUpperCase()}
          </div>
          <div className="flex-grow-1">
            <h2 className="fw-extrabold mb-1 d-flex align-items-center gap-2" style={{ fontFamily: 'Nunito, sans-serif' }}>
              {user.display_name || 'User'}
              {editing && <HiPencil size={16} className="text-muted" />}
            </h2>
            <p className="text-muted mb-0">{user.email}</p>
            <small className="text-muted">Member since 2026</small>
          </div>
          <Button variant="outline-danger" size="sm" className="rounded-pill d-flex align-items-center gap-1" onClick={handleLogout}>
            <HiArrowRightOnRectangle size={14} /> Sign Out
          </Button>
        </div>

        {message && <Alert variant={message.type} dismissible onClose={() => setMessage(null)} className="d-flex align-items-center gap-2">{message.type === 'success' && <HiCheckCircle size={16} style={{ color: 'var(--color-success)' }} />}{message.text}</Alert>}

        <div className="d-flex gap-1 mb-4 border-bottom pb-2 flex-wrap" style={{ borderColor: 'var(--color-border)' }}>
          {tabs.map(tab => {
            const Icon = tab.icon;
            const active = activeTab === tab.key;
            return (
              <Button key={tab.key} variant={active ? 'primary' : 'link'}
                size="sm" className={`rounded-pill px-3 d-flex align-items-center gap-1 ${active ? 'fw-semibold' : 'text-decoration-none text-muted'}`}
                onClick={() => setActiveTab(tab.key)}>
                <Icon size={14} /> {tab.label}
              </Button>
            );
          })}
        </div>

        {activeTab === 'profile' && (
          <Row>
            <Col lg={8}>
              <Card className="border-0 shadow-sm mb-4">
                <Card.Body className="p-4">
                  <div className="d-flex justify-content-between align-items-center mb-4">
                    <h5 className="fw-bold mb-0 d-flex align-items-center gap-2"><HiUserCircle size={22} style={{ color: 'var(--color-accent)' }} /> Personal Information</h5>
                    {!editing && <Button variant="outline-primary" size="sm" className="rounded-pill d-flex align-items-center gap-1" onClick={() => setEditing(true)}><HiPencil size={14} /> Edit</Button>}
                  </div>
                  <Form>
                    <Row>
                      <Col md={6} className="mb-3">
                        <Form.Label className="fw-semibold small text-muted">Display Name</Form.Label>
                        <Form.Control type="text" value={displayName} onChange={e => setDisplayName(e.target.value)} disabled={!editing} className="rounded-3" />
                      </Col>
                      <Col md={6} className="mb-3">
                        <Form.Label className="fw-semibold small text-muted">Email</Form.Label>
                        <Form.Control type="email" value={user.email} disabled className="rounded-3" />
                      </Col>
                    </Row>
                    <Row>
                      <Col md={6} className="mb-3"><Form.Label className="fw-semibold small text-muted">Level</Form.Label><Form.Control type="text" value="Intermediate" disabled className="rounded-3" /></Col>
                      <Col md={6} className="mb-3"><Form.Label className="fw-semibold small text-muted">Language</Form.Label><Form.Select disabled={!editing} className="rounded-3"><option>Vietnamese</option><option>English</option></Form.Select></Col>
                    </Row>
                    {editing && (
                      <div className="d-flex gap-2">
                        <Button variant="primary" size="sm" className="rounded-pill px-4 d-flex align-items-center gap-1" onClick={handleSave} disabled={saving}>
                          {saving ? <><Spinner animation="border" size="sm" /> Saving...</> : <><HiCheckCircle size={16} /> Save</>}
                        </Button>
                        <Button variant="outline-secondary" size="sm" className="rounded-pill px-4" onClick={() => setEditing(false)}>Cancel</Button>
                      </div>
                    )}
                  </Form>
                </Card.Body>
              </Card>
            </Col>
            <Col lg={4}>
              <Card className="border-0 shadow-sm mb-4">
                <Card.Body className="p-4 text-center">
                  <HiBookOpen size={32} className="mb-2" style={{ color: 'var(--color-accent)' }} />
                  <h5 className="fw-bold">Your Stats</h5>
                  <Row className="mt-3"><Col><div className="fw-bold fs-4">12</div><small className="text-muted">Sessions</small></Col><Col><div className="fw-bold fs-4">8h</div><small className="text-muted">Speaking</small></Col><Col><div className="fw-bold fs-4">🏅</div><small className="text-muted">Rank</small></Col></Row>
                </Card.Body>
              </Card>
              <Card className="border-0 shadow-sm">
                <Card.Body className="p-4">
                  <h6 className="fw-bold mb-3 d-flex align-items-center gap-1"><HiShieldCheck size={16} style={{ color: 'var(--color-success)' }} /> Interests</h6>
                  <div className="d-flex flex-wrap gap-1">
                    {['technology', 'business', 'travel', 'music', 'gaming'].map(tag => (
                      <span key={tag} className="rounded-pill px-3 py-2 fw-medium" style={{ display: 'inline-block', background: 'var(--color-accent-muted)', color: 'var(--color-accent)', fontSize: '0.75rem', fontWeight: 600 }}>#{tag}</span>
                    ))}
                  </div>
                </Card.Body>
              </Card>
            </Col>
          </Row>
        )}

        {activeTab === 'subscription' && (
          <div className="text-center py-4">
            <HiCreditCard size={48} className="mb-3" style={{ color: 'var(--color-accent)' }} />
            <h5 className="fw-bold">Subscription Plans</h5>
            <p className="text-muted mb-4">Upgrade to unlock advanced features</p>
            <Row className="justify-content-center">
              {[
                { name: 'Free', price: '$0', features: ['5 rooms/day', 'Basic AI feedback', 'Standard matching'], color: 'outline-secondary' },
                { name: 'Pro', price: '$9.99/mo', features: ['Unlimited rooms', 'Advanced AI feedback', 'Priority matching', 'Session notes'], color: 'primary', popular: true },
                { name: 'Pro+', price: '$19.99/mo', features: ['All Pro features', 'TTS voice feedback', 'Expert RAG insights', 'Leaderboard'], color: 'outline-primary' },
              ].map((plan, idx) => (
                <Col key={idx} md={4} className="mb-3">
                  <Card className={`h-100 border-0 shadow-sm ${plan.popular ? 'border-primary' : ''}`} style={plan.popular ? { borderTop: '3px solid var(--color-accent)' } : {}}>
                    <Card.Body className="d-flex flex-column text-center p-4">
                      {plan.popular && <span className="badge bg-primary mb-2 align-self-center rounded-pill">Popular</span>}
                      <h5 className="fw-bold">{plan.name}</h5>
                      <div className="display-6 fw-bold my-2">{plan.price}</div>
                      <ul className="list-unstyled text-muted small flex-grow-1 text-start">
                        {plan.features.map(f => <li key={f} className="mb-1 d-flex align-items-center gap-1"><HiCheckCircle size={14} style={{ color: 'var(--color-success)' }} /> {f}</li>)}
                      </ul>
                      <Link to={`/payment?plan=${plan.name.toLowerCase()}`}>
                        <Button variant={plan.color} className="rounded-pill w-100 mt-auto fw-semibold">
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

        {activeTab === 'history' && (
          <Card className="border-0 shadow-sm">
            <Card.Body className="p-4 text-center py-5">
              <HiBookOpen size={48} className="mb-3" style={{ color: 'var(--color-text-muted)' }} />
              <h5 className="fw-bold">No Sessions Yet</h5>
              <p className="text-muted mb-3">Join a room to start building your history!</p>
              <Link to="/learning"><Button variant="primary" className="rounded-pill px-4">Find a Room</Button></Link>
            </Card.Body>
          </Card>
        )}

        {activeTab === 'settings' && (
          <Card className="border-0 shadow-sm">
            <Card.Body className="p-4">
              <h5 className="fw-bold mb-4 d-flex align-items-center gap-2"><HiCog6Tooth size={22} style={{ color: 'var(--color-accent)' }} /> Settings</h5>
              <div className="mb-4"><h6 className="fw-semibold">Notifications</h6><Form.Check type="switch" id="n1" label="Room match notifications" defaultChecked className="mb-2" /><Form.Check type="switch" id="n2" label="Session reminders" defaultChecked className="mb-2" /><Form.Check type="switch" id="n3" label="Email updates" /></div>
              <hr style={{ borderColor: 'var(--color-border)' }} />
              <div className="mb-4"><h6 className="fw-semibold">Privacy</h6><Form.Check type="switch" id="p1" label="Show profile" defaultChecked className="mb-2" /><Form.Check type="switch" id="p2" label="Show on leaderboard" defaultChecked /></div>
              <hr style={{ borderColor: 'var(--color-border)' }} />
              <div><h6 className="fw-semibold text-danger">Danger Zone</h6><Button variant="outline-danger" size="sm" className="rounded-pill">Delete Account</Button></div>
            </Card.Body>
          </Card>
        )}
      </Container>
    </div>
  );
}
