import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import AuthScreen from '../AuthScreen';
import { AuthProvider } from '../../context/AuthContext';

vi.mock('../../services/api', () => ({
  default: {
    post: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}));

import api from '../../services/api';

describe('AuthScreen', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('renders login form initially', () => {
    render(
      <AuthProvider>
        <AuthScreen />
      </AuthProvider>
    );

    expect(screen.getByText('Second Brain RAG')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Second Brain RAG');
    expect(screen.getByLabelText('Email Address')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('toggles between Sign In and Register modes', () => {
    render(
      <AuthProvider>
        <AuthScreen />
      </AuthProvider>
    );

    const registerTab = screen.getByRole('tab', { name: /register/i });
    fireEvent.click(registerTab);

    expect(screen.getByText(/create your account to start curating knowledge/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument();

    const signInTab = screen.getByRole('tab', { name: /sign in/i });
    fireEvent.click(signInTab);

    expect(screen.getByText(/sign in to access your ai second brain/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('submits login request with entered credentials', async () => {
    (api.post as any).mockResolvedValueOnce({
      data: { access_token: 'login-jwt-token' },
    });

    render(
      <AuthProvider>
        <AuthScreen />
      </AuthProvider>
    );

    fireEvent.change(screen.getByLabelText('Email Address'), {
      target: { value: 'test@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'password123' },
    });

    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/auth/login', {
        email: 'test@example.com',
        password: 'password123',
      });
    });
  });

  it('displays error message on failed login', async () => {
    (api.post as any).mockRejectedValueOnce({
      response: { status: 401, data: { detail: 'Invalid credentials' } },
    });

    render(
      <AuthProvider>
        <AuthScreen />
      </AuthProvider>
    );

    fireEvent.change(screen.getByLabelText('Email Address'), {
      target: { value: 'wrong@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'wrongpass' },
    });

    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Invalid credentials');
    });
  });

  it('submits registration request when in register mode', async () => {
    (api.post as any).mockResolvedValueOnce({
      data: { access_token: 'register-jwt-token' },
    });

    render(
      <AuthProvider>
        <AuthScreen />
      </AuthProvider>
    );

    fireEvent.click(screen.getByRole('tab', { name: /register/i }));

    fireEvent.change(screen.getByLabelText('Email Address'), {
      target: { value: 'newuser@example.com' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'secretpass' },
    });

    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/auth/register', {
        email: 'newuser@example.com',
        password: 'secretpass',
      });
    });
  });
});
