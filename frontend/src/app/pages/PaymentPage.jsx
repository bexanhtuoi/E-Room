import { useState } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Card from 'react-bootstrap/Card';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import Spinner from 'react-bootstrap/Spinner';
import Alert from 'react-bootstrap/Alert';
import { HiCreditCard, HiCheckCircle, HiLockClosed, HiArrowLeft } from 'react-icons/hi2';
import { fetchJson } from '../../lib/api';
import { queryClient } from '../../lib/queryClient';

const PLANS = {
  pro: {
    name: 'Pro', price: 9.99, period: 'month',
    features: ['Unlimited AI corrections', 'Advanced AI feedback', 'Priority matching', '3 heartbeats per room', 'Web Search Expert'],
    color: 'primary',
  },
  pro_plus: {
    name: 'Pro+', price: 19.99, period: 'month',
    features: ['Everything in Pro', 'TTS pronunciation', 'Full RAG + Web Expert', 'Auto session notes', 'Room series', 'Leaderboard', 'Up to 15 participants'],
    color: 'success',
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
      <Container className="py-5">
        <div className="text-center" style={{ maxWidth: 480, margin: '0 auto' }}>
          <div style={{
            width: 72, height: 72, borderRadius: '50%',
            background: 'var(--color-success-muted)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 16px',
          }}>
            <HiCheckCircle size={40} style={{ color: 'var(--color-success)' }} />
          </div>
          <h3 className="fw-extrabold mb-2" style={{ fontFamily: 'Nunito, sans-serif' }}>Payment Successful!</h3>
          <p className="text-muted mb-4">
            You're now on the <strong>{plan.name}</strong> plan. Welcome aboard! 🎉
          </p>
          <div className="d-flex gap-2 justify-content-center">
            <Link to="/profile">
              <Button variant="outline-primary" className="rounded-pill">Manage Subscription</Button>
            </Link>
            <Link to="/">
              <Button variant="primary" className="rounded-pill fw-semibold px-4">Go to Dashboard</Button>
            </Link>
          </div>
        </div>
      </Container>
    );
  }

  return (
    <div className="payment-page fade-in">
      <Container className="py-4">
        <div style={{ maxWidth: 900, margin: '0 auto' }}>
          <div className="text-center mb-4">
            <HiCreditCard size={40} className="mb-2" style={{ color: 'var(--color-accent)' }} />
            <h2 className="fw-extrabold mb-1" style={{ fontFamily: 'Nunito, sans-serif' }}>Complete Subscription</h2>
            <p className="text-muted">
              Upgrading to <span className="fw-bold" style={{ color: 'var(--color-accent)' }}>{plan.name}</span>
            </p>
          </div>

          <Row>
            {/* Plan summary */}
            <Col lg={5} className="mb-4 mb-lg-0">
              <Card className="border-0 h-100" style={{ background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)' }}>
                <Card.Body className="p-4 d-flex flex-column">
                  <div className="d-flex align-items-center gap-2 mb-3">
                    <span style={{
                      padding: '2px 10px', borderRadius: 99,
                      background: selectedPlan === 'pro_plus' ? 'var(--color-success-muted)' : 'var(--color-accent-muted)',
                      color: selectedPlan === 'pro_plus' ? 'var(--color-success)' : 'var(--color-accent)',
                      fontSize: '0.72rem', fontWeight: 700,
                    }}>
                      {plan.name}
                    </span>
                    {selectedPlan === 'pro_plus' && (
                      <span style={{ padding: '2px 8px', borderRadius: 99, background: 'var(--color-warning-muted)', color: 'var(--color-warning)', fontSize: '0.65rem', fontWeight: 700 }}>
                        BEST VALUE
                      </span>
                    )}
                  </div>
                  <div className="mb-3">
                    <span className="fw-bold" style={{ fontSize: '2rem', fontFamily: 'Nunito, sans-serif' }}>
                      ${plan.price}
                    </span>
                    <span className="text-muted" style={{ fontSize: '0.85rem' }}>/{plan.period}</span>
                  </div>
                  <ul className="list-unstyled flex-grow-1" style={{ fontSize: '0.85rem' }}>
                    {plan.features.map((f) => (
                      <li key={f} className="mb-2 d-flex align-items-center gap-2">
                        <HiCheckCircle size={14} style={{ color: 'var(--color-success)', flexShrink: 0 }} />
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                  <Link to="/pricing" className="small text-decoration-none"
                    style={{ color: 'var(--color-accent)' }}>
                    <HiArrowLeft size={12} className="me-1" />
                    Change plan
                  </Link>
                </Card.Body>
              </Card>
            </Col>

            {/* Payment form */}
            <Col lg={7}>
              <Card style={{ background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)' }}>
                <Card.Body className="p-4">
                  <h5 className="fw-bold mb-4 d-flex align-items-center gap-2">
                    <HiCreditCard size={20} style={{ color: 'var(--color-accent)' }} />
                    Payment Details
                  </h5>

                  <Form onSubmit={handleSubmit}>
                    {error && <Alert variant="danger" className="py-2 small">{error}</Alert>}

                    <Form.Group className="mb-3">
                      <Form.Label className="fw-semibold small text-muted">Cardholder Name</Form.Label>
                      <Form.Control
                        type="text" placeholder="John Doe" required
                        value={form.name}
                        onChange={(e) => updateField('name', e.target.value)}
                        className="rounded-3" style={{ fontSize: '0.88rem' }}
                      />
                    </Form.Group>

                    <Form.Group className="mb-3">
                      <Form.Label className="fw-semibold small text-muted">Card Number</Form.Label>
                      <Form.Control
                        type="text" placeholder="4242 4242 4242 4242"
                        value={form.cardNumber}
                        onChange={(e) => updateField('cardNumber', formatCardNumber(e.target.value))}
                        maxLength={19} required className="rounded-3" style={{ fontSize: '0.88rem' }}
                      />
                    </Form.Group>

                    <Row>
                      <Col md={6} className="mb-3">
                        <Form.Label className="fw-semibold small text-muted">Expiry</Form.Label>
                        <Form.Control
                          type="text" placeholder="MM/YY"
                          value={form.expiry}
                          onChange={(e) => updateField('expiry', formatExpiry(e.target.value))}
                          maxLength={5} required className="rounded-3" style={{ fontSize: '0.88rem' }}
                        />
                      </Col>
                      <Col md={6} className="mb-3">
                        <Form.Label className="fw-semibold small text-muted">CVC</Form.Label>
                        <Form.Control
                          type="text" placeholder="123"
                          value={form.cvc}
                          onChange={(e) => updateField('cvc', e.target.value.replace(/\D/g, '').slice(0, 3))}
                          maxLength={3} required className="rounded-3" style={{ fontSize: '0.88rem' }}
                        />
                      </Col>
                    </Row>

                    <div className="d-flex justify-content-between align-items-center border-top pt-3"
                      style={{ borderColor: 'var(--color-border)' }}>
                      <div>
                        <div className="fw-bold">Total</div>
                        <small className="text-muted">Billed monthly, cancel anytime</small>
                      </div>
                      <div className="fw-bold" style={{ fontSize: '1.2rem', fontFamily: 'Nunito, sans-serif' }}>
                        ${plan.price}
                      </div>
                    </div>

                    <Button
                      type="submit"
                      variant="primary"
                      size="lg"
                      className="rounded-pill w-100 mt-3 fw-semibold"
                      disabled={paymentMutation.isPending}
                      style={{ minHeight: 48 }}
                    >
                      {paymentMutation.isPending ? (
                        <><Spinner animation="border" size="sm" className="me-2" /> Processing...</>
                      ) : `Pay $${plan.price}`}
                    </Button>

                    <p className="text-muted text-center small mt-2 mb-0 d-flex align-items-center justify-content-center gap-1">
                      <HiLockClosed size={14} /> Secured by Stripe
                    </p>
                  </Form>
                </Card.Body>
              </Card>
            </Col>
          </Row>
        </div>
      </Container>
    </div>
  );
}
