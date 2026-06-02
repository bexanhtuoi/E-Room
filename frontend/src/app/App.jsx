import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { AuthProvider } from './AuthContext';
import { AuthGuard } from './AuthGuard';
import { ErrorBoundary } from '../components/ui/ErrorBoundary';
import { HomePage } from './pages/HomePage';
import { LoginPage } from '../features/auth/LoginPage';
import { AppShell } from './AppShell';

const LearningPage = lazy(() => import('./pages/LearningPage').then(m => ({ default: m.LearningPage })));
const ProfilePage = lazy(() => import('./pages/ProfilePage').then(m => ({ default: m.ProfilePage })));
const PaymentPage = lazy(() => import('./pages/PaymentPage').then(m => ({ default: m.PaymentPage })));
const PricingPage = lazy(() => import('./pages/PricingPage').then(m => ({ default: m.PricingPage })));
const RoomPage = lazy(() => import('../features/rooms/RoomPage').then(m => ({ default: m.RoomPage })));
const OnboardingWizard = lazy(() => import('../features/onboarding/OnboardingWizard').then(m => ({ default: m.OnboardingWizard })));
const SessionsPage = lazy(() => import('../features/sessions/SessionsPage').then(m => ({ default: m.SessionsPage })));
const SessionDetailPage = lazy(() => import('../features/sessions/SessionDetailPage').then(m => ({ default: m.SessionDetailPage })));
const NotesPage = lazy(() => import('../features/notes/NotesPage').then(m => ({ default: m.NotesPage })));
const NoteDetailPage = lazy(() => import('../features/notes/NoteDetailPage').then(m => ({ default: m.NoteDetailPage })));
const SeriesPage = lazy(() => import('../features/series/SeriesPage').then(m => ({ default: m.SeriesPage })));
const LeaderboardPage = lazy(() => import('../features/leaderboard/LeaderboardPage').then(m => ({ default: m.LeaderboardPage })));
const BlogPage = lazy(() => import('./pages/BlogPage').then(m => ({ default: m.BlogPage })));
const BlogDetailPage = lazy(() => import('./pages/BlogDetailPage').then(m => ({ default: m.BlogDetailPage })));
const ContactPage = lazy(() => import('./pages/ContactPage').then(m => ({ default: m.ContactPage })));

function PageLoader() {
  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--color-bg)', color: 'var(--color-text-muted)',
    }}>
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
            <Route path="/learning" element={<Protected><LearningPage /></Protected>} />
            <Route path="/meeting" element={<Protected><LearningPage /></Protected>} />
            <Route path="/profile" element={<Protected><ProfilePage /></Protected>} />
            <Route path="/pricing" element={<AppShell><PricingPage /></AppShell>} />
            <Route path="/payment" element={<Protected><PaymentPage /></Protected>} />
            <Route path="/sessions" element={<Protected><SessionsPage /></Protected>} />
            <Route path="/sessions/:sessionId" element={<Protected><SessionDetailPage /></Protected>} />
            <Route path="/notes" element={<Protected><NotesPage /></Protected>} />
            <Route path="/notes/:noteId" element={<Protected><NoteDetailPage /></Protected>} />
            <Route path="/series" element={<Protected><SeriesPage /></Protected>} />
            <Route path="/leaderboard" element={<Protected><LeaderboardPage /></Protected>} />
            <Route path="/rankings" element={<Protected><LeaderboardPage /></Protected>} />
            <Route path="/rooms/:roomId" element={<AuthGuard><RoomPage /></AuthGuard>} />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          </ErrorBoundary>
        </Suspense>
      </AuthProvider>
    </BrowserRouter>
  );
}
