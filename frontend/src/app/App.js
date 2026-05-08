import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './AuthContext';
import { ProtectedRoute } from './ProtectedRoute';
import { DashboardPage } from './pages/DashboardPage';
import { LoginPage } from '../features/auth/LoginPage';
import { RoomPage } from '../features/rooms/RoomPage';

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/rooms/:roomId"
            element={
              <ProtectedRoute>
                <RoomPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
