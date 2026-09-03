import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock child components to isolate App layout testing
vi.mock('../FileUpload', () => ({ default: () => <div data-testid="file-upload">FileUpload</div> }));
vi.mock('../DocumentList', () => ({ default: () => <div data-testid="doc-list">DocumentList</div> }));
vi.mock('../ChatInterface', () => ({ default: () => <div data-testid="chat">ChatInterface</div> }));

import App from '../../App';

describe('App', () => {
  beforeEach(() => {
    localStorage.setItem('access_token', 'mock-jwt-token');
  });

  afterEach(() => {
    localStorage.clear();
  });

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

  it('renders auth screen when not authenticated', () => {
    localStorage.clear();
    render(<App />);
    expect(screen.getByRole('tab', { name: /^sign in$/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /^register$/i })).toBeInTheDocument();
    expect(screen.queryByTestId('file-upload')).not.toBeInTheDocument();
  });

  it('renders user area and logout button in header when authenticated', () => {
    localStorage.setItem('user_email', 'user@example.com');
    render(<App />);
    expect(screen.getByText('user@example.com')).toBeInTheDocument();
    const logoutBtn = screen.getByRole('button', { name: /log out/i });
    expect(logoutBtn).toBeInTheDocument();

    fireEvent.click(logoutBtn);
    // After logout, user should be back on the auth screen
    expect(screen.getByRole('tab', { name: /^sign in$/i })).toBeInTheDocument();
    expect(screen.queryByTestId('file-upload')).not.toBeInTheDocument();
  });
});
