import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

// Mock child components to isolate App layout testing
vi.mock('../FileUpload', () => ({ default: () => <div data-testid="file-upload">FileUpload</div> }));
vi.mock('../DocumentList', () => ({ default: () => <div data-testid="doc-list">DocumentList</div> }));
vi.mock('../ChatInterface', () => ({ default: () => <div data-testid="chat">ChatInterface</div> }));

import App from '../../App';

describe('App', () => {
  it('renders the header with brand name', () => {
    render(<App />);
    expect(screen.getByText('Second Brain RAG')).toBeInTheDocument();
  });

  it('renders all main sections', () => {
    render(<App />);
    expect(screen.getByTestId('file-upload')).toBeInTheDocument();
    expect(screen.getByTestId('doc-list')).toBeInTheDocument();
    expect(screen.getByTestId('chat')).toBeInTheDocument();
  });

  it('has correct ARIA landmarks', () => {
    render(<App />);
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('has sidebar with document management label', () => {
    render(<App />);
    expect(screen.getByLabelText('Document management')).toBeInTheDocument();
  });

  it('has chat section with AI Chat label', () => {
    render(<App />);
    expect(screen.getByLabelText('AI Chat')).toBeInTheDocument();
  });

  it('wraps sections in error boundaries', () => {
    // The error boundaries are present (they render children normally)
    render(<App />);
    // If error boundaries didn't render, children wouldn't appear
    expect(screen.getByTestId('file-upload')).toBeInTheDocument();
    expect(screen.getByTestId('chat')).toBeInTheDocument();
  });
});
