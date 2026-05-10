import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import Alert from 'react-bootstrap/Alert';
import Spinner from 'react-bootstrap/Spinner';
import InputGroup from 'react-bootstrap/InputGroup';
import ProgressBar from 'react-bootstrap/ProgressBar';
import {
  HiEye, HiEyeSlash, HiCheck, HiGlobeAlt, HiShieldCheck,
  HiLightBulb, HiExclamationTriangle, HiArrowRight,
  HiUser, HiLockClosed, HiEnvelope, HiSparkles
} from 'react-icons/hi2';
import { FcGoogle } from 'react-icons/fc';
import { FaGithub } from 'react-icons/fa';
import { useAuth } from '../../app/AuthContext';

function getPasswordStrength(pw) {
  if (!pw) return { score: 0, label: '', color: '' };
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  const map = [
    { score: 0, label: '', color: '' },
    { score: 1, label: 'Weak', color: '#ef4444' },
    { score: 2, label: 'Fair', color: '#f59e0b' },
    { score: 3, label: 'Good', color: '#6366f1' },
    { score: 4, label: 'Strong', color: '#10b981' },
    { score: 5, label: 'Great', color: '#10b981' },
  ];
  return map[Math.min(score, 5)];
}

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
  const [agreeTerms, setAgreeTerms] = useState(false);
  const contentRef = useRef(null);

  const strength = getPasswordStrength(password);

  useEffect(() => {
    if (isAuthenticated) navigate('/', { replace: true });
  }, [isAuthenticated, navigate]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    if (isRegister && !agreeTerms) {
      setError('Please agree to the Terms of Service and Privacy Policy.');
      return;
    }
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
      setError(err.message || 'Authentication failed.');
    } finally {
      setBusy(false);
    }
  }

  const brandFeatures = [
    { icon: HiGlobeAlt, text: 'Practice English in live video rooms with real people worldwide' },
    { icon: HiLightBulb, text: 'AI-powered real-time feedback on pronunciation & grammar' },
    { icon: HiShieldCheck, text: 'Safe, moderated environment with NSFW protection' },
    { icon: HiSparkles, text: 'Smart matching pairs you with learners at your level' },
  ];

  return (
    <div className="login-page fade-in" style={{ minHeight: '100vh', background: 'var(--color-bg)', display: 'flex' }}>
      <Container fluid className="d-flex p-0">
        <Row className="g-0 flex-grow-1">

          <Col lg={5} xl={6} className="d-none d-lg-flex flex-column justify-content-center p-5 position-relative"
            style={{
              background: 'linear-gradient(160deg, var(--color-bg-elevated) 0%, var(--color-bg-surface) 100%)',
              overflow: 'hidden',
            }}
          >

            <div className="position-absolute rounded-circle"
              style={{
                width: 420, height: 420, top: '-12%', right: '-18%',
                background: 'radial-gradient(circle, var(--color-accent-muted) 0%, transparent 70%)',
                opacity: 0.5, pointerEvents: 'none',
              }}
            />
            <div className="position-absolute rounded-circle"
              style={{
                width: 280, height: 280, bottom: '-8%', left: '-10%',
                background: 'radial-gradient(circle, rgba(16,185,129,0.08) 0%, transparent 70%)',
                opacity: 0.5, pointerEvents: 'none',
              }}
            />

            <div ref={contentRef} style={{ position: 'relative', zIndex: 1, maxWidth: 460 }}>

              <div className="d-flex align-items-center gap-3 mb-5">
                <div className="d-flex align-items-center justify-content-center rounded-3 flex-shrink-0"
                  style={{
                    width: 52, height: 52,
                    background: 'var(--color-accent-gradient)',
                    color: '#fff', fontSize: '1.3rem', fontWeight: 800,
                    fontFamily: 'Nunito, sans-serif',
                    boxShadow: 'var(--shadow-glow)',
                  }}>
                  E
                </div>
                <div>
                  <h1 className="fw-extrabold mb-0" style={{ fontFamily: 'Nunito, sans-serif', fontSize: '1.6rem', color: 'var(--color-text-primary)' }}>
                    E-Room
                  </h1>
                  <small style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>Speak English, Connect Globally</small>
                </div>
              </div>

              <h2 className="fw-extrabold mb-3" style={{ fontFamily: 'Nunito, sans-serif', fontSize: '1.8rem', lineHeight: 1.2, color: 'var(--color-text-primary)' }}>
                Your journey to <span className="gradient-text">fluent English</span> starts here.
              </h2>
              <p className="mb-4" style={{ color: 'var(--color-text-secondary)', fontSize: '0.95rem', lineHeight: 1.7 }}>
                Join thousands of learners practicing in structured video rooms with AI-powered feedback.
              </p>

              <ul className="list-unstyled d-flex flex-column gap-3">
                {brandFeatures.map((item, i) => {
                  const Icon = item.icon;
                  return (
                    <li key={i} className="d-flex align-items-start gap-3 fade-in-up"
                      style={{ animationDelay: `${0.1 + i * 0.1}s`, fontSize: '0.9rem', color: 'var(--color-text-secondary)' }}
                    >
                      <div className="feature-icon-circle flex-shrink-0 d-flex align-items-center justify-content-center"
                        style={{ width: 32, height: 32, marginTop: 1 }}
                      >
                        <Icon size={15} style={{ color: 'var(--color-accent)' }} />
                      </div>
                      <span style={{ lineHeight: 1.5 }}>{item.text}</span>
                    </li>
                  );
                })}
              </ul>

              <div className="mt-5 p-3 rounded-3"
                style={{
                  background: 'var(--color-bg-glass)',
                  border: '1px solid var(--color-border)',
                  backdropFilter: 'blur(12px)',
                }}>
                <p className="mb-2" style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', fontStyle: 'italic', lineHeight: 1.6 }}>
                  "E-Room transformed my English speaking. The AI feedback is incredibly accurate and the community is so supportive!"
                </p>
                <div className="d-flex align-items-center gap-2">
                  <div className="rounded-circle d-flex align-items-center justify-content-center"
                    style={{ width: 28, height: 28, background: 'var(--color-accent-gradient)', color: '#fff', fontSize: '0.7rem', fontWeight: 700 }}>
                    MT
                  </div>
                  <div>
                    <div className="fw-semibold" style={{ fontSize: '0.8rem', color: 'var(--color-text-primary)' }}>Minh Trang</div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>IELTS 7.5 · Member since 2025</div>
                  </div>
                </div>
              </div>
            </div>
          </Col>

          <Col lg={7} xl={6} className="d-flex align-items-center justify-content-center p-4 p-lg-5"
            style={{ background: 'var(--color-bg)' }}
          >
            <div style={{ maxWidth: 440, width: '100%' }} className="fade-in-up">

              <div className="d-flex align-items-center gap-2 mb-4 d-lg-none">
                <div className="d-flex align-items-center justify-content-center rounded-3"
                  style={{
                    width: 36, height: 36,
                    background: 'var(--color-accent-gradient)',
                    color: '#fff', fontWeight: 800, fontFamily: 'Nunito, sans-serif',
                  }}>
                  E
                </div>
                <span className="fw-extrabold" style={{ fontFamily: 'Nunito, sans-serif', color: 'var(--color-text-primary)' }}>E-Room</span>
              </div>

              <div className="mb-4">
                <h2 className="fw-extrabold mb-1" style={{ fontFamily: 'Nunito, sans-serif', color: 'var(--color-text-primary)', fontSize: '1.7rem' }}>
                  {isRegister ? 'Create your account' : 'Welcome back'}
                </h2>
                <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>
                  {isRegister ? 'Start your English speaking journey today' : 'Sign in to continue your learning'}
                </p>
              </div>

              <div className="d-flex gap-2 mb-4">
                <Button variant="outline-secondary" className="flex-grow-1 d-flex align-items-center justify-content-center gap-2 py-2 rounded-3"
                  style={{ fontSize: '0.85rem', borderColor: 'var(--color-border-strong)' }}>
                  <FcGoogle size={18} /> Google
                </Button>
                <Button variant="outline-secondary" className="flex-grow-1 d-flex align-items-center justify-content-center gap-2 py-2 rounded-3"
                  style={{ fontSize: '0.85rem', borderColor: 'var(--color-border-strong)' }}>
                  <FaGithub size={18} /> GitHub
                </Button>
              </div>

              <div className="d-flex align-items-center gap-3 mb-4">
                <div className="flex-grow-1" style={{ height: 1, background: 'var(--color-border)' }} />
                <small style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>or</small>
                <div className="flex-grow-1" style={{ height: 1, background: 'var(--color-border)' }} />
              </div>

              <Form onSubmit={handleSubmit}>
                {isRegister && (
                  <Form.Group className="mb-3">
                    <Form.Label className="fw-semibold small" style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>
                      Display Name
                    </Form.Label>
                    <InputGroup>
                      <InputGroup.Text className="bg-transparent" style={{ borderColor: 'var(--color-border)', borderRight: 'none' }}>
                        <HiUser size={16} style={{ color: 'var(--color-text-muted)' }} />
                      </InputGroup.Text>
                      <Form.Control
                        type="text" value={displayName}
                        onChange={e => setDisplayName(e.target.value)}
                        placeholder="Your name"
                        required
                        className="py-2"
                        style={{ borderLeft: 'none' }}
                      />
                    </InputGroup>
                  </Form.Group>
                )}

                <Form.Group className="mb-3">
                  <Form.Label className="fw-semibold small" style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>
                    Email Address
                  </Form.Label>
                  <InputGroup>
                    <InputGroup.Text className="bg-transparent" style={{ borderColor: 'var(--color-border)', borderRight: 'none' }}>
                      <HiEnvelope size={16} style={{ color: 'var(--color-text-muted)' }} />
                    </InputGroup.Text>
                    <Form.Control
                      type="email" value={email}
                      onChange={e => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      autoFocus required
                      className="py-2"
                      style={{ borderLeft: 'none' }}
                    />
                  </InputGroup>
                </Form.Group>

                <Form.Group className="mb-1">
                  <Form.Label className="fw-semibold small" style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>
                    Password
                  </Form.Label>
                  <InputGroup>
                    <InputGroup.Text className="bg-transparent" style={{ borderColor: 'var(--color-border)', borderRight: 'none' }}>
                      <HiLockClosed size={16} style={{ color: 'var(--color-text-muted)' }} />
                    </InputGroup.Text>
                    <Form.Control
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      placeholder="••••••••"
                      required
                      minLength={8}
                      className="py-2"
                      style={{ borderLeft: 'none', borderRight: 'none' }}
                    />
                    <Button variant="outline-secondary"
                      className="d-flex align-items-center"
                      style={{
                        borderColor: 'var(--color-border)',
                        borderLeft: 'none',
                        background: 'var(--color-bg-surface)',
                      }}
                      onClick={() => setShowPassword(!showPassword)}
                      tabIndex={-1}
                    >
                      {showPassword ? <HiEyeSlash size={16} /> : <HiEye size={16} />}
                    </Button>
                  </InputGroup>
                </Form.Group>

                {isRegister && password && (
                  <div className="mb-3 mt-2">
                    <div className="d-flex justify-content-between align-items-center mb-1">
                      <small style={{ color: 'var(--color-text-muted)', fontSize: '0.7rem' }}>Password strength</small>
                      <small className="fw-semibold" style={{ color: strength.color, fontSize: '0.7rem' }}>{strength.label}</small>
                    </div>
                    <ProgressBar
                      now={strength.score * 20}
                      variant={strength.score <= 1 ? 'danger' : strength.score <= 2 ? 'warning' : strength.score <= 3 ? 'info' : 'success'}
                      style={{ height: 4, borderRadius: 2 }}
                    />
                    <div className="d-flex flex-wrap gap-2 mt-2">
                      {[
                        { ok: password.length >= 8, text: '8+ chars' },
                        { ok: /[A-Z]/.test(password), text: 'Uppercase' },
                        { ok: /[0-9]/.test(password), text: 'Number' },
                        { ok: /[^A-Za-z0-9]/.test(password), text: 'Symbol' },
                      ].map((r, i) => (
                        <small key={i} className="d-flex align-items-center gap-1"
                          style={{ color: r.ok ? 'var(--color-success)' : 'var(--color-text-muted)', fontSize: '0.68rem' }}>
                          <HiCheck size={12} style={{ opacity: r.ok ? 1 : 0.3 }} /> {r.text}
                        </small>
                      ))}
                    </div>
                  </div>
                )}

                {!isRegister && (
                  <div className="d-flex justify-content-end mb-3">
                    <Button variant="link" className="p-0 text-decoration-none small"
                      style={{ color: 'var(--color-accent)', fontSize: '0.8rem', fontWeight: 500 }}>
                      Forgot password?
                    </Button>
                  </div>
                )}

                {isRegister && (
                  <Form.Group className="mb-3">
                    <Form.Check type="checkbox" id="agree-terms"
                      checked={agreeTerms} onChange={e => setAgreeTerms(e.target.checked)}
                      label={
                        <small style={{ color: 'var(--color-text-muted)', fontSize: '0.78rem' }}>
                          I agree to the <a href="#terms" style={{ color: 'var(--color-accent)' }}>Terms of Service</a> and <a href="#privacy" style={{ color: 'var(--color-accent)' }}>Privacy Policy</a>
                        </small>
                      }
                    />
                  </Form.Group>
                )}

                {error && (
                  <Alert variant="danger" className="py-2 px-3 d-flex align-items-center gap-2 fade-in" style={{ fontSize: '0.82rem', borderRadius: 'var(--radius-md)' }}>
                    <HiExclamationTriangle size={16} style={{ flexShrink: 0 }} />
                    {error}
                  </Alert>
                )}

                <Button type="submit" variant="primary" size="lg"
                  className="w-100 mt-2 fw-semibold d-flex align-items-center justify-content-center gap-2 rounded-3"
                  disabled={busy}
                  style={{ height: 48 }}
                >
                  {busy ? (
                    <><Spinner animation="border" size="sm" /> Please wait...</>
                  ) : (
                    <>{isRegister ? 'Create Account' : 'Sign In'} <HiArrowRight size={18} /></>
                  )}
                </Button>
              </Form>

              <p className="text-center mt-4 mb-0">
                <small style={{ color: 'var(--color-text-muted)' }}>
                  {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
                </small>
                <Button variant="link" className="p-0 fw-semibold text-decoration-none small"
                  style={{ color: 'var(--color-accent)' }}
                  onClick={() => { setIsRegister(!isRegister); setError(''); setAgreeTerms(false); }}
                >
                  {isRegister ? 'Sign in' : 'Create free account'}
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
        .login-page .input-group-text {
          background: var(--color-bg-surface) !important;
        }
      `}</style>
    </div>
  );
}
