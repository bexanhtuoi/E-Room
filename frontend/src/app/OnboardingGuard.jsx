import { Navigate } from 'react-router-dom';
import { useAuth } from './AuthContext';

export function OnboardingGuard({ children }) {
  const { user, loading } = useAuth();

  if (loading) return null;

  if (user && !user.profile_completed) {
    return <Navigate to="/onboarding" replace />;
  }

  return children;
}
