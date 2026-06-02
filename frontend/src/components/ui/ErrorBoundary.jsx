import { Component } from 'react';

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div style={{
          minHeight: '100vh', display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          padding: 40, textAlign: 'center',
          background: 'var(--color-bg)', color: 'var(--color-text-primary)',
        }}>
          <h2 style={{ marginBottom: 8 }}>Something went wrong</h2>
          <p style={{ color: 'var(--color-text-muted)', marginBottom: 4, fontSize: '0.85rem' }}>
            {this.state.error?.message}
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: 16, padding: '8px 20px', borderRadius: 99,
              border: '1px solid var(--color-border)',
              background: 'var(--color-bg-surface)',
              color: 'var(--color-text-primary)',
              cursor: 'pointer', fontFamily: 'inherit', fontSize: '0.85rem',
            }}
          >
            Reload page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
