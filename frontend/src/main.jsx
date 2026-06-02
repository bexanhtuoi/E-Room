import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from './lib/queryClient';
import 'bootstrap/dist/css/bootstrap.min.css';
import './styles/theme.css';
import './i18n';
import { ThemeProvider } from './context/ThemeContext';
import { App } from './app/App';

const rootElement = document.getElementById('root');
try {
  const root = ReactDOM.createRoot(rootElement);
  root.render(
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <App />
        </ThemeProvider>
      </QueryClientProvider>
    </React.StrictMode>
  );
  console.log('[boot] render() called successfully');
} catch (e) {
  console.error('[boot] RENDER ERROR:', e.message);
  rootElement.innerHTML = 'RENDER ERROR: ' + e.message + '<br>' + e.stack;
}
