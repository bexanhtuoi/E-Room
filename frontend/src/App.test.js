import { render, screen } from '@testing-library/react';
import { AuthProvider } from './app/AuthContext';
import { LoginPage } from './features/auth/LoginPage';

test('renders login page', () => {
  render(
    <AuthProvider>
      <LoginPage />
    </AuthProvider>
  );
  expect(screen.getByText(/Welcome back/i)).toBeInTheDocument();
});
