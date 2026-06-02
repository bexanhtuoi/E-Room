import '@testing-library/jest-dom';
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

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
