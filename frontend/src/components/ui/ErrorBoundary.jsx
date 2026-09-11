import { Component } from 'react';
import '../../styles/ErrorBoundary.css';

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    // Deploy moi doi hash chunk (RoomsPage-*.js) → tab cu import chunk cu
    // bi 404. Tu reload 1 lan de lay index.html + chunk moi, tranh vong lap
    // bang co session (server hong that thi hien nut Reload tay).
    const message = String(error?.message || '');
    const isStaleChunk = /Failed to fetch dynamically imported module|Importing a module script failed|ChunkLoadError/i.test(message);
    if (isStaleChunk && !sessionStorage.getItem('er-chunk-reloaded')) {
      sessionStorage.setItem('er-chunk-reloaded', '1');
      window.location.reload();
      return { hasError: false, error: null };
    }
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
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <p className="error-boundary-message">
            {this.state.error?.message}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="error-boundary-btn"
          >
            Reload page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
