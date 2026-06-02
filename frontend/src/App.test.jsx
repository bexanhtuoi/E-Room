import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from './app/AuthContext';
import { LoginPage } from './features/auth/LoginPage';

test('renders login page', () => {
  render(
    <MemoryRouter>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </MemoryRouter>
  );
  expect(screen.getByText(/Welcome back/i)).toBeInTheDocument();
});
