import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { AuthProvider } from './AuthContext';
import { AuthGuard } from './AuthGuard';
import { ErrorBoundary } from '../components/ui/ErrorBoundary';
import { HomePage } from './pages/HomePage';
import { LoginPage } from '../features/auth/LoginPage';
import { AppShell } from './AppShell';

const RoomsPage = lazy(() => import('../features/rooms/RoomsPage').then(m => ({ default: m.RoomsPage })));
const ProfilePage = lazy(() => import('./pages/ProfilePage').then(m => ({ default: m.ProfilePage })));
const PaymentPage = lazy(() => import('./pages/PaymentPage').then(m => ({ default: m.PaymentPage })));
const PricingPage = lazy(() => import('./pages/PricingPage').then(m => ({ default: m.PricingPage })));
const RoomPage = lazy(() => import('../features/rooms/RoomPage').then(m => ({ default: m.RoomPage })));
const OnboardingWizard = lazy(() => import('../features/onboarding/OnboardingWizard').then(m => ({ default: m.OnboardingWizard })));
const BlogPage = lazy(() => import('./pages/BlogPage').then(m => ({ default: m.BlogPage })));
const BlogDetailPage = lazy(() => import('./pages/BlogDetailPage').then(m => ({ default: m.BlogDetailPage })));
const ContactPage = lazy(() => import('./pages/ContactPage').then(m => ({ default: m.ContactPage })));

function PageLoader() {
  return (
    <div className="page-loader">
      Loading...
    </div>
  );
}

function Protected({ children, requireOnboarding = true }) {
  return (
    <AuthGuard requireOnboarding={requireOnboarding}>
      <AppShell>{children}</AppShell>
    </AuthGuard>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Suspense fallback={<PageLoader />}>
          <ErrorBoundary>
          <Routes>
            {/* Public */}
            <Route path="/" element={<AppShell><HomePage /></AppShell>} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/blog" element={<AppShell><BlogPage /></AppShell>} />
            <Route path="/blog/:slug" element={<AppShell><BlogDetailPage /></AppShell>} />
            <Route path="/contact" element={<AppShell><ContactPage /></AppShell>} />

            {/* Onboarding */}
            <Route path="/onboarding" element={<AuthGuard><OnboardingWizard /></AuthGuard>} />

            {/* Protected */}
            <Route path="/rooms" element={<Protected><RoomsPage /></Protected>} />
            <Route path="/learning" element={<Navigate to="/rooms" replace />} />
            <Route path="/meeting" element={<Navigate to="/rooms" replace />} />
            <Route path="/profile" element={<Protected><ProfilePage /></Protected>} />
            <Route path="/pricing" element={<AppShell><PricingPage /></AppShell>} />
            <Route path="/payment" element={<Protected><PaymentPage /></Protected>} />
            {/* v1 routes removed: portal profile v2 covers rooms/activity/documents/notifications */}
            <Route path="/rooms/:roomId" element={<AuthGuard><RoomPage /></AuthGuard>} />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          </ErrorBoundary>
        </Suspense>
      </AuthProvider>
    </BrowserRouter>
  );
}
