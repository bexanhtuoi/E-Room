import { useState } from 'react';
import { Section, Eyebrow } from '../../components/common/UI';
import { SITE } from '../../data/site';

export function ContactPage() {
  const [form, setForm] = useState({ name: '', email: '', message: '' });
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  function submit(e) {
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim() || !form.message.trim()) { setError('Please fill name, email and message.'); return; }
    if (!/\S+@\S+\.\S+/.test(form.email)) { setError('Invalid email address.'); return; }
    setError('');
    setStatus('sending');
    setTimeout(() => setStatus('done'), 900);
  }

  return (
    <div>
      <Section>
        <div style={{ maxWidth: 640, margin: '0 auto' }}>
          <div className="er-center">
            <Eyebrow>Contact</Eyebrow>
            <h1 style={{ fontSize: 'clamp(30px,4vw,46px)', lineHeight: 1.05, letterSpacing: '-0.02em', margin: '0 0 12px', color: '#000' }}>Talk to a human.</h1>
            <p className="er-sub">We reply within 1 business day.</p>
          </div>

          <div style={{ marginTop: 32, borderTop: '2px solid #111' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, padding: '16px 0', borderBottom: '1px solid #e8e8e8', flexWrap: 'wrap' }}>
              <strong>Hotline</strong><span>{SITE.hotline} • {SITE.hotlineHours}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, padding: '16px 0', borderBottom: '1px solid #e8e8e8', flexWrap: 'wrap' }}>
              <strong>Email</strong><span>{SITE.supportEmail}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, padding: '16px 0', borderBottom: '1px solid #e8e8e8', flexWrap: 'wrap' }}>
              <strong>Office</strong><span style={{ textAlign: 'right', maxWidth: 360 }}>{SITE.address}</span>
            </div>
          </div>

          <form onSubmit={submit} style={{ display: 'grid', gap: 14, marginTop: 32 }}>
            <div><label className="er-label">Name *</label><input className="er-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Your name" /></div>
            <div><label className="er-label">Email *</label><input className="er-input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@email.com" /></div>
            <div><label className="er-label">Message *</label><textarea className="er-textarea" rows={5} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} placeholder="How can we help?" /></div>
            {error && <div className="er-alert er-alert--err">{error}</div>}
            {status === 'done' && <div className="er-alert er-alert--ok">Sent. We will reply within 1 business day.</div>}
            <button className="er-btn" type="submit" disabled={status === 'sending'} style={{ justifyContent: 'center' }}>{status === 'sending' ? 'Sending…' : 'Send message →'}</button>
          </form>
        </div>
      </Section>
    </div>
  );
}
