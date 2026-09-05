import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Section, Eyebrow, Card, FaqList } from '../../components/common/UI';
import { PLANS, BILLING_FAQS } from '../../data/site';

const COMPARE_ROWS = [
  ['Public rooms / week', '5 rooms', 'Unlimited', 'Unlimited'],
  ['Live transcripts', '✓', '✓', '✓'],
  ['Meeting recaps', 'Basic', 'Full + notes history', 'Full + voice playback'],
  ['@ai answers in room', 'Standard', 'Standard', 'Smarter + longer context'],
  ['Room size', 'Up to 4', 'Up to 4', 'Up to 4 + guests'],
  ['Create private rooms', '—', '✓', '✓'],
  ['Session history', 'Last 5 rooms', 'Unlimited', 'Unlimited + analytics'],
  ['Priority matching', '—', '✓', '✓ First in queue'],
];

export function PricingPage() {
  const [yearly, setYearly] = useState(false);

  function price(p) {
    if (p.key === 'free') return p.price;
    if (!yearly) return p.price;
    const m = parseFloat(p.price.replace('$', ''));
    return `$${(m * 0.8).toFixed(2)}`;
  }

  return (
    <div>
      {/* Header riêng: bảng giá + toggle, không dùng chữ khổng lồ */}
      <Section>
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 32, alignItems: 'end' }} className="pricing-head">
          <div>
            <Eyebrow>Pricing</Eyebrow>
            <h1 style={{ fontSize: 'clamp(30px,4vw,48px)', lineHeight: 1.05, letterSpacing: '-0.02em', margin: '0 0 12px', color: '#000' }}>Pay only when practice becomes a habit.</h1>
            <p className="er-sub">Start free with real rooms. Upgrade for full reports, notes and bigger rooms. Cancel anytime, history stays saved.</p>
          </div>
          <div style={{ border: '1px solid #111', padding: 18, background: '#f7f7f7' }}>
            <div style={{ display: 'flex', border: '1px solid #111', background: '#fff' }}>
              {[false, true].map((y) => (
                <button key={String(y)} onClick={() => setYearly(y)} style={{ flex: 1, padding: '12px 0', fontWeight: 800, fontSize: 14, background: yearly === y ? '#111' : '#fff', color: yearly === y ? '#fff' : '#111', border: 'none', cursor: 'pointer' }}>
                  {y ? 'Yearly −20%' : 'Monthly'}
                </button>
              ))}
            </div>
            <p style={{ fontSize: 13, color: '#666', margin: '12px 0 0' }}>Yearly billing saves 20% on Pro and Pro+. Switch anytime via {<strong style={{ color: '#111' }}>support@e-room.app</strong>}.</p>
          </div>
        </div>

        <div className="er-grid er-grid--3" style={{ marginTop: 40, alignItems: 'stretch' }}>
          {PLANS.map((p) => {
            const popular = p.key === 'pro';
            return (
              <Card key={p.key} style={{ padding: 30, display: 'flex', flexDirection: 'column', border: popular ? '2px solid #111' : '1px solid #e8e8e8', position: 'relative' }}>
                {p.badge && <span style={{ position: 'absolute', top: -14, left: 24, fontSize: 12, fontWeight: 800, background: '#111', color: '#fff', padding: '5px 10px' }}>{p.badge}</span>}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="er-tag">{p.name}</span>
                </div>
                <div style={{ margin: '18px 0 4px' }}><span style={{ fontSize: 52, fontWeight: 800, color: '#000' }}>{price(p)}</span><span style={{ color: '#666' }}> {p.period}</span></div>
                <p style={{ fontWeight: 700, color: '#000' }}>{p.note}</p>
                <div style={{ margin: '18px 0 6px', fontSize: 13, fontWeight: 800, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                  {p.key === 'free' && 'What you get'}
                  {p.key === 'pro' && 'Everything in Starter, plus'}
                  {p.key === 'pro_plus' && 'Everything in Pro, plus'}
                </div>
                <ul style={{ margin: '0 0 22px', paddingLeft: 18, fontSize: 15, display: 'grid', gap: 9 }}>
                  {p.features.map((f) => <li key={f}>{f}</li>)}
                </ul>
                <div style={{ marginTop: 'auto' }}>
                  <Link className={`er-btn${popular ? '' : ' er-btn--ghost'}`} style={{ width: '100%', justifyContent: 'center', textDecoration: 'none' }} to="/login">{p.cta} →</Link>
                  <p style={{ fontSize: 12, color: '#888', marginTop: 10, textAlign: 'center' }}>{p.key === 'free' ? 'No credit card required.' : 'Cancel anytime. History kept.'}</p>
                </div>
              </Card>
            );
          })}
        </div>
      </Section>

      <Section soft>
        <Eyebrow>Compare plans</Eyebrow>
        <h2 className="er-h2">Starter vs Pro vs Pro+.</h2>
        <p className="er-sub">Every paid tier keeps everything from the previous one — you only gain, never lose.</p>
        <div style={{ overflowX: 'auto', marginTop: 28, border: '1px solid #111', background: '#fff' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed', fontSize: 14, minWidth: 640 }}>
            <colgroup><col style={{ width: '40%' }} /><col style={{ width: '20%' }} /><col style={{ width: '20%' }} /><col style={{ width: '20%' }} /></colgroup>
            <thead>
              <tr style={{ background: '#111', color: '#fff' }}>
                <th style={{ textAlign: 'left', padding: '14px 16px' }}>Feature</th>
                <th style={{ padding: '14px 8px', textAlign: 'center' }}>Starter</th>
                <th style={{ padding: '14px 8px', textAlign: 'center' }}>Pro</th>
                <th style={{ padding: '14px 8px', textAlign: 'center' }}>Pro+</th>
              </tr>
            </thead>
            <tbody>
              {COMPARE_ROWS.map(([f, a, b, c], i) => (
                <tr key={f} style={{ background: i % 2 ? '#f7f7f7' : '#fff', borderTop: '1px solid #e8e8e8' }}>
                  <td style={{ padding: '13px 16px', fontWeight: 700 }}>{f}</td>
                  <td style={{ padding: '13px 8px', textAlign: 'center' }}>{a}</td>
                  <td style={{ padding: '13px 8px', textAlign: 'center', fontWeight: 700 }}>{b}</td>
                  <td style={{ padding: '13px 8px', textAlign: 'center' }}>{c}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="er-grid er-grid--3" style={{ marginTop: 16 }}>
          {[['No forced upgrade', 'Free users still join real rooms with transcripts.'], ['AI scales with you', 'Paid plans unlock longer history, smarter @ai answers and voice playback.'], ['Built for hosts', 'Pro+ adds guest invites, clubs and team analytics.']].map(([t, d]) => (
            <Card key={t}><h3>{t}</h3><p>{d}</p></Card>
          ))}
        </div>
      </Section>

      <Section>
        <div style={{ maxWidth: 800 }}>
          <Eyebrow>Billing FAQ</Eyebrow>
          <h2 className="er-h2">Questions, answered.</h2>
          <div style={{ marginTop: 24 }}><FaqList items={BILLING_FAQS} /></div>
        </div>
      </Section>
    </div>
  );
}
