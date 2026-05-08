import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './AuthContext';
import { ProtectedRoute } from './ProtectedRoute';
import { HomePage } from './pages/HomePage';
import { ProfilePage } from './pages/ProfilePage';
import { PaymentPage } from './pages/PaymentPage';
import { DashboardPage } from './pages/DashboardPage';
import { LoginPage } from '../features/auth/LoginPage';
import { RoomPage } from '../features/rooms/RoomPage';
import { AppShell } from './AppShell';

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public */}
          <Route path="/" element={<AppShell><HomePage /></AppShell>} />
          <Route path="/login" element={<LoginPage />} />

          {/* Protected */}
          <Route path="/dashboard" element={
            <ProtectedRoute><AppShell><DashboardPage /></AppShell></ProtectedRoute>
          } />
          <Route path="/profile" element={
            <ProtectedRoute><AppShell><ProfilePage /></AppShell></ProtectedRoute>
          } />
          <Route path="/payment" element={
            <ProtectedRoute><AppShell><PaymentPage /></AppShell></ProtectedRoute>
          } />
          <Route path="/rooms/:roomId" element={
            <ProtectedRoute><AppShell><RoomPage /></AppShell></ProtectedRoute>
          } />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
