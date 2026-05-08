import { Navigate } from 'react-router-dom';
import { useAuth } from '../app/AuthContext';

export function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#020617',
        color: '#94a3b8',
      }}>
        Loading...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
