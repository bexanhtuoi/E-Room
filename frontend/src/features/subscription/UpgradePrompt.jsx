import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSubscriptionStore } from '../../stores/subscriptionStore';
import { HiRocketLaunch, HiXMark } from 'react-icons/hi2';

export function UpgradePrompt({ feature = 'this feature', visible, onClose }) {
  const navigate = useNavigate();
  const [selected, setSelected] = useState('pro');

  if (!visible) return null;

  const plans = [
    {
      key: 'free', name: 'Free', price: '$0', features: [
        '3 AI corrections per session',
        '1 heartbeat per room',
        'Basic matching',
        'Up to 5 participants',
      ],
      cta: 'Current plan',
      disabled: true,
    },
    {
      key: 'pro', name: 'Pro', price: '$9.99', period: '/month', features: [
        'Unlimited corrections',
        '3 heartbeats per room',
        'Web Search Expert',
        'AI room practice',
        'Up to 5 participants',
      ],
      cta: 'Upgrade to Pro',
      highlighted: true,
    },
    {
      key: 'pro_plus', name: 'Pro+', price: '$19.99', period: '/month', features: [
        'Everything in Pro',
        '5 heartbeats per room',
        'Full RAG + Web Expert',
        'TTS pronunciation',
        'Auto session notes',
        'Room series',
        'Leaderboard',
        'Up to 15 participants',
      ],
      cta: 'Go Pro+',
    },
  ];

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1060,
      background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 16,
    }}>
      <div style={{
        maxWidth: 600, width: '100%',
        background: 'var(--color-bg-elevated)',
        border: '1px solid var(--color-border-strong)',
        borderRadius: 20, padding: '28px 24px',
        boxShadow: '0 20px 60px rgba(0,0,0,0.45)',
        animation: 'scaleIn 0.25s ease',
        position: 'relative',
      }}>
        {/* Close */}
        <button onClick={onClose} style={{
          position: 'absolute', top: 14, right: 14,
          width: 28, height: 28, borderRadius: '50%',
          border: 'none', background: 'var(--color-bg-surface)',
          color: 'var(--color-text-muted)', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <HiXMark size={16} />
        </button>

        <div className="text-center mb-4">
          <HiRocketLaunch size={36} style={{ color: 'var(--color-accent)' }} />
          <h4 className="fw-extrabold mt-2 mb-1" style={{ fontFamily: 'Nunito, sans-serif' }}>
            Unlock {feature}
          </h4>
          <p className="text-muted small mb-0">
            You've reached the limit for {feature}. Upgrade to continue.
          </p>
        </div>

        {/* Plans */}
        <div style={{ display: 'flex', gap: 10 }}>
          {plans.map((plan) => {
            const isSelected = selected === plan.key;
            return (
              <div
                key={plan.key}
                onClick={() => !plan.disabled && setSelected(plan.key)}
                style={{
                  flex: 1, padding: '16px 12px', borderRadius: 14, cursor: plan.disabled ? 'default' : 'pointer',
                  background: isSelected ? 'var(--color-accent-muted)' : 'var(--color-bg-surface)',
                  border: `2px solid ${isSelected ? 'var(--color-accent)' : plan.highlighted ? 'var(--color-border-strong)' : 'var(--color-border)'}`,
                  opacity: plan.disabled ? 0.6 : 1,
                  transition: 'all 0.15s',
                  position: 'relative',
                }}
              >
                {plan.highlighted && (
                  <div style={{
                    position: 'absolute', top: -10, left: '50%', transform: 'translateX(-50%)',
                    padding: '2px 10px', borderRadius: 99,
                    background: 'var(--color-accent-gradient)',
                    color: '#fff', fontSize: '0.6rem', fontWeight: 700, whiteSpace: 'nowrap',
                  }}>
                    POPULAR
                  </div>
                )}
                <div className="fw-bold mb-2" style={{ fontSize: '0.95rem' }}>{plan.name}</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 800, fontFamily: 'Nunito, sans-serif' }}>
                  {plan.price}<span style={{ fontSize: '0.7rem', fontWeight: 400, color: 'var(--color-text-muted)' }}>{plan.period || ''}</span>
                </div>
                <ul style={{ margin: '10px 0', padding: 0, listStyle: 'none', fontSize: '0.72rem', lineHeight: 1.8, color: 'var(--color-text-secondary)' }}>
                  {plan.features.map((f, i) => (
                    <li key={i} className="d-flex align-items-center gap-1">
                      <span style={{ color: 'var(--color-success)' }}>✓</span> {f}
                    </li>
                  ))}
                </ul>
                <button
                  disabled={plan.disabled}
                  onClick={() => { if (!plan.disabled) navigate('/payment'); }}
                  style={{
                    width: '100%', padding: '8px', borderRadius: 99,
                    background: isSelected ? 'var(--color-accent-gradient)' : 'var(--color-bg-hover)',
                    color: isSelected ? '#fff' : 'var(--color-text-secondary)',
                    border: 'none', cursor: plan.disabled ? 'not-allowed' : 'pointer',
                    fontWeight: 700, fontSize: '0.78rem', fontFamily: 'inherit',
                    opacity: plan.disabled ? 0.5 : 1,
                  }}
                >
                  {plan.cta}
                </button>
              </div>
            );
          })}
        </div>

        <p className="text-muted text-center mt-3 mb-0" style={{ fontSize: '0.7rem' }}>
          7-day free trial • Cancel anytime • Secure payment
        </p>
      </div>
    </div>
  );
}
