import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import Navbar from 'react-bootstrap/Navbar';
import Nav from 'react-bootstrap/Nav';
import Container from 'react-bootstrap/Container';
import Button from 'react-bootstrap/Button';
import Badge from 'react-bootstrap/Badge';
import { HiHome, HiAcademicCap, HiUserCircle, HiCreditCard, HiLogout, HiSun, HiMoon } from 'react-icons/hi2';
import { useAuth } from './AuthContext';
import { useTheme } from '../context/ThemeContext';
import { Avatar } from '../components/ui/Avatar';

export function AppShell({ children }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(false);
  const { theme, toggleTheme } = useTheme();

  function handleLogout() {
    logout();
    navigate('/login');
  }

  const isActive = path => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  const navItems = [
    { path: '/', label: 'Home', icon: HiHome },
    { path: '/learning', label: 'Learning', icon: HiAcademicCap },
  ];

  return (
    <div className="app-shell d-flex flex-column min-vh-100" style={{ background: 'var(--color-bg)' }}>
      <Navbar
        expand="lg"
        fixed="top"
        expanded={expanded}
        onToggle={setExpanded}
        className="glass-panel"
        style={{
          background: 'var(--color-bg-glass)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          borderBottom: '1px solid var(--color-border)',
          fontFamily: 'Nunito, sans-serif',
        }}
      >
        <Container>
          <Navbar.Brand as={Link} to="/" onClick={() => setExpanded(false)}
            className="fw-extrabold d-flex align-items-center gap-2"
            style={{ color: 'var(--color-text-primary)', fontSize: '1.1rem' }}
          >
            <span className="d-flex align-items-center justify-content-center rounded-3"
              style={{ width: 32, height: 32, background: 'var(--color-accent)', color: '#fff', fontSize: '0.95rem', fontWeight: 800 }}>
              E
            </span>
            E-Room
          </Navbar.Brand>

          <Navbar.Toggle aria-controls="main-navbar" className="border-0" />

          <Navbar.Collapse id="main-navbar">
            <Nav className="me-auto gap-1">
              {navItems.map(item => (
                <Nav.Link key={item.path} as={Link} to={item.path}
                  className={`rounded-pill px-3 d-flex align-items-center gap-1 ${isActive(item.path) ? 'active' : ''}`}
                  style={{
                    color: isActive(item.path) ? 'var(--color-accent)' : 'var(--color-text-secondary)',
                    fontWeight: isActive(item.path) ? 600 : 500,
                    fontSize: '0.875rem',
                    background: isActive(item.path) ? 'var(--color-accent-muted)' : 'transparent',
                  }}
                  onClick={() => setExpanded(false)}
                >
                  <item.icon size={16} />
                  {item.label}
                </Nav.Link>
              ))}
            </Nav>

            <Nav className="align-items-lg-center gap-1">
              <Button variant="link" size="sm" className="text-decoration-none rounded-pill px-2 d-flex align-items-center"
                style={{ color: 'var(--color-text-secondary)', fontSize: '1.1rem' }}
                onClick={toggleTheme} title="Toggle theme"
              >
                {theme === 'dark' ? <HiSun size={18} /> : <HiMoon size={18} />}
              </Button>

              {user ? (
                <>
                  <Nav.Link as={Link} to="/profile"
                    className="rounded-pill px-3 d-flex align-items-center gap-2"
                    style={{
                      color: isActive('/profile') ? 'var(--color-accent)' : 'var(--color-text-secondary)',
                      fontWeight: isActive('/profile') ? 600 : 500, fontSize: '0.875rem',
                    }}
                    onClick={() => setExpanded(false)}
                  >
                    <HiUserCircle size={18} />
                    <span className="d-none d-md-inline">{user.display_name || 'Profile'}</span>
                  </Nav.Link>

                  <Nav.Link as={Link} to="/payment"
                    className={`rounded-pill px-3 d-flex align-items-center gap-1 ${isActive('/payment') ? 'active' : ''}`}
                    style={{
                      color: isActive('/payment') ? 'var(--color-accent)' : 'var(--color-text-secondary)',
                      fontWeight: 500, fontSize: '0.875rem',
                    }}
                    onClick={() => setExpanded(false)}
                  >
                    <HiCreditCard size={16} />
                    <Badge bg="warning" text="dark" className="rounded-pill fw-semibold" style={{ fontSize: '0.6rem' }}>PRO</Badge>
                  </Nav.Link>

                  <Button variant="link" size="sm"
                    className="text-decoration-none rounded-pill px-2 d-none d-lg-flex align-items-center"
                    style={{ color: 'var(--color-text-muted)', fontSize: '1rem' }}
                    onClick={handleLogout} title="Sign out"
                  >
                    <HiLogout size={18} />
                  </Button>

                  <Button variant="outline-danger" size="sm" className="rounded-pill d-lg-none w-100 mt-2"
                    onClick={() => { handleLogout(); setExpanded(false); }}
                  >Sign Out</Button>
                </>
              ) : (
                <Button as={Link} to="/login" variant="primary" size="sm"
                  className="rounded-pill px-4 fw-semibold" onClick={() => setExpanded(false)}>
                  Sign In
                </Button>
              )}
            </Nav>
          </Navbar.Collapse>
        </Container>
      </Navbar>

      <main style={{ paddingTop: '72px', flex: 1 }}>{children}</main>

      <footer className="py-3 border-top" style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg-elevated)' }}>
        <Container>
          <div className="d-flex flex-column flex-md-row justify-content-between align-items-center gap-2">
            <small className="text-muted">
              <span className="fw-bold" style={{ fontFamily: 'Nunito, sans-serif', color: 'var(--color-text-primary)' }}>E-Room</span>
              {' '}— Speak English, Connect Globally
            </small>
            <div className="d-flex gap-3">
              <Link to="/" className="text-muted small text-decoration-none">Home</Link>
              <Link to="/learning" className="text-muted small text-decoration-none">Learning</Link>
              <Link to="/profile" className="text-muted small text-decoration-none">Profile</Link>
              <Link to="/payment" className="text-muted small text-decoration-none">Pricing</Link>
            </div>
          </div>
        </Container>
      </footer>
    </div>
  );
}
