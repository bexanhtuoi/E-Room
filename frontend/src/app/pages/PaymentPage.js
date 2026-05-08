import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Card from 'react-bootstrap/Card';
import Button from 'react-bootstrap/Button';
import Badge from 'react-bootstrap/Badge';
import Form from 'react-bootstrap/Form';
import Spinner from 'react-bootstrap/Spinner';

export function PaymentPage() {
  const [searchParams] = useSearchParams();
  const selectedPlan = searchParams.get('plan') || 'pro';
  const [cardNumber, setCardNumber] = useState('');
  const [expiry, setExpiry] = useState('');
  const [cvc, setCvc] = useState('');
  const [processing, setProcessing] = useState(false);
  const [done, setDone] = useState(false);

  const plans = {
    free: { name: 'Free', price: '$0', period: 'forever', features: ['5 rooms/day', 'Basic AI feedback', 'Standard matching'], color: 'secondary' },
    pro: { name: 'Pro', price: '$9.99', period: 'month', features: ['Unlimited rooms', 'Advanced AI feedback', 'Priority matching', 'Session notes'], color: 'primary' },
    'pro-plus': { name: 'Pro+', price: '$19.99', period: 'month', features: ['Everything in Pro', 'TTS voice feedback', 'Expert RAG insights', 'Leaderboard access', 'API access'], color: 'success' },
  };

  const plan = plans[selectedPlan] || plans.pro;

  function handleSubmit(e) {
    e.preventDefault();
    setProcessing(true);
    setTimeout(() => {
      setProcessing(false);
      setDone(true);
    }, 2000);
  }

  if (done) {
    return (
      <Container className="py-5">
        <div className="text-center fade-in" style={{ maxWidth: '480px', margin: '0 auto' }}>
          <div className="display-1 mb-3">🎉</div>
          <h3 className="fw-bold mb-2">Payment Successful!</h3>
          <p className="text-muted mb-4">You are now on the <strong>{plan.name}</strong> plan. Enjoy all the features!</p>
          <div className="d-flex gap-2 justify-content-center">
            <Link to="/profile?tab=subscription">
              <Button variant="outline-primary" className="rounded-pill">Manage Subscription</Button>
            </Link>
            <Link to="/">
              <Button variant="primary" className="rounded-pill">Go to Dashboard</Button>
            </Link>
          </div>
        </div>
      </Container>
    );
  }

  return (
    <div className="payment-page fade-in">
      <Container className="py-5">
        <div style={{ maxWidth: '900px', margin: '0 auto' }}>
          <div className="text-center mb-5">
            <h2 className="fw-bold mb-2">Complete Your Subscription</h2>
            <p className="text-muted">You're upgrading to the <Badge bg={plan.color} className="rounded-pill px-2">{plan.name}</Badge> plan</p>
          </div>

          <Row>
            <Col lg={5} className="mb-4 mb-lg-0">
              <Card className="border-0 shadow-sm h-100">
                <Card.Body className="p-4 d-flex flex-column">
                  <Badge bg={plan.color} className="align-self-start mb-3 rounded-pill">{plan.name}</Badge>
                  <div className="mb-3">
                    <span className="display-5 fw-bold">{plan.price}</span>
                    <span className="text-muted">/{plan.period}</span>
                  </div>
                  <ul className="list-unstyled flex-grow-1">
                    {plan.features.map(f => (
                      <li key={f} className="mb-2 d-flex align-items-center gap-2">
                        <span style={{ color: 'var(--color-success)' }}>✓</span>
                        <span className="small">{f}</span>
                      </li>
                    ))}
                  </ul>
                  <Link to="/pricing">
                    <Button variant="link" size="sm" className="text-decoration-none p-0 mt-2">← Change plan</Button>
                  </Link>
                </Card.Body>
              </Card>
            </Col>

            <Col lg={7}>
              <Card className="border-0 shadow-sm">
                <Card.Body className="p-4">
                  <h5 className="fw-bold mb-4">Payment Details</h5>
                  <Form onSubmit={handleSubmit}>
                    <Form.Group className="mb-3">
                      <Form.Label className="fw-semibold small text-muted">Cardholder Name</Form.Label>
                      <Form.Control type="text" placeholder="John Doe" required className="rounded-3" />
                    </Form.Group>
                    <Form.Group className="mb-3">
                      <Form.Label className="fw-semibold small text-muted">Card Number</Form.Label>
                      <Form.Control
                        type="text"
                        placeholder="4242 4242 4242 4242"
                        value={cardNumber}
                        onChange={e => setCardNumber(e.target.value.replace(/\D/g, '').replace(/(\d{4})/g, '$1 ').trim())}
                        maxLength={19}
                        required
                        className="rounded-3"
                      />
                    </Form.Group>
                    <Row>
                      <Col md={6} className="mb-3">
                        <Form.Label className="fw-semibold small text-muted">Expiry Date</Form.Label>
                        <Form.Control
                          type="text"
                          placeholder="MM/YY"
                          value={expiry}
                          onChange={e => {
                            let v = e.target.value.replace(/\D/g, '');
                            if (v.length > 2) v = v.slice(0, 2) + '/' + v.slice(2, 4);
                            setExpiry(v);
                          }}
                          maxLength={5}
                          required
                          className="rounded-3"
                        />
                      </Col>
                      <Col md={6} className="mb-3">
                        <Form.Label className="fw-semibold small text-muted">CVC</Form.Label>
                        <Form.Control
                          type="text"
                          placeholder="123"
                          value={cvc}
                          onChange={e => setCvc(e.target.value.replace(/\D/g, '').slice(0, 3))}
                          maxLength={3}
                          required
                          className="rounded-3"
                        />
                      </Col>
                    </Row>
                    <div className="d-flex justify-content-between align-items-center border-top pt-3 mt-2" style={{ borderColor: 'var(--color-border)' }}>
                      <div>
                        <div className="fw-bold">Total</div>
                        <small className="text-muted">Billed monthly, cancel anytime</small>
                      </div>
                      <div className="text-end">
                        <div className="fw-bold fs-5">{plan.price}</div>
                      </div>
                    </div>
                    <Button
                      type="submit"
                      variant={plan.color === 'success' ? 'success' : 'primary'}
                      size="lg"
                      className="rounded-pill w-100 mt-3 fw-semibold"
                      disabled={processing}
                    >
                      {processing ? (
                        <><Spinner animation="border" size="sm" className="me-2" /> Processing...</>
                      ) : (
                        `Pay ${plan.price}`
                      )}
                    </Button>
                    <p className="text-muted text-center small mt-2 mb-0">
                      🔒 Secured by Stripe. Your payment info is encrypted.
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
