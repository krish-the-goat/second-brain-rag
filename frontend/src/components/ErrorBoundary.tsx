import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackMessage?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          aria-live="assertive"
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '3rem 2rem',
            textAlign: 'center',
            gap: '1rem',
            minHeight: '200px',
          }}
        >
          <AlertCircle size={48} style={{ color: '#ff4757', opacity: 0.8 }} aria-hidden="true" />
          <h2 style={{ fontSize: '1.1rem', color: 'var(--text-primary)', fontWeight: 600 }}>
            Something went wrong
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: '400px' }}>
            {this.props.fallbackMessage || 'An unexpected error occurred. Please try again.'}
          </p>
          {this.state.error && (
            <details style={{ color: 'var(--text-muted)', fontSize: '0.8rem', maxWidth: '500px' }}>
              <summary style={{ cursor: 'pointer', marginBottom: '0.5rem' }}>Error details</summary>
              <code style={{ wordBreak: 'break-all' }}>{this.state.error.message}</code>
            </details>
          )}
          <button
            onClick={this.handleReset}
            aria-label="Retry and reset the component"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.6rem 1.2rem',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border, rgba(255,255,255,0.1))',
              background: 'var(--bg-surface)',
              color: 'var(--text-primary)',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: 500,
              transition: 'all 0.2s',
            }}
          >
            <RefreshCw size={14} aria-hidden="true" />
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
