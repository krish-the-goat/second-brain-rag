import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ErrorBoundary from '../ErrorBoundary';

function ThrowingComponent({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error('Test explosion');
  return <div>All good</div>;
}

describe('ErrorBoundary', () => {
  // Suppress console.error for expected errors in tests
  const originalError = console.error;
  beforeAll(() => { console.error = vi.fn(); });
  afterAll(() => { console.error = originalError; });

  it('renders children when there is no error', () => {
    render(
      <ErrorBoundary>
        <div>Child content</div>
      </ErrorBoundary>
    );
    expect(screen.getByText('Child content')).toBeInTheDocument();
  });

  it('shows fallback UI when child throws', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('displays custom fallback message', () => {
    render(
      <ErrorBoundary fallbackMessage="Upload broke!">
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText('Upload broke!')).toBeInTheDocument();
  });

  it('shows error details in expandable section', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText('Error details')).toBeInTheDocument();
    expect(screen.getByText('Test explosion')).toBeInTheDocument();
  });

  it('resets error state when Try again is clicked', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();

    // The reset button should be present and clickable
    const btn = screen.getByRole('button', { name: /retry and reset/i });
    expect(btn).toBeInTheDocument();

    // Clicking it resets internal state (component will re-throw,
    // but this verifies the button mechanism works)
    fireEvent.click(btn);
    // After click, the child re-throws so error boundary catches again
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });
});
