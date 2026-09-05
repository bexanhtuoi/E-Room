import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { HiArrowRightOnRectangle, HiUserCircle } from 'react-icons/hi2';
import { LogoMark } from '../brand/LogoMark';
import { SITE } from '../../data/site';
import { useAuth } from '../../app/AuthContext';

const LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/pricing', label: 'Pricing' },
  { to: '/blog', label: 'Blog' },
  { to: '/contact', label: 'Contact' },
];

export function PublicLayout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const displayName = user?.full_name || user?.display_name || user?.email || 'Profile';

  return (
    <div className="er">
      <header style={{ position: 'sticky', top: 0, zIndex: 50, background: '#fff', borderBottom: '1px solid #111' }}>
        <div className="er-container" style={{ height: 'var(--er-nav-h)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
          <Link to="/" style={{ textDecoration: 'none' }} aria-label="E-Room home"><LogoMark /></Link>
          <nav style={{ display: 'flex', gap: 4 }} className="er-nav-desktop">
            {LINKS.map((l) => (
              <NavLink key={l.to} to={l.to} end={l.end} style={({ isActive }) => ({ textDecoration: 'none', fontWeight: 700, fontSize: 14, padding: '10px 14px', background: isActive ? '#111' : 'transparent', color: isActive ? '#fff' : '#111', border: '1px solid transparent' })}>
                {l.label}
              </NavLink>
            ))}
          </nav>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span className="er-nav-cta" style={{ display: 'inline-flex', gap: 0, alignItems: 'stretch', border: '1px solid #111', background: '#fff' }}>
              {user ? (
                <>
                  <button onClick={() => navigate('/rooms')} style={{ padding: '10px 16px', background: '#111', color: '#fff', border: 'none', fontWeight: 800, fontSize: 14, cursor: 'pointer', whiteSpace: 'nowrap' }}>Go to Rooms</button>
                  <Link to="/profile" style={{ display: 'inline-flex', alignItems: 'center', gap: 7, textDecoration: 'none', color: '#111', fontWeight: 700, fontSize: 14, padding: '0 14px', borderLeft: '1px solid #e8e8e8' }} title="Your profile">
                    <HiUserCircle size={20} />
                    <span style={{ maxWidth: 110, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{displayName}</span>
                  </Link>
                  <button onClick={() => { logout(); navigate('/'); }} title="Sign out" aria-label="Sign out"
                    style={{ display: 'inline-flex', alignItems: 'center', padding: '0 12px', background: '#fff', color: '#111', border: 'none', borderLeft: '1px solid #e8e8e8', cursor: 'pointer' }}>
                    <HiArrowRightOnRectangle size={19} />
                  </button>
                </>
              ) : (
                <>
                  <Link style={{ padding: '10px 16px', textDecoration: 'none', color: '#111', fontWeight: 700, fontSize: 14 }} to="/login">Sign in</Link>
                  <Link style={{ padding: '10px 16px', textDecoration: 'none', background: '#111', color: '#fff', fontWeight: 800, fontSize: 14 }} to="/login">Start free</Link>
                </>
              )}
            </span>
            <button className="er-btn er-btn--ghost er-nav-toggle" style={{ padding: '10px 12px' }} onClick={() => setOpen((v) => !v)} aria-label="Menu" aria-expanded={open}>≡</button>
          </div>
        </div>
        {open && (
          <nav style={{ borderTop: '1px solid #e8e8e8', padding: 12 }} className="er-nav-mobile">
            {LINKS.map((l) => (
              <NavLink key={l.to} to={l.to} end={l.end} onClick={() => setOpen(false)} style={{ display: 'block', padding: '12px 8px', color: '#111', fontWeight: 700, textDecoration: 'none', borderBottom: '1px solid #f0f0f0' }}>{l.label}</NavLink>
            ))}
            <span style={{ display: 'flex', gap: 8, padding: '12px 0 4px' }}>
              {user ? (
                <>
                  <button className="er-btn er-btn--ghost" style={{ flex: 1 }} onClick={() => { setOpen(false); navigate('/rooms'); }}>Go to Rooms</button>
                  <Link className="er-btn er-btn--ghost" style={{ flex: 1, textDecoration: 'none', textAlign: 'center' }} to="/profile" onClick={() => setOpen(false)}>Profile</Link>
                </>
              ) : (
                <>
                  <Link className="er-btn er-btn--ghost" style={{ flex: 1, textDecoration: 'none', textAlign: 'center' }} to="/login" onClick={() => setOpen(false)}>Sign in</Link>
                  <Link className="er-btn" style={{ flex: 1, textDecoration: 'none', textAlign: 'center' }} to="/login" onClick={() => setOpen(false)}>Start free</Link>
                </>
              )}
            </span>
          </nav>
        )}
      </header>
      <main>{children}</main>
      <footer style={{ background: '#111', color: '#fff' }}>
        <div className="er-container" style={{ paddingTop: 72, paddingBottom: 28 }}>
          <div className="er-grid er-grid--4">
            <div>
              <div style={{ background: '#fff', display: 'inline-block', padding: 6 }}><LogoMark /></div>
              <p style={{ color: '#bbb', marginTop: 14, maxWidth: 300 }}>{SITE.tagline} Small video rooms, live transcripts and AI feedback for English learners.</p>
              <p style={{ color: '#fff', fontWeight: 700, marginTop: 16 }}>{SITE.hotline}</p>
              <p style={{ color: '#bbb', fontSize: 13 }}>{SITE.hotlineHours}<br />{SITE.email} • {SITE.supportEmail}</p>
            </div>
            <div>
              <h4 style={{ margin: '0 0 12px' }}>Product</h4>
              <div style={{ display: 'grid', gap: 8 }}>
                <Link to="/" style={{ color: '#bbb' }}>Home</Link>
                <Link to="/pricing" style={{ color: '#bbb' }}>Pricing</Link>
                <Link to="/blog" style={{ color: '#bbb' }}>Blog</Link>
                <Link to="/contact" style={{ color: '#bbb' }}>Contact</Link>
              </div>
            </div>
            <div>
              <h4 style={{ margin: '0 0 12px' }}>Rooms</h4>
              <div style={{ display: 'grid', gap: 8, color: '#bbb' }}>
                <span>AI Agents</span><span>Digital Art</span><span>Startups</span><span>Cinema</span>
              </div>
            </div>
            <div>
              <h4 style={{ margin: '0 0 12px' }}>Office</h4>
              <p style={{ color: '#bbb', fontSize: 14 }}>{SITE.address}</p>
              <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                {SITE.socials.map((s) => <a key={s.label} href={s.href} style={{ color: '#fff', border: '1px solid #fff', padding: '6px 10px', fontSize: 12, fontWeight: 700, textDecoration: 'none' }}>{s.label}</a>)}
              </div>
            </div>
          </div>
          <div style={{ borderTop: '1px solid #333', marginTop: 40, paddingTop: 18, display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, color: '#999', fontSize: 13 }}>
            <span>© {new Date().getFullYear()} E-Room. All rights reserved.</span>
            <span>Privacy • Terms • Hotline {SITE.hotline}</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
