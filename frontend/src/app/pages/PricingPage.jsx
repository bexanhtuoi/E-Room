import { Link } from 'react-router-dom';
import Container from 'react-bootstrap/Container';
import Button from 'react-bootstrap/Button';
import Badge from 'react-bootstrap/Badge';
import { HiCheckCircle, HiCurrencyDollar, HiShieldCheck, HiSparkles, HiUserGroup } from 'react-icons/hi2';
import '../../styles/MarketingPages.css';

const plans = [
  {
    key: 'free',
    name: 'Starter',
    price: '$0',
    note: 'For getting used to live English rooms.',
    features: ['Join public meeting rooms', 'Basic AI correction cards', 'Standard room discovery', 'Limited daily room creation'],
  },
  {
    key: 'pro',
    name: 'Pro',
    price: '$9.99',
    period: '/month',
    note: 'For learners who practice every week.',
    badge: 'Most practical',
    features: ['Unlimited speaking rooms', 'Advanced AI feedback', 'Priority matching', 'Session notes', 'More room heartbeats'],
  },
  {
    key: 'pro_plus',
    name: 'Pro+',
    price: '$19.99',
    period: '/month',
    note: 'For interview prep, cohorts, and serious study.',
    badge: 'Full access',
    features: ['Everything in Pro', 'TTS pronunciation feedback', 'Expert RAG insights', 'Leaderboard access', 'Up to 15 participants'],
  },
];

export function PricingPage() {
  return (
    <main className="marketing-page pricing-page fade-in">
      <Container className="marketing-page__container">
        <section className="pricing-hero">
          <div className="pricing-hero__coin" aria-hidden="true"><HiCurrencyDollar size={40} /></div>
          <span className="marketing-eyebrow">Pricing</span>
          <h1>Choose the speaking plan that matches your practice rhythm.</h1>
          <p>Start free, then upgrade only when you need deeper feedback, session notes, and advanced room tools. Payment starts after you select a plan.</p>
        </section>

        <section className="pricing-grid" aria-label="Subscription plans">
          {plans.map((plan) => (
            <article className={`pricing-card ${plan.badge ? 'is-featured' : ''}`} key={plan.key}>
              <div className="pricing-card__header">
                <div>
                  <h2>{plan.name}</h2>
                  <p>{plan.note}</p>
                </div>
                {plan.badge && <Badge bg="primary">{plan.badge}</Badge>}
              </div>
              <div className="pricing-card__price">
                <strong>{plan.price}</strong>
                {plan.period && <span>{plan.period}</span>}
              </div>
              <ul>
                {plan.features.map((feature) => <li key={feature}><HiCheckCircle size={16} />{feature}</li>)}
              </ul>
              {plan.key === 'free' ? (
                <Button as={Link} to="/learning" variant="outline-primary" className="rounded-pill w-100 fw-semibold">Start free</Button>
              ) : (
                <Button as={Link} to={`/payment?plan=${plan.key}`} variant={plan.badge ? 'primary' : 'outline-primary'} className="rounded-pill w-100 fw-semibold">Choose {plan.name}</Button>
              )}
            </article>
          ))}
        </section>

        <section className="pricing-proof">
          <article><HiShieldCheck size={22} /><strong>No forced upgrade</strong><span>Free users still join real speaking rooms.</span></article>
          <article><HiSparkles size={22} /><strong>AI depth scales</strong><span>Paid plans unlock stronger feedback and notes.</span></article>
          <article><HiUserGroup size={22} /><strong>Built for groups</strong><span>Pro+ supports larger rooms and rankings.</span></article>
        </section>
      </Container>
    </main>
  );
}
