import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import Alert from 'react-bootstrap/Alert';
import Spinner from 'react-bootstrap/Spinner';
import InputGroup from 'react-bootstrap/InputGroup';
import { useAuth } from '../../app/AuthContext';

export function LoginPage() {
  const { login, register, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    if (isAuthenticated) navigate('/', { replace: true });
  }, [isAuthenticated, navigate]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      if (isRegister) {
        await register(email, password, displayName);
        await login(email, password);
      } else {
        await login(email, password);
      }
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.message || 'Authentication failed. Please try again.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page" style={{ minHeight: '100vh', background: 'var(--color-bg)' }}>
      <Container fluid className="h-100">
        <Row className="min-vh-100">
          {/* Left Brand Panel */}
          <Col lg={5} className="d-none d-lg-flex flex-column justify-content-center p-5" style={{
            background: 'linear-gradient(135deg, var(--color-bg-surface) 0%, var(--color-bg-elevated) 100%)',
            position: 'relative',
            overflow: 'hidden'
          }}>
            <div className="position-relative" style={{ zIndex: 1 }}>
              <div className="d-inline-flex align-items-center justify-content-center mb-4" style={{
                width: 56, height: 56, borderRadius: 'var(--radius-md)',
                background: 'var(--color-accent)', color: '#fff',
                fontSize: 26, fontWeight: 800, fontFamily: 'Nunito, sans-serif'
              }}>E</div>
              <h1 className="fw-extrabold mb-2" style={{ fontFamily: 'Nunito, sans-serif', fontSize: '2rem', color: 'var(--color-text-primary)' }}>
                E-Room
              </h1>
              <p className="text-muted mb-4" style={{ fontSize: '1.05rem' }}>Speak English, Connect Globally</p>
              <ul className="list-unstyled d-flex flex-column gap-3">
                {['Practice with real people in structured rooms', 'AI-powered feedback on your speaking', 'Connect with learners worldwide'].map((text, i) => (
                  <li key={i} className="d-flex align-items-center gap-2 text-muted" style={{ fontSize: '0.9rem' }}>
                    <span className="d-flex align-items-center justify-content-center rounded-circle" style={{
                      width: 24, height: 24, background: 'var(--color-accent-muted)', color: 'var(--color-accent)', fontSize: 12
                    }}>✓</span>
                    {text}
                  </li>
                ))}
              </ul>
            </div>
            <div className="position-absolute" style={{
              top: '-30%', right: '-15%', width: 500, height: 500, borderRadius: '50%',
              background: 'radial-gradient(circle, var(--color-accent-muted) 0%, transparent 70%)',
              opacity: 0.5, pointerEvents: 'none'
            }} />
          </Col>

          {/* Right Form Panel */}
          <Col lg={7} className="d-flex align-items-center justify-content-center p-4">
            <div style={{ maxWidth: 420, width: '100%' }} className="fade-in">
              <h2 className="fw-bold mb-1" style={{ fontFamily: 'Nunito, sans-serif' }}>
                {isRegister ? 'Create account' : 'Welcome back'}
              </h2>
              <p className="text-muted mb-4">
                {isRegister ? 'Join English speaking rooms' : 'Sign in to start speaking'}
              </p>

              <Form onSubmit={handleSubmit}>
                {isRegister && (
                  <Form.Group className="mb-3">
                    <Form.Label className="fw-semibold small text-muted">Display Name</Form.Label>
                    <Form.Control
                      type="text"
                      value={displayName}
                      onChange={e => setDisplayName(e.target.value)}
                      placeholder="Your name"
                      required
                      className="rounded-3 py-2"
                    />
                  </Form.Group>
                )}

                <Form.Group className="mb-3">
                  <Form.Label className="fw-semibold small text-muted">Email</Form.Label>
                  <Form.Control
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    autoFocus
                    required
                    className="rounded-3 py-2"
                  />
                </Form.Group>

                <Form.Group className="mb-3">
                  <Form.Label className="fw-semibold small text-muted">Password</Form.Label>
                  <InputGroup>
                    <Form.Control
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      placeholder="••••••••"
                      required
                      minLength={8}
                      className="rounded-start-3 py-2"
                    />
                    <Button
                      variant="outline-secondary"
                      className="rounded-end-3"
                      onClick={() => setShowPassword(!showPassword)}
                      tabIndex={-1}
                    >
                      {showPassword ? '🙈' : '👁️'}
                    </Button>
                  </InputGroup>
                </Form.Group>

                {error && (
                  <Alert variant="danger" className="py-2 small d-flex align-items-center gap-2">
                    ⚠️ {error}
                  </Alert>
                )}

                <Button
                  type="submit"
                  variant="primary"
                  size="lg"
                  className="rounded-pill w-100 mt-2 fw-semibold"
                  disabled={busy}
                >
                  {busy ? (
                    <><Spinner animation="border" size="sm" className="me-2" /> Please wait...</>
                  ) : isRegister ? (
                    'Create account'
                  ) : (
                    'Sign in'
                  )}
                </Button>
              </Form>

              <p className="text-center mt-3 mb-0">
                <small className="text-muted">
                  {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
                </small>
                <Button
                  variant="link"
                  className="p-0 fw-semibold text-decoration-none small"
                  onClick={() => { setIsRegister(!isRegister); setError(''); }}
                >
                  {isRegister ? 'Sign in' : 'Register'}
                </Button>
              </p>
            </div>
          </Col>
        </Row>
      </Container>

      <style>{`
        .login-page .form-control:focus {
          border-color: var(--color-accent);
          box-shadow: 0 0 0 0.25rem var(--color-accent-muted);
        }
      `}</style>
    </div>
  );
}
