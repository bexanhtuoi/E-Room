import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { ThemeToggle } from '../components/ui/ThemeToggle';
import { Avatar } from '../components/ui/Avatar';

export function AppShell({ children }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  function handleLogout() {
    logout();
    navigate('/login');
  }

  const isActive = (path) => location.pathname.startsWith(path);

  return (
    <div className="app-shell">
      <nav className="navbar">
        <div className="navbar-inner">
          <div className="navbar-left">
            <Link to="/dashboard" className="navbar-brand">
              <span className="navbar-logo">E</span>
              <span className="navbar-name">E-Room</span>
            </Link>
            <div className="navbar-links">
              <Link
                to="/dashboard"
                className={`navbar-link ${isActive('/dashboard') ? 'active' : ''}`}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /></svg>
                Dashboard
              </Link>
              <Link
                to="/dashboard"
                className={`navbar-link ${isActive('/rooms') ? 'active' : ''}`}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" /><rect x="1" y="9" width="22" height="14" rx="2" ry="2" /></svg>
                Rooms
              </Link>
            </div>
          </div>

          <div className="navbar-right">
            <ThemeToggle />
            {user && (
              <>
                <span className="navbar-user-name">{user.display_name}</span>
                <Avatar name={user.display_name || user.email} size={32} />
                <button className="navbar-logout" onClick={handleLogout} title="Logout">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
                </button>
              </>
            )}

            <button
              className="navbar-hamburger"
              onClick={() => setMenuOpen(!menuOpen)}
              aria-label="Toggle menu"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                {menuOpen ? (
                  <><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></>
                ) : (
                  <><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="18" x2="21" y2="18" /></>
                )}
              </svg>
            </button>
          </div>
        </div>

        {menuOpen && (
          <div className="navbar-mobile-menu">
            <Link to="/dashboard" className="navbar-link active" onClick={() => setMenuOpen(false)}>Dashboard</Link>
            <Link to="/dashboard" className="navbar-link" onClick={() => setMenuOpen(false)}>Rooms</Link>
            {user && (
              <button className="navbar-logout mobile" onClick={() => { handleLogout(); setMenuOpen(false); }}>Logout</button>
            )}
          </div>
        )}
      </nav>

      <main className="main-content">
        {children}
      </main>

      <style>{`
        .app-shell { min-height: 100vh; background: var(--color-bg); }
        .navbar {
          position: fixed; top: 0; left: 0; right: 0; z-index: 50;
          height: var(--navbar-height);
          background: var(--color-bg-glass);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          border-bottom: 1px solid var(--color-border);
        }
        .navbar-inner {
          display: flex; align-items: center; justify-content: space-between;
          height: 100%; padding: 0 20px; max-width: 1280px; margin: 0 auto;
        }
        .navbar-left { display: flex; align-items: center; gap: 32px; }
        .navbar-brand {
          display: flex; align-items: center; gap: 8px;
          color: var(--color-text-primary); font-weight: 700; font-size: 17px;
          font-family: var(--font-display); text-decoration: none;
        }
        .navbar-logo {
          display: flex; align-items: center; justify-content: center;
          width: 30px; height: 30px; border-radius: var(--radius-sm);
          background: var(--color-accent); color: #fff;
          font-size: 15px; font-weight: 700;
        }
        .navbar-links { display: flex; gap: 4px; }
        .navbar-link {
          display: flex; align-items: center; gap: 6px;
          padding: 6px 12px; border-radius: var(--radius-md);
          color: var(--color-text-secondary); font-size: 13px; font-weight: 500;
          text-decoration: none; transition: all var(--transition-fast);
        }
        .navbar-link:hover { color: var(--color-text-primary); background: var(--color-bg-hover); }
        .navbar-link.active { color: var(--color-accent); background: var(--color-accent-muted); }

        .navbar-right { display: flex; align-items: center; gap: 10px; }
        .navbar-user-name { font-size: 13px; color: var(--color-text-secondary); font-weight: 500; }
        .navbar-logout {
          display: flex; align-items: center; justify-content: center;
          width: 32px; height: 32px; border-radius: var(--radius-md);
          color: var(--color-text-muted); transition: all var(--transition-fast);
        }
        .navbar-logout:hover { color: var(--color-danger); background: var(--color-danger-muted); }
        .navbar-logout.mobile { width: 100%; justify-content: flex-start; padding: 10px 16px; }

        .navbar-hamburger { display: none; align-items: center; justify-content: center; color: var(--color-text-secondary); }
        .navbar-mobile-menu { display: none; flex-direction: column; padding: 8px 16px 16px; background: var(--color-bg-elevated); border-bottom: 1px solid var(--color-border); }

        @media (max-width: 768px) {
          .navbar-links { display: none; }
          .navbar-user-name { display: none; }
          .navbar-hamburger { display: flex; }
          .navbar-mobile-menu { display: flex; }
        }

        .main-content { padding-top: var(--navbar-height); min-height: calc(100vh - var(--navbar-height)); }
      `}</style>
    </div>
  );
}
