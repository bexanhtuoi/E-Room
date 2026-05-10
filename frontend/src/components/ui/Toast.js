import { createContext, useCallback, useContext, useState } from 'react';

const ToastContext = createContext(null);

let toastId = 0;

const COLORS = {
  success: { bg: '#059669', icon: '✅' },
  error: { bg: '#dc2626', icon: '❌' },
  warning: { bg: '#d97706', icon: '⚠️' },
  info: { bg: '#2563eb', icon: 'ℹ️' },
};

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = 'info', duration = 5000) => {
    const id = ++toastId;
    setToasts(prev => [...prev, { id, message, type, duration }]);
    if (duration > 0) {
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id));
      }, duration);
    }
    return id;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}
      <div style={{
        position: 'fixed', top: 16, right: 16, zIndex: 9999,
        display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 380,
      }}>
        {toasts.map(t => {
          const { bg, icon } = COLORS[t.type] || COLORS.info;
          return (
            <div key={t.id} style={{
              background: '#1e293b', borderLeft: `4px solid ${bg}`,
              color: '#f1f5f9', padding: '12px 16px', borderRadius: 8,
              fontSize: 14, lineHeight: 1.5, display: 'flex', gap: 10,
              alignItems: 'flex-start', boxShadow: '0 4px 16px rgba(0,0,0,.4)',
              animation: 'toastSlideIn 0.25s ease',
            }}>
              <span style={{ flexShrink: 0 }}>{icon}</span>
              <span style={{ flex: 1 }}>{t.message}</span>
              <button
                onClick={() => removeToast(t.id)}
                style={{
                  background: 'none', border: 'none', color: '#94a3b8',
                  cursor: 'pointer', fontSize: 16, lineHeight: 1, padding: 0,
                  flexShrink: 0,
                }}
                aria-label="Dismiss"
              >
                ✕
              </button>
            </div>
          );
        })}
      </div>
      <style>{`
        @keyframes toastSlideIn {
          from { opacity: 0; transform: translateX(24px); }
          to { opacity: 1; transform: translateX(0); }
        }
      `}</style>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>');
  return ctx;
}

export function showApiError(addToast, error, fallback = 'Something went wrong') {
  const message = error?.detail || error?.message || fallback;
  addToast(message, 'error');
}

export { ToastContext };
export default ToastProvider;
