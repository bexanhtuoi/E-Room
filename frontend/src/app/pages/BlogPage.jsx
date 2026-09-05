import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Section, Eyebrow, Card } from '../../components/common/UI';
import { BLOG_POSTS } from '../../data/site';

export function BlogPage() {
  const [q, setQ] = useState('');
  const [cat, setCat] = useState('All');
  const cats = ['All', ...new Set(BLOG_POSTS.map((p) => p.category))];
  const list = BLOG_POSTS.filter((p) => (cat === 'All' || p.category === cat) && (!q || (p.title + p.excerpt).toLowerCase().includes(q.toLowerCase())));
  const [lead, ...rest] = list;

  return (
    <div>
      <Section>
        <div style={{ border: '2px solid #111', background: '#111', color: '#fff', padding: 'clamp(24px,4vw,40px)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 20, flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.14em' }}>THE E-ROOM JOURNAL</div>
            <h1 style={{ fontSize: 'clamp(28px,4vw,44px)', lineHeight: 1.05, margin: '10px 0 8px' }}>Speaking tactics,<br />weekly.</h1>
            <p style={{ color: '#bbb', margin: 0, maxWidth: 520 }}>Room routines, hosting guides and conversation tactics from hosts and regulars.</p>
          </div>
          <div style={{ display: 'flex', gap: 0, border: '1px solid #fff' }}>
            {[['8', 'guides'], ['4', 'topics'], ['6 min', 'avg read']].map(([v, l], i) => (
              <div key={l} style={{ padding: '12px 18px', borderLeft: i ? '1px solid #fff' : 'none', textAlign: 'center' }}>
                <div style={{ fontWeight: 800, fontSize: 18 }}>{v}</div><div style={{ fontSize: 11, color: '#bbb' }}>{l}</div>
              </div>
            ))}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 24, flexWrap: 'wrap' }}>
          {cats.map((c) => (
            <button key={c} className={`er-btn${c === cat ? '' : ' er-btn--ghost'}`} style={{ padding: '10px 14px' }} onClick={() => setCat(c)}>{c}</button>
          ))}
          <input className="er-input" style={{ maxWidth: 260 }} placeholder="Search articles…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        {lead && (
          <Card key={lead.slug} style={{ marginTop: 24, padding: 28 }}>
            <span className="er-tag">{lead.category}</span>
            <h3 style={{ fontSize: 28 }}><Link to={`/blog/${lead.slug}`} style={{ color: '#111' }}>{lead.title}</Link></h3>
            <p>{lead.excerpt}</p>
            <p style={{ marginTop: 10, fontSize: 13, color: '#666' }}>{lead.author} • {lead.date} • {lead.readTime}</p>
          </Card>
        )}
        <div className="er-grid er-grid--3" style={{ marginTop: 16 }}>
          {rest.map((p) => (
            <Card key={p.slug}>
              <span className="er-tag">{p.category}</span>
              <h3><Link to={`/blog/${p.slug}`} style={{ color: '#111' }}>{p.title}</Link></h3>
              <p>{p.excerpt}</p>
              <p style={{ marginTop: 10, fontSize: 13, color: '#666' }}>{p.author} • {p.readTime}</p>
            </Card>
          ))}
        </div>
        {list.length === 0 && <div className="er-alert" style={{ marginTop: 24 }}>No articles found. Try another keyword.</div>}
      </Section>
      <Section soft>
        <Card ink>
          <h3 style={{ fontSize: 28 }}>Get one speaking tip every Monday.</h3>
          <p>Short emails, no spam. Unsubscribe anytime.</p>
          <form style={{ display: 'flex', gap: 8, marginTop: 16, flexWrap: 'wrap' }} onSubmit={(e) => e.preventDefault()}>
            <input className="er-input" style={{ maxWidth: 320, background: '#fff' }} placeholder="you@email.com" type="email" required />
            <button className="er-btn" style={{ background: '#fff', color: '#111', borderColor: '#fff' }} type="submit">Subscribe</button>
          </form>
        </Card>
      </Section>
    </div>
  );
}
