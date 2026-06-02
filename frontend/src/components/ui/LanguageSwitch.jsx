import { useTranslation } from 'react-i18next';

export function LanguageSwitch({ compact = false }) {
  const { i18n } = useTranslation();

  function toggle() {
    const next = i18n.language === 'vi' ? 'en' : 'vi';
    i18n.changeLanguage(next);
  }

  if (compact) {
    return (
      <button
        onClick={toggle}
        style={{
          padding: '4px 10px', borderRadius: 99,
          background: 'var(--color-bg-surface)',
          border: '1px solid var(--color-border)',
          color: 'var(--color-text-secondary)',
          cursor: 'pointer', fontWeight: 700, fontSize: '0.72rem',
          fontFamily: 'inherit', fontFeatureSettings: '"calt" 1',
        }}
      >
        {i18n.language === 'vi' ? '🇻🇳 VI' : '🇬🇧 EN'}
      </button>
    );
  }

  return (
    <button
      onClick={toggle}
      style={{
        display: 'flex', alignItems: 'center', gap: 6,
        padding: '8px 14px', borderRadius: 99,
        background: 'var(--color-bg-surface)',
        border: '1px solid var(--color-border)',
        color: 'var(--color-text-secondary)', cursor: 'pointer',
        fontFamily: 'inherit', fontWeight: 600, fontSize: '0.82rem',
        transition: 'all 0.12s',
      }}
      onMouseOver={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)'; }}
      onMouseOut={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)'; }}
    >
      {i18n.language === 'vi' ? '🇻🇳 Tiếng Việt' : '🇬🇧 English'}
    </button>
  );
}
