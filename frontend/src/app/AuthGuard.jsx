import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';

export function AuthGuard({ children, requireOnboarding = false }) {
  const { isAuthenticated, loading, user } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center',
        justifyContent: 'center', background: 'var(--color-bg)', color: 'var(--color-text-muted)',
      }}>
        Loading...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requireOnboarding && user && !user.profile_completed && !location.pathname.startsWith('/onboarding')) {
    return <Navigate to="/onboarding" replace />;
  }

  return children;
}
