import { render, screen } from '@testing-library/react';
import { App } from './app/App';

test('renders e-room shell title', () => {
  render(<App />);
  expect(screen.getByText(/Realtime English speaking rooms/i)).toBeInTheDocument();
});
