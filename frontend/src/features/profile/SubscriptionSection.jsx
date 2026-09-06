import { Link } from 'react-router-dom';

const PLANS = [
  { key: 'free', name: 'Starter', price: '$0', features: ['5 rooms/week', 'Live transcripts', 'Meeting recaps'] },
  { key: 'pro', name: 'Pro', price: '$9.99/mo', features: ['Unlimited rooms', 'Full recaps + history', 'Priority matching', 'Private rooms'], popular: true },
  { key: 'pro_plus', name: 'Pro+', price: '$19.99/mo', features: ['All Pro features', 'Voice playback', 'Smarter @ai answers', 'Guest invites'] },
];

export function SubscriptionSection({ tier }) {
  return (
    <section className="portal-panel">
      <div className="portal-panel__head">
        <h2>Subscription</h2>
        <Link className="er-btn er-btn--ghost portal-mini-btn" style={{ textDecoration: 'none' }} to="/pricing">Compare plans</Link>
      </div>
      <div className="portal-plans">
        {PLANS.map((plan) => {
          const current = plan.key === tier;
          return (
            <div key={plan.key} className={`portal-plan${current ? ' is-current' : ''}`}>
              <div className="portal-plan__top">
                <strong>{plan.name}</strong>
                {current
                  ? <span className="portal-flag is-solid">CURRENT</span>
                  : plan.popular && <span className="portal-flag">POPULAR</span>}
              </div>
              <div className="portal-plan__price">{plan.price}</div>
              <ul className="portal-plan__features">
                {plan.features.map((f) => <li key={f}>{f}</li>)}
              </ul>
              <div className="portal-plan__cta">
                {plan.key === 'free'
                  ? <button className="er-btn er-btn--ghost" style={{ width: '100%', justifyContent: 'center' }} disabled={current}>Free plan</button>
                  : <Link className="er-btn" style={{ width: '100%', justifyContent: 'center', textDecoration: 'none' }} to={`/payment?plan=${plan.key}`}>{current ? 'Manage plan' : 'Upgrade'}</Link>}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
