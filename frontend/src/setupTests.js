import '@testing-library/jest-dom';
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

// Node >= 22 exposes a global `localStorage` stub that is non-functional
// unless --localstorage-file points at a valid path (throws
// "localStorage.getItem is not a function" under jsdom). Force a simple
// in-memory storage so tests behave like browsers.
const __mem = {};
Object.defineProperty(globalThis, 'localStorage', {
  value: {
    getItem: (k) => (k in __mem ? __mem[k] : null),
    setItem: (k, v) => { __mem[k] = String(v); },
    removeItem: (k) => { delete __mem[k]; },
    clear: () => { for (const k of Object.keys(__mem)) delete __mem[k]; },
    get length() { return Object.keys(__mem).length; },
    key: (i) => Object.keys(__mem)[i] ?? null,
  },
  writable: true,
  configurable: true,
});

i18n.use(initReactI18next).init({
  lng: 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
  resources: {
    en: {
      translation: {
        auth: {
          welcome_back: 'Welcome back',
          sign_in_subtitle: 'Sign in to continue your learning',
          create_account_title: 'Create your account',
          start_journey: 'Start your English speaking journey today',
          or: 'or',
          email_label: 'Email Address',
          email_placeholder: 'you@example.com',
          password_label: 'Password',
        },
      },
    },
  },
});
