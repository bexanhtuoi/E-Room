import { useState } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import Spinner from 'react-bootstrap/Spinner';
import Alert from 'react-bootstrap/Alert';
import { HiCheckCircle, HiLockClosed, HiArrowLeft } from 'react-icons/hi2';
import { fetchJson } from '../../lib/api';
import { queryClient } from '../../lib/queryClient';

const PLANS = {
  pro: {
    name: 'Pro', price: 9.99, period: 'month',
    features: ['Unlimited rooms', 'Full recaps + notes history', 'Priority matching', 'Create private rooms', 'Longer room timers'],
  },
  pro_plus: {
    name: 'Pro+', price: 19.99, period: 'month',
    features: ['Everything in Pro', 'Voice playback of recaps', 'Smarter @ai answers', 'Up to 4 seats + guest invites', 'Team analytics'],
  },
};

function formatCardNumber(value) {
  const digits = value.replace(/\D/g, '').slice(0, 16);
  return digits.replace(/(\d{4})/g, '$1 ').trim();
}

function formatExpiry(value) {
  const digits = value.replace(/\D/g, '').slice(0, 4);
  if (digits.length > 2) return digits.slice(0, 2) + '/' + digits.slice(2);
  return digits;
}

export function PaymentPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const selectedPlan = searchParams.get('plan') || 'pro';
  const plan = PLANS[selectedPlan] || PLANS.pro;

  const [form, setForm] = useState({
    name: '',
    cardNumber: '',
    expiry: '',
    cvc: '',
  });
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');

  const paymentMutation = useMutation({
    mutationFn: (data) => fetchJson('/subscriptions/create', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscription'] });
      setDone(true);
    },
    onError: (err) => {
      setError(err?.message || 'Payment failed. Please try again.');
    },
  });

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    setError('');

    const cardClean = form.cardNumber.replace(/\s/g, '');
    if (cardClean.length < 13) { setError('Invalid card number'); return; }
    if (form.expiry.length < 5) { setError('Invalid expiry date'); return; }
    if (form.cvc.length < 3) { setError('Invalid CVC'); return; }
    if (!form.name.trim()) { setError('Cardholder name is required'); return; }

    paymentMutation.mutate({
      plan: selectedPlan,
      card_number: cardClean,
      expiry: form.expiry,
      cvc: form.cvc,
      cardholder_name: form.name,
    });
  }

  if (done) {
    return (
      <Container className="py-5 text-center">
        <div style={{ maxWidth: 400, margin: '0 auto' }}>
          <div style={{ marginBottom: 8 }}>
            <HiCheckCircle size={36} style={{ color: 'var(--color-success)' }} />
          </div>
          <h3 style={{ fontWeight: 700, margin: '0 0 8px', color: 'var(--color-text-primary)', fontSize: '1.15rem' }}>Payment successful!</h3>
          <p className="text-muted mb-4" style={{ fontSize: '0.85rem' }}>
            You are now on the <strong>{plan.name}</strong> plan.
          </p>
          <div className="d-flex gap-2 justify-content-center">
            <Link to="/profile">
              <Button variant="outline-primary" className="px-4">Manage subscription</Button>
            </Link>
            <Link to="/">
              <Button variant="primary" className="px-4 fw-semibold">Go to dashboard</Button>
            </Link>
          </div>
        </div>
      </Container>
    );
  }

  return (
    <main className="fade-in" style={{ minHeight: 'calc(100dvh - 72px)', background: 'var(--color-bg)' }}>
      <Container className="py-4">
        <div style={{ maxWidth: 960, margin: '0 auto' }}>
          <div style={{ marginBottom: 32 }}>
            <h2 style={{ fontWeight: 800, margin: '0 0 4px', color: 'var(--color-text-primary)', fontSize: '1.35rem' }}>Complete your subscription</h2>
            <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem', margin: 0 }}>
              Upgrading to <strong style={{ color: 'var(--color-accent)' }}>{plan.name}</strong>
            </p>
          </div>

          <Row>
            <Col lg={5} className="mb-4 mb-lg-0">
              <div>
                <div className="d-flex align-items-center gap-2 mb-3">
                  <span style={{
                    display: 'inline-flex', padding: '2px 10px',
                    background: selectedPlan === 'pro_plus' ? 'var(--color-success-muted)' : 'var(--color-accent-muted)',
                    color: selectedPlan === 'pro_plus' ? 'var(--color-success)' : 'var(--color-accent)',
                    fontSize: '0.72rem', fontWeight: 700,
                  }}>
                    {plan.name}
                  </span>
                  {selectedPlan === 'pro_plus' && (
                    <span style={{
                      display: 'inline-flex', padding: '2px 8px',
                      fontSize: '0.65rem', fontWeight: 700,
                      background: 'var(--color-warning-muted)', color: 'var(--color-warning)',
                    }}>BEST VALUE</span>
                  )}
                </div>
                <div className="mb-3">
                  <strong style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--color-text-primary)', lineHeight: 1 }}>${plan.price}</strong>
                  <span style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', marginLeft: 4 }}>/{plan.period}</span>
                </div>
                <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 16px', fontSize: '0.85rem' }}>
                  {plan.features.map((f) => (
                    <li key={f} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, color: 'var(--color-text-secondary)' }}>
                      <HiCheckCircle size={14} style={{ color: 'var(--color-success)', flexShrink: 0 }} />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
                <Link to="/pricing" style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: 'var(--color-text-muted)', fontSize: '0.8rem', fontWeight: 600, textDecoration: 'none' }}>
                  <HiArrowLeft size={12} /> Change plan
                </Link>
              </div>
            </Col>

            <Col lg={7}>
              <div>
                <h5 style={{ fontWeight: 700, marginBottom: 20, color: 'var(--color-text-primary)', fontSize: '0.95rem' }}>
                  Payment details
                </h5>

                <Form onSubmit={handleSubmit}>
                  {error && <Alert variant="danger" className="py-2 small">{error}</Alert>}

                  <Form.Group className="mb-3">
                    <Form.Label className="fw-semibold small text-muted" style={{ fontSize: '0.78rem' }}>Cardholder name</Form.Label>
                    <Form.Control
                      type="text" placeholder="John Doe" required
                      value={form.name}
                      onChange={(e) => updateField('name', e.target.value)}
                    />
                  </Form.Group>

                  <Form.Group className="mb-3">
                    <Form.Label className="fw-semibold small text-muted" style={{ fontSize: '0.78rem' }}>Card number</Form.Label>
                    <Form.Control
                      type="text" placeholder="4242 4242 4242 4242"
                      value={form.cardNumber}
                      onChange={(e) => updateField('cardNumber', formatCardNumber(e.target.value))}
                      maxLength={19} required
                    />
                  </Form.Group>

                  <Row>
                    <Col md={6} className="mb-3">
                      <Form.Label className="fw-semibold small text-muted" style={{ fontSize: '0.78rem' }}>Expiry</Form.Label>
                      <Form.Control
                        type="text" placeholder="MM/YY"
                        value={form.expiry}
                        onChange={(e) => updateField('expiry', formatExpiry(e.target.value))}
                        maxLength={5} required
                      />
                    </Col>
                    <Col md={6} className="mb-3">
                      <Form.Label className="fw-semibold small text-muted" style={{ fontSize: '0.78rem' }}>CVC</Form.Label>
                      <Form.Control
                        type="text" placeholder="123"
                        value={form.cvc}
                        onChange={(e) => updateField('cvc', e.target.value.replace(/\D/g, '').slice(0, 3))}
                        maxLength={3} required
                      />
                    </Col>
                  </Row>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', marginTop: 8, borderTop: '1px solid var(--color-border)' }}>
                    <div>
                      <div style={{ color: 'var(--color-text-primary)', fontWeight: 700, fontSize: '0.9rem' }}>Total</div>
                      <small style={{ color: 'var(--color-text-muted)', fontSize: '0.78rem' }}>Billed monthly, cancel anytime</small>
                    </div>
                    <div style={{ color: 'var(--color-text-primary)', fontSize: '1.4rem', fontWeight: 800 }}>${plan.price}</div>
                  </div>

                  <Button
                    type="submit"
                    variant="primary"
                    size="lg"
                    className="w-100 mt-3 fw-semibold"
                    style={{ height: 48, fontSize: '0.95rem' }}
                    disabled={paymentMutation.isPending}
                  >
                    {paymentMutation.isPending ? (
                      <><Spinner animation="border" size="sm" className="me-2" /> Processing...</>
                    ) : `Pay $${plan.price}`}
                  </Button>

                  <p style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, marginTop: 14, color: 'var(--color-text-muted)', fontSize: '0.78rem', fontWeight: 600 }}>
                    <HiLockClosed size={14} /> Secured by Stripe
                  </p>
                </Form>
              </div>
            </Col>
          </Row>
        </div>
      </Container>
    </main>
  );
}
